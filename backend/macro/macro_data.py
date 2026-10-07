"""
أسعار ومعلومات عالمية مؤثرة على القرار الاستثماري: الذهب، الفضة، الدولار، ومؤشر الدولار
(عن طريق yfinance)، وأخبار جيوسياسية/اقتصادية عامة مؤثرة على الأسواق (عن طريق نفس آلية
Google/Bing News المستخدمة في أخبار الأسهم الفردية).
"""
import hashlib
import yfinance as yf
import pandas as pd
from utils.provider_health import provider_recently_failed as _provider_recently_failed
from utils.provider_health import mark_provider_failed as _mark_provider_failed
from utils.provider_health import mark_provider_ok as _mark_provider_ok
from utils.cache import ttl_cache

@ttl_cache(300)
def fetch_macro_prices():
    """
    أسعار عالمية مؤثرة على القرار الاستثماري (الذهب، الفضة، الدولار مقابل الجنيه، مؤشر
    الدولار) عن طريق yfinance - نفس المصدر المستخدم في باقي الأداة، مفيش مصدر جديد.
    كل عملة/سلعة ليها رمز احتياطي بديل (زي GLD بدل GC=F) لو الرمز الأساسي رجّع بيانات
    فاضية أو NaN (عقود العملات الآجلة أحياناً بيكون فيها فجوات في التداول اليومي).
    """
    symbols = {
        "🥇 الذهب (أوقية/دولار)": ["GC=F", "GLD"],
        "🥈 الفضة (أوقية/دولار)": ["SI=F", "SLV"],
        "💵 دولار/جنيه مصري": ["USDEGP=X"],
        "📊 مؤشر الدولار (DXY)": ["DX-Y.NYB", "UUP"],
    }
    results = {}
    for label, candidates in symbols.items():
        for sym in candidates:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="10d", interval="1d")
                if hist is None or hist.empty:
                    continue
                hist = hist.dropna(subset=["Close"])
                if hist.empty:
                    continue
                last = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
                if pd.isna(last) or pd.isna(prev):
                    continue
                change_pct = ((last - prev) / prev) * 100 if prev else 0
                results[label] = {"price": round(last, 2), "change_pct": round(change_pct, 2)}
                break  # نجح الرمز ده، متجربش الاحتياطي
            except Exception:
                continue
    return results


def fetch_macro_news(query, max_items=5, freshness_days=3):
    """
    أخبار عامة عن السوق العالمي/الجيوسياسي (حروب، قرارات اقتصادية كبرى) ومدى تأثيرها على
    البورصة المصرية والعالمية والذهب والفضة والدولار - بنفس آلية Google/Bing News المستخدمة
    لأخبار الأسهم الفردية، بس باستعلام عام مش مرتبط بسهم بعينه.
    بيضيف "when:Nd" لاستعلام Google News (خاصية حقيقية في بحث جوجل بتحدد الأخبار لآخر
    N يوم بس) عشان نتجنب رجوع أخبار قديمة/عامة مش مرتبطة باللحظة الحالية.
    بيرجع (قائمة {"title","date","source","link"} مرتبة زمنياً الأحدث أولاً, رسالة خطأ أو None).
    """
    import requests as req
    import xml.etree.ElementTree as ET
    from urllib.parse import quote
    from email.utils import parsedate_to_datetime
    from datetime import datetime as _dt

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        "Accept-Language": "ar,en;q=0.9"
    }
    errors = []

    def _parse_items(items):
        parsed = []
        for it in items:
            title_el = it.find("title")
            if title_el is None or not title_el.text:
                continue
            parsed_dt = None
            date_display = ""
            pub_el = it.find("pubDate")
            if pub_el is not None and pub_el.text:
                try:
                    parsed_dt = parsedate_to_datetime(pub_el.text)
                    date_display = parsed_dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_display = pub_el.text[:16]
            source_el = it.find("source")
            source_str = source_el.text if source_el is not None and source_el.text else ""
            link_el = it.find("link")
            link_str = link_el.text if link_el is not None and link_el.text else ""
            parsed.append({"title": title_el.text, "date": date_display, "_parsed_dt": parsed_dt,
                            "source": source_str, "link": link_str})
        # ترتيب زمني حقيقي (مش ترتيب جوجل الافتراضي اللي بيرجّح الصلة مش بالضرورة الحداثة)
        parsed.sort(key=lambda x: x["_parsed_dt"] or _dt.min, reverse=True)
        for p in parsed:
            p.pop("_parsed_dt", None)
        return parsed

    provider_key_base = f"macro_news_{hashlib.md5(query.encode('utf-8')).hexdigest()[:8]}"
    query_with_freshness = f"{query} when:{freshness_days}d"

    if not _provider_recently_failed(f"{provider_key_base}_google"):
        try:
            q = quote(query_with_freshness)
            url = f"https://news.google.com/rss/search?q={q}&hl=ar&gl=EG&ceid=EG:ar"
            resp = req.get(url, timeout=6, headers=headers)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:max_items]
            headlines = _parse_items(items)
            if headlines:
                _mark_provider_ok(f"{provider_key_base}_google")
                return headlines, None
            errors.append("Google News: رجّع رد من غير أي أخبار")
        except Exception as e:
            _mark_provider_failed(f"{provider_key_base}_google")
            errors.append(f"Google News: {e}")
    else:
        errors.append("Google News: تم تخطيه مؤقتاً (فشل قبل كده في آخر 5 دقايق بنفس الجلسة)")

    if not _provider_recently_failed(f"{provider_key_base}_bing"):
        try:
            q = quote(query)
            url = f"https://www.bing.com/news/search?q={q}&format=RSS"
            resp = req.get(url, timeout=6, headers=headers)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:max_items]
            headlines = _parse_items(items)
            if headlines:
                _mark_provider_ok(f"{provider_key_base}_bing")
                return headlines, None
            errors.append("Bing News: رجّع رد من غير أي أخبار")
        except Exception as e:
            _mark_provider_failed(f"{provider_key_base}_bing")
            errors.append(f"Bing News: {e}")
    else:
        errors.append("Bing News: تم تخطيه مؤقتاً (فشل قبل كده في آخر 5 دقايق بنفس الجلسة)")

    return [], " | ".join(errors)


def fetch_all_macro_news(max_items_per_query=4):
    """
    بدل استعلام عام واحد غامض بيرجّع أخبار مالية عامة مش بالضرورة حديثة أو مرتبطة، بندوّر
    بعدة استعلامات مستهدفة منفصلة (كل واحد لموضوع محدد) وبعدين ندمج النتايج، نشيل التكرار،
    ونرتبها زمنياً مع بعض - عشان نغطي مواضيع مختلفة فعلاً (حروب، ذهب، دولار، البورصة نفسها)
    بدل ما استعلام واحد طويل يشتت جوجل نيوز ويرجع نتايج عامة مش دقيقة.
    """
    from datetime import datetime as _dt

    queries = [
        "أسعار الذهب اليوم",
        "سعر الدولار اليوم مقابل الجنيه المصري",
        "البورصة المصرية اليوم EGX",
        "حرب صراع عسكري تأثير الأسواق العالمية",
        "أسواق المال العالمية اليوم",
    ]

    all_items = []
    all_errors = []
    seen_titles = set()
    for q in queries:
        items, err = fetch_macro_news(q, max_items=max_items_per_query, freshness_days=2)
        if err:
            all_errors.append(err)
        for it in items:
            key = it["title"].strip()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            all_items.append(it)

    if not all_items:
        return [], " | ".join(all_errors) if all_errors else "مفيش نتائج من أي استعلام"

    def _sort_key(item):
        try:
            return _dt.strptime(item["date"], "%Y-%m-%d %H:%M")
        except Exception:
            return _dt.min

    all_items.sort(key=_sort_key, reverse=True)
    return all_items, None


