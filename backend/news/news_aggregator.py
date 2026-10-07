"""
تجميع الأخبار وإعلانات السوق من كل المصادر (mubasher.info أولاً، Google/Bing News كباكاب)،
وتحليل تأثيرها بالـ AI كنسب مئوية (إيجابي/سلبي/محايد).
"""
import re
import hashlib
import threading
from utils.provider_health import provider_recently_failed as _provider_recently_failed
from utils.provider_health import mark_provider_failed as _mark_provider_failed
from utils.provider_health import mark_provider_ok as _mark_provider_ok
from data_sources.mubasher_source import fetch_mubasher_news, fetch_mubasher_announcements, _parse_mubasher_date
from news.news_cache import load_news_cache, save_news_cache
from news.ai_provider import call_ai_with_fallback, _parse_sentiment_percentages, _parse_news_analysis
from news.pdf_handler import get_pdf_text_and_url, get_pdf_text
from utils.cache import ttl_cache

_news_cache_lock = threading.Lock()


def _recent_mubasher_sources(ticker_symbol, company_name, max_items):
    """اجلب أخبار السهم وإعلانات السوق الرسمية من مباشر، مع محاولة صمود مستقلة لكل صفحة."""
    news_items = []
    announcement_items = []
    errors = []
    try:
        news_items, news_error = fetch_mubasher_news(
            ticker_symbol, company_name, max_items=max_items + 4
        )
        if news_error:
            errors.append(news_error)
    except Exception as exc:
        errors.append(f"Mubasher News: {exc}")
    try:
        announcement_items, announcement_error = fetch_mubasher_announcements(
            ticker_symbol, company_name, max_items=max_items + 4
        )
        if announcement_error:
            errors.append(announcement_error)
    except Exception as exc:
        errors.append(f"Mubasher Announcements: {exc}")
    return news_items, announcement_items, errors

@ttl_cache(300)
def fetch_news_headlines(ticker_symbol, company_name, max_items=3):
    """
    ترتيب المصادر: مباشر أولاً للأخبار والإفصاحات الرسمية الخاصة بسهم EGX، ثم Google News
    RSS، ثم Bing News RSS فقط كاحتياط عند عدم وجود خبر مطابق في المصادر السابقة.
    من mubasher بنجيب الأخبار العادية ("أخبار السهم") وإعلانات السوق الرسمية مع بعض
    (قرارات مجلس إدارة، جمعيات عمومية، نتائج أعمال...) ومرتبين زمنياً مع بعض كقائمة واحدة.
    بيرجع (قائمة {"title","date","source","link","item_type"}, رسالة خطأ أو None) عشان
    نقدر نميّز بين "فعلاً مفيش أخبار" و"فيه مشكلة وصول"، ونعرض تاريخ ومصدر ونوع كل بند.
    """
    mubasher_news, mubasher_announcements, mubasher_errors = _recent_mubasher_sources(
        ticker_symbol, company_name, max_items
    )

    combined = list(mubasher_news) + list(mubasher_announcements)
    if combined and (mubasher_news or mubasher_announcements):
        # مباشر هو المصدر الأساسي، ونضم الأخبار والإفصاحات الرسمية فيه قبل أي مصدر بديل.
        from datetime import datetime as _dt
        unique_mubasher = {}
        for item in combined:
            normalized_title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
            key = re.sub(r"[^\w]+", "", normalized_title.casefold())
            if normalized_title:
                unique_mubasher.setdefault(key, {**item, "title": normalized_title})
        ordered_mubasher = sorted(
            unique_mubasher.values(),
            key=lambda item: _parse_mubasher_date(item.get("date", "")) or _dt.min,
            reverse=True,
        )
        return ordered_mubasher[:max_items + 3], None

    import requests as req
    import xml.etree.ElementTree as ET
    from urllib.parse import quote
    from email.utils import parsedate_to_datetime

    symbol = ticker_symbol.replace(".CA", "")
    generic_name_tokens = {
        "شركة", "ش", "م", "القابضة", "المصرية", "مصر", "للاستثمار", "المصري",
        "للتنمية", "والاستثمار", "والشركة", "مجموعة", "بنك", "المجموعة",
    }
    distinctive_name_tokens = [
        token.casefold() for token in re.findall(r"[\w\u0600-\u06ff]+", company_name or "")
        if len(token) >= 3 and token not in generic_name_tokens
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        "Accept-Language": "ar,en;q=0.9"
    }
    errors = list(mubasher_errors)

    def _parse_items(items):
        parsed = []
        for it in items:
            title_el = it.find("title")
            if title_el is None or not title_el.text:
                continue
            date_str = ""
            pub_el = it.find("pubDate")
            if pub_el is not None and pub_el.text:
                try:
                    date_str = parsedate_to_datetime(pub_el.text).strftime("%Y-%m-%d")
                except Exception:
                    date_str = pub_el.text[:16]
            source_el = it.find("source")
            source_str = source_el.text if source_el is not None and source_el.text else ""
            link_el = it.find("link")
            link_str = link_el.text if link_el is not None and link_el.text else ""
            title = re.sub(r"\s+", " ", title_el.text).strip()
            upper_title = title.upper()
            ticker_match = re.search(rf"(?<![A-Z0-9]){re.escape(symbol.upper())}(?![A-Z0-9])", upper_title)
            name_match = any(token in title.casefold() for token in distinctive_name_tokens)
            if not ticker_match and not name_match:
                continue
            parsed.append({"title": title, "date": date_str, "source": source_str,
                            "link": link_str, "item_type": "خبر"})
        return parsed

    def _fetch_rss(provider):
        if _provider_recently_failed(provider):
            return [], f"{provider}: تم تخطيه مؤقتاً بعد فشل سابق"
        try:
            if provider == "news_google":
                query = quote(f"{symbol} {company_name} بورصة")
                url = f"https://news.google.com/rss/search?q={query}&hl=ar&gl=EG&ceid=EG:ar"
            else:
                query = quote(f"{symbol} {company_name} بورصة مصر")
                url = f"https://www.bing.com/news/search?q={query}&format=RSS"
            resp = req.get(url, timeout=6, headers=headers)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            results = _parse_items(root.findall(".//item")[:max_items + 3])
            _mark_provider_ok(provider)
            return results, None if results else f"{provider}: لا توجد نتائج"
        except Exception as exc:
            _mark_provider_failed(provider)
            return [], f"{provider}: {exc}"

    # Google/Bing احتياط فقط عند غياب نتائج مباشر، ونجربهما بالتتابع:
    # أول مصدر عام يعيد خبراً مطابقاً ينهي الطلب لتقليل زمن الانتظار.
    fallback_results = []
    google_results, google_error = _fetch_rss("news_google")
    if google_results:
        fallback_results.extend(google_results)
    elif google_error:
        errors.append(google_error)
    if not fallback_results:
        bing_results, bing_error = _fetch_rss("news_bing")
        fallback_results.extend(bing_results)
        if not bing_results and bing_error:
            errors.append(bing_error)

    # دمج المصادر مع إزالة التكرار، مع إعطاء الأولوية للتاريخ الأحدث.
    from datetime import datetime as _dt, timezone as _timezone
    from email.utils import parsedate_to_datetime

    candidates = combined + fallback_results
    unique = {}
    for item in candidates:
        title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
        if not title:
            continue
        key = re.sub(r"[^\w]+", "", title.casefold())
        unique.setdefault(key, {**item, "title": title})

    def _date_key(item):
        value = item.get("date", "")
        parsed = _parse_mubasher_date(value)
        if parsed:
            return parsed.replace(tzinfo=_timezone.utc)
        try:
            parsed = parsedate_to_datetime(value)
            return parsed.replace(tzinfo=_timezone.utc) if parsed.tzinfo is None else parsed.astimezone(_timezone.utc)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = _dt.fromisoformat(value.replace("Z", "+00:00"))
                return parsed.replace(tzinfo=_timezone.utc) if parsed.tzinfo is None else parsed.astimezone(_timezone.utc)
            except (TypeError, ValueError):
                return _dt.min.replace(tzinfo=_timezone.utc)

    ordered = sorted(unique.values(), key=_date_key, reverse=True)
    if ordered:
        return ordered[:max_items + 3], None
    return [], " | ".join(errors) if errors else None



@ttl_cache(300)
def analyze_news_for_stock(ticker_symbol, company_name):
    """
    بيجيب آخر أخبار/إعلانات السهم ويحلل تأثيرها بالـ AI كنسب مئوية (إيجابي/سلبي/محايد
    مجموعهم 100%) بدل تصنيف واحد جامد - عشان خبر ممكن يكون إيجابي غالباً (60%) بس فيه
    احتمال تأثير محايد (30%) أو سلبي (10%) حسب السياق. مع كاش على القرص بالعنوان (hash) —
    لو نفس الخبر ظهر تاني في أي rerun أو فحص جديد، مش هيتبعت للـ AI تاني خالص (توفير توكينز).
    بيرجع (النتائج, آخر أخطاء الـ AI) عشان تقدر تشوف سبب الفشل بدل ما يفشل بصمت.
    """
    with _news_cache_lock:
        cache = load_news_cache()
    headlines, news_error = fetch_news_headlines(ticker_symbol, company_name)
    if not headlines:
        return [], [news_error] if news_error else []

    results = []
    changed = False
    cache_pruned = False
    last_errors = []
    for item in headlines:
        headline = item["title"]
        news_date = item.get("date", "")
        news_source = item.get("source", "")
        item_type = item.get("item_type", "خبر")
        link = item.get("link", "")
        h_hash = hashlib.sha256(headline.encode("utf-8")).hexdigest()
        cache_key = f"{ticker_symbol}:{h_hash}"

        sentiment_pct = None
        sentiment_label = None
        fundamental_type = None
        fundamental_impact = None
        pdf_url = None

        if cache_key in cache:
            cached_val = cache[cache_key]
            if isinstance(cached_val, dict):
                if "sentiment_pct" in cached_val:
                    sentiment_pct = cached_val.get("sentiment_pct")
                    sentiment_label = cached_val.get("sentiment_label")
                    fundamental_type = cached_val.get("fundamental_type")
                    fundamental_impact = cached_val.get("fundamental_impact")
                    pdf_url = cached_val.get("pdf_url")
                else:
                    sentiment_pct = cached_val
            elif str(cached_val).startswith("غير محدد (تعذّر الوصول لأي مزوّد AI)"):
                cache.pop(cache_key, None)
                cache_pruned = True
                cached_val = None
            else:
                sentiment_label = cached_val
        else:
            cached_val = None

        if cached_val is None:
            # استخراج ملف الـ PDF المرفق إن وجد (خاصة لإعلانات السوق والإفصاحات الرسمية)
            pdf_text = None
            if item_type == "إعلان" or (link and (link.lower().endswith(".pdf") or "mubasher.info" in link)):
                pdf_text, found_pdf = get_pdf_text_and_url(link, cache, ticker_symbol)
                if found_pdf:
                    pdf_url = found_pdf

            if pdf_text:
                noun = "الإعلان الرسمي وملف الإفصاح المرفق"
                context_block = f"""عنوان الإعلان:
{headline}

نص الإفصاح المرفق (PDF):
{pdf_text[:2500]}"""
            else:
                noun = "الإعلان الرسمي" if item_type == "إعلان" else "الخبر"
                context_block = f"""{noun}:
{headline}"""

            prompt = (
                f"""حلّل تأثير {noun} ده على سهم {company_name} في البورصة المصرية وأثره الأساسي على الشركة.
قسّم احتمالية التأثير لنسب مئوية بين ثلاث احتمالات مجموعهم 100 بالظبط (إيجابي، سلبي، محايد)، مع تحديد تصنيف الأثر الأساسي وملخص مركز في سطر واحد.
رد بالصيغة دي بالظبط بدون أي مقدمات أو كلام إضافي:
إيجابي:XX سلبي:YY محايد:ZZ
تصنيف:[نوع الأثر مثل: نتائج مالية وأرباح / زيادة رأس مال وتوزيعات / شراكة وتوسع / قرارات إدارية / قضايا ومخاطر / روتيني]
الأثر:[ملخص الأثر الأساسي في جملة واحدة مكثفة]

{context_block}"""
            )
            ai_reply, ai_errors = call_ai_with_fallback(prompt)
            if ai_reply:
                parsed_pct, parsed_type, parsed_impact = _parse_news_analysis(ai_reply)
                if parsed_pct:
                    sentiment_pct = parsed_pct
                    fundamental_type = parsed_type
                    fundamental_impact = parsed_impact
                    cache[cache_key] = {
                        "sentiment_pct": sentiment_pct,
                        "fundamental_type": fundamental_type,
                        "fundamental_impact": fundamental_impact,
                        "pdf_url": pdf_url,
                    }
                else:
                    sentiment_label = ai_reply.strip()
                    cache[cache_key] = {
                        "sentiment_label": sentiment_label,
                        "fundamental_type": parsed_type,
                        "fundamental_impact": parsed_impact,
                        "pdf_url": pdf_url,
                    }
            else:
                sentiment_label = "غير متاح — تعذّر تحليل الخبر آلياً"
                last_errors = ai_errors
            changed = bool(ai_reply)

        results.append({
            "headline": headline, "date": news_date, "source": news_source,
            "link": item.get("link", ""),
            "sentiment_pct": sentiment_pct, "sentiment_label": sentiment_label,
            "fundamental_type": fundamental_type,
            "fundamental_impact": fundamental_impact,
            "pdf_url": pdf_url,
            "item_type": item_type
        })

    if changed or cache_pruned:
        with _news_cache_lock:
            current_cache = load_news_cache()
            current_cache.update(cache)
            save_news_cache(current_cache)
    return results, last_errors


