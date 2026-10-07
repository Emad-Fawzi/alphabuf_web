"""
investing.com كمصدر ثانوي (اختياري، للإطار اليومي فقط) للسعر، البيانات الأساسية، والتاريخ.
الموقع محمي بـ Cloudflare ومفيش API رسمي مجاني، فكل الدوال هنا ترجع نتيجة فاضية بهدوء لو
فشلت من غير ما توقف أي حاجة تانية في الأداة. البحث بيتم بكود السهم أولاً (مش الاسم العربي)
لأن فهرس بحث investing.com إنجليزي أساساً، مع تفضيل صريح للنتيجة اللي عليها علامة "EGX:"
لتفادي سحب GDR/ADR لنفس الشركة من بورصة تانية بعملة مختلفة (مشكلة حقيقية واجهناها مع COMI).
"""
import re
import pandas as pd
from utils.provider_health import provider_recently_failed as _provider_recently_failed
from utils.provider_health import mark_provider_failed as _mark_provider_failed
from utils.provider_health import mark_provider_ok as _mark_provider_ok
from utils.cache import ttl_cache

def _find_egx_equity_link(soup):
    """
    investing.com بيدرج نفس الشركة أحياناً على أكتر من بورصة (مثال حقيقي: COMI مقيد في EGX
    وكمان GDR في لندن (COMIq) وADR في السوق الأمريكي OTC (CIBEY) - بعملات وأسعار مختلفة
    خالص). لو أخدنا أول نتيجة بحث عمياني ممكن نلقط السهم الغلط تماماً (بورصة تانية، عملة
    تانية). الدالة دي بتدوّر على كل روابط /equities/ وتفضّل أي واحد جنبه "EGX:" تحديداً
    (تعليم البورصة الرسمي)، مش مجرد كلمة "Egypt" اللي ممكن تكون جزء من اسم الشركة القانوني
    حتى لو مقيدة فعلياً في بورصة تانية (زي "Commercial International Bank Egypt SAE" اللي
    ظهرت في نتيجة بحث حقيقية وهي مقيدة في لندن مش في مصر).
    """
    candidates = soup.find_all("a", href=re.compile(r"^/equities/"))
    if not candidates:
        return None
    for tag in candidates:
        context = tag.get_text(" ", strip=True)
        parent_context = tag.find_parent().get_text(" ", strip=True) if tag.find_parent() else ""
        combined = f"{context} {parent_context}"
        if "EGX:" in combined or "(EGX)" in combined:
            return tag
    return candidates[0]


def fetch_investing_snapshot(ticker_symbol, company_name=None):
    """
    investing.com كأولوية: بندوّر بكود السهم (COMI مثلاً) مش بالاسم العربي، لأن فهرس بحث
    investing.com إنجليزي أساساً وغالباً مش هيلاقي تطابق كويس مع اسم شركة بالعربي، بينما
    كود السهم كلمة إنجليزية دايماً وأقرب لصيغة البحث بتاعتهم. لو البحث بالكود فشل، بنجرب
    الاسم كاحتياطي أخير بس. بنفضّل النتيجة اللي عليها علامة EGX/Egypt عشان نتجنب سحب
    GDR/ADR لنفس الشركة من بورصة تانية بعملة مختلفة (شفنا المشكلة دي فعلياً مع COMI).
    ملحوظة أمانة: صفحة البحث العامة بتاعة investing.com غالباً متظبطة على أسماء الشركات
    مش أكواد قصيرة زي COMI، يعني حتى لو الكود صح ممكن ميرجعش نتيجة والكود يقع تلقائياً
    على البحث بالاسم - ده سلوك متوقع من الموقع نفسه مش خطأ في الكود.
    الموقع محمي بـ Cloudflare ومفيش API رسمي مجاني، فالدالة دي بترجع None بهدوء لو فشلت
    من غير ما توقف أي حاجة تانية في الأداة.
    """
    if _provider_recently_failed("investing_snapshot"):
        from urllib.parse import quote
        symbol = ticker_symbol.replace(".CA", "")
        return {"url": f"https://www.investing.com/search/?q={quote(symbol)}",
                "price": None, "skipped": True}
    try:
        import requests as req
        from bs4 import BeautifulSoup
        from urllib.parse import quote

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        symbol = ticker_symbol.replace(".CA", "")

        # الخطوة 1: البحث بكود السهم أولاً
        search_url = f"https://www.investing.com/search/?q={quote(symbol)}"
        search_resp = req.get(search_url, headers=headers, timeout=6)
        search_resp.raise_for_status()
        soup = BeautifulSoup(search_resp.text, "html.parser")
        link_tag = _find_egx_equity_link(soup)

        # لو البحث بالكود ملقاش حاجة وعندنا اسم الشركة، نجرب بيه كاحتياطي أخير
        if (not link_tag or not link_tag.get("href")) and company_name:
            search_url = f"https://www.investing.com/search/?q={quote(company_name)}"
            search_resp = req.get(search_url, headers=headers, timeout=6)
            search_resp.raise_for_status()
            soup = BeautifulSoup(search_resp.text, "html.parser")
            link_tag = _find_egx_equity_link(soup)

        if not link_tag or not link_tag.get("href"):
            _mark_provider_ok("investing_snapshot")  # الاتصال نجح، بس مفيش نتيجة مطابقة
            # حتى لو الاتنين فشلوا (بالكود والاسم)، نرجّع رابط بحث بالكود دايماً - ده اللي
            # المستخدم هيشوفه لو ضغط، فمفيش داعي يبقى بحث بالاسم العربي أبداً
            return {"url": f"https://www.investing.com/search/?q={quote(symbol)}", "price": None}

        equity_url = "https://www.investing.com" + link_tag["href"]

        # الخطوة 2: محاولة استخراج السعر من صفحة السهم نفسها
        price = None
        try:
            page_resp = req.get(equity_url, headers=headers, timeout=6)
            page_resp.raise_for_status()
            page_soup = BeautifulSoup(page_resp.text, "html.parser")
            price_tag = page_soup.find(attrs={"data-test": "instrument-price-last"})
            if price_tag:
                price = float(price_tag.get_text(strip=True).replace(",", ""))
        except Exception:
            pass

        _mark_provider_ok("investing_snapshot")
        return {"url": equity_url, "price": price}
    except Exception:
        _mark_provider_failed("investing_snapshot")
        from urllib.parse import quote
        symbol = ticker_symbol.replace(".CA", "")
        return {"url": f"https://www.investing.com/search/?q={quote(symbol)}", "price": None}


def fetch_investing_fundamentals(equity_url):
    """
    بيجيب مؤشرات أساسية (P/E، العائد على حقوق الملكية، الديون/حقوق الملكية، توزيعات الأرباح)
    وآخر ربع سنوي متاح مجاناً (الإيرادات وصافي الربح) من صفحة "Financial Summary" بتاعة السهم
    (مؤكدة من صفحة حقيقية بعتها المستخدم: investing.com/equities/{slug}-financial-summary).
    الاستخراج هنا بيدوّر على نص التسمية نفسه (زي "P/E Ratio") مش على أسماء كلاسات CSS داخلية،
    عشان يبقى أكتر مقاومة لو الموقع غيّر تصميمه شكلياً.
    ملحوظة أمانة: اتأكد الرابط والمحتوى من سكرين شوت حقيقي، لكن ترتيب العناصر جوه الـ HTML
    الخام لسه تخمين مبني على شكل الصفحة، مش الكود الفعلي - محتمل يحتاج ضبط لو مانفعش تمام.
    """
    if _provider_recently_failed("investing_fundamentals"):
        return {}
    try:
        import requests as req
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        summary_url = equity_url.rstrip("/") + "-financial-summary"
        resp = req.get(summary_url, headers=headers, timeout=6)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        def _label_value(label_text):
            label_el = soup.find(string=lambda s: s and s.strip() == label_text)
            if not label_el:
                return None
            container = label_el.find_parent()
            if container is not None:
                sibling = container.find_next_sibling()
                if sibling:
                    text = sibling.get_text(strip=True)
                    if text:
                        return text
            nxt = label_el.find_next(string=True)
            return nxt.strip() if nxt else None

        fundamentals = {}
        for label, key in [
            ("P/E Ratio", "pe_ratio"),
            ("Price/Book", "price_book"),
            ("Debt / Equity", "debt_equity"),
            ("Return on Equity", "roe"),
            ("Dividend Yield", "dividend_yield"),
            ("EBITDA", "ebitda"),
        ]:
            val = _label_value(label)
            if val:
                fundamentals[key] = val

        # آخر ربع سنوي متاح مجاناً: الصفحة ممكن تعرض جدول "Annual" افتراضياً (لسه معندناش
        # تأكيد لو ده صحيح 100%)، فبندوّر على كل الصفوف اللي فيها نفس التسمية (مش أول واحدة
        # بس) ونختار الصف اللي فيه أكتر عدد قيم حقيقية (غالباً الربع سنوي لأنه اللي كان
        # ظاهر مجاني في السكرين شوت). كمان بنستبعد القيم اللي شكلها "0.00"/"00.00" تحديداً
        # لأن دي بالظبط القيمة الوهمية اللي بتظهر مكان الخانات المقفولة (Pro) في السكرين شوت -
        # أخدها كأنها رقم حقيقي كان بيدّي "صفر" مضلِّل بدل ما يقول "البيانات دي مقفولة".
        for label, key in [("Total Revenues", "latest_quarter_revenue"),
                            ("Net Income", "latest_quarter_net_income")]:
            row_labels = soup.find_all(string=lambda s: s and s.strip() == label)
            best_values = []
            for row_label in row_labels:
                row = row_label.find_parent("tr") or row_label.find_parent()
                if not row:
                    continue
                values = []
                for cell in row.find_all(["td", "div"], recursive=True):
                    text = cell.get_text(strip=True)
                    if text in ("0.00", "00.00", "-", ""):
                        continue
                    try:
                        float(text.replace(",", ""))
                        values.append(text)
                    except ValueError:
                        continue
                if len(values) > len(best_values):
                    best_values = values
            if best_values:
                fundamentals[key] = best_values[-1]  # آخر قيمة حقيقية = أحدث ربع متاح مجاناً

        _mark_provider_ok("investing_fundamentals")
        return fundamentals
    except Exception:
        _mark_provider_failed("investing_fundamentals")
        return {}



@ttl_cache(300)
def fetch_investing_history(ticker_symbol, company_name=None):
    """
    investing.com كمصدر أساسي للتاريخ (بالإطار اليومي بس): بندوّر بكود السهم أولاً (مش الاسم
    العربي - فهرس بحثهم إنجليزي أساساً)، نلاقي صفحة السهم، وبعدين نروح لصفحة "historical-data"
    بتاعته ونستخرج منها الشموع. لو البحث بالكود فشل، بنجرب الاسم كاحتياطي أخير.
    ملحوظة أداء مهمة: ده بيضيف لغاية طلبين HTTP لكل سهم (بحث + صفحة التاريخ)، يعني فحص كامل
    لـ 232 سهم ممكن يبقى أبطأ بشكل ملحوظ ويزوّد فرصة إن investing.com يعمل حجب مؤقت (Cloudflare)
    لو الطلبات كتير في وقت قصير. لو حصل كده، الكود بيرجع تلقائي لياهو فاينانس من غير ما يوقف الفحص.
    """
    if _provider_recently_failed("investing_history"):
        return None
    try:
        import requests as req
        from bs4 import BeautifulSoup
        from urllib.parse import quote

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        symbol = ticker_symbol.replace(".CA", "")

        search_url = f"https://www.investing.com/search/?q={quote(symbol)}"
        search_resp = req.get(search_url, headers=headers, timeout=6)
        search_resp.raise_for_status()
        soup = BeautifulSoup(search_resp.text, "html.parser")
        link_tag = _find_egx_equity_link(soup)

        if (not link_tag or not link_tag.get("href")) and company_name:
            search_url = f"https://www.investing.com/search/?q={quote(company_name)}"
            search_resp = req.get(search_url, headers=headers, timeout=6)
            search_resp.raise_for_status()
            soup = BeautifulSoup(search_resp.text, "html.parser")
            link_tag = _find_egx_equity_link(soup)

        if not link_tag or not link_tag.get("href"):
            _mark_provider_ok("investing_history")
            return None

        slug = link_tag["href"].rstrip("/").split("/")[-1]
        hist_url = f"https://www.investing.com/equities/{slug}-historical-data"

        hist_resp = req.get(hist_url, headers=headers, timeout=6)
        hist_resp.raise_for_status()
        hist_soup = BeautifulSoup(hist_resp.text, "html.parser")
        table = hist_soup.find("table")
        if table is None:
            return None

        headers_row = [th.get_text(strip=True) for th in table.find_all("th")]
        col_idx = {}
        for i, h in enumerate(headers_row):
            hl = h.lower()
            if "date" in hl:
                col_idx["date"] = i
            elif hl in ("price", "close"):
                col_idx.setdefault("close", i)
            elif "open" in hl:
                col_idx["open"] = i
            elif "high" in hl:
                col_idx["high"] = i
            elif "low" in hl:
                col_idx["low"] = i
            elif "vol" in hl:
                col_idx["volume"] = i

        required = {"date", "open", "high", "low", "close"}
        if not required.issubset(col_idx.keys()):
            return None

        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) <= max(col_idx.values()):
                continue
            try:
                date = pd.to_datetime(cells[col_idx["date"]].get_text(strip=True))
                o = float(cells[col_idx["open"]].get_text(strip=True).replace(",", ""))
                h = float(cells[col_idx["high"]].get_text(strip=True).replace(",", ""))
                l = float(cells[col_idx["low"]].get_text(strip=True).replace(",", ""))
                c = float(cells[col_idx["close"]].get_text(strip=True).replace(",", ""))
                v = 0.0
                if "volume" in col_idx:
                    v_txt = cells[col_idx["volume"]].get_text(strip=True).upper().replace(",", "")
                    if v_txt.endswith("K"):
                        v = float(v_txt[:-1]) * 1_000
                    elif v_txt.endswith("M"):
                        v = float(v_txt[:-1]) * 1_000_000
                    elif v_txt not in ("", "-"):
                        v = float(v_txt)
            except (ValueError, IndexError):
                continue
            rows.append({"Date": date, "Open": o, "High": h, "Low": l, "Close": c, "Volume": v})

        if not rows:
            return None

        result_df = pd.DataFrame(rows).set_index("Date").sort_index()
        # فحص جودة البيانات: لو الصفوف قليلة جداً أو كل الأسعار متطابقة (صفحة اترجعت جزئياً
        # أو محجوبة)، البيانات دي مش موثوقة لحساب مؤشرات فنية أو نسبة تغيّر حقيقية، فبنرفضها
        # ونسيب الكود يرجع لياهو فاينانس بدل ما نستخدم بيانات مضلِّلة (كانت بتسبب ظهور
        # "متوسط التغير %" صفر دايماً في الفريم اليومي لما investing.com يرجّع بيانات ناقصة).
        # رفعنا الحد لـ 55 صف عشان متوسط 50 يوم (SMA50) يتحسب من بيانات حقيقية كافية،
        # وضفنا فحص حداثة (آخر تاريخ مش أقدم من أسبوع) عشان نرفض بيانات قديمة/مخبأة بالغلط
        # (لاحظنا حالة حقيقية لسهم ظهر بإشارة "قاع" غلط بسبب نافذة بيانات قصيرة/قديمة).
        if len(result_df) < 55 or result_df["Close"].nunique() <= 1:
            return None
        last_date = result_df.index.max()
        now = pd.Timestamp.now(tz=last_date.tz) if last_date.tz is not None else pd.Timestamp.now()
        if (now - last_date).days > 7:
            return None
        _mark_provider_ok("investing_history")
        return result_df
    except Exception:
        _mark_provider_failed("investing_history")
        return None


