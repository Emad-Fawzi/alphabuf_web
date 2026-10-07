"""
مصدر تحقق إضافي (stockanalysis.com) من سعر السوق وتاريخه: مصدر خفيف (طلب واحد بس
لكل السوق للسعر اللحظي، أو صفحة واحدة للتاريخ لكل سهم عند الحاجة)، بدون مخاطرة Cloudflare
زي investing.com.
"""
import re
import pandas as pd
from utils.cache import ttl_cache

@ttl_cache(300)
def fetch_price_verification_snapshot():
    """
    مصدر تحقق إضافي وأسرع تحديثًا من ياهو فاينانس: بيجيب أحدث سعر إقفال ونسبة تغيّر
    لكل أسهم البورصة المصرية بطلب واحد بس من stockanalysis.com (مش طلب لكل سهم لوحده)،
    ويُستخدم بعدين لتصحيح آخر سعر وآخر نسبة تغيّر في نتائج ياهو فاينانس لو كانت متأخرة.
    البيانات التاريخية (للمؤشرات الفنية زي RSI وMACD) لسه بتيجي من ياهو فاينانس لأنه
    المصدر المجاني الوحيد اللي بيدي تاريخ شموع كامل بسهولة.
    ملحوظة: لو الموقع غيّر شكل الصفحة أو منع الطلبات الآلية، الدالة بترجع قاموس فاضي
    والسكريبت بيرجع تلقائيًا يعتمد على سعر ياهو فاينانس بس من غير ما يقف أو يدّي خطأ.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(
            "https://stockanalysis.com/list/egyptian-stock-exchange/",
            headers=headers, timeout=12
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if table is None:
            return {}

        headers_row = [th.get_text(strip=True) for th in table.find_all("th")]
        try:
            sym_idx = next(i for i, h in enumerate(headers_row) if "Symbol" in h)
            price_idx = next(i for i, h in enumerate(headers_row) if "Price" in h)
            chg_idx = next(i for i, h in enumerate(headers_row) if "Change" in h)
        except StopIteration:
            return {}

        snapshot = {}
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) <= max(sym_idx, price_idx, chg_idx):
                continue
            symbol = cells[sym_idx].get_text(strip=True).upper()
            if not symbol:
                continue
            try:
                price = float(cells[price_idx].get_text(strip=True).replace(",", ""))
            except ValueError:
                continue
            chg_text = cells[chg_idx].get_text(strip=True).replace("%", "").replace(",", "")
            try:
                change_pct = float(chg_text)
            except ValueError:
                change_pct = None
            snapshot[symbol] = {"price": price, "change_pct": change_pct}
        return snapshot
    except Exception:
        return {}


@ttl_cache(300)
def fetch_stockanalysis_history(ticker_symbol):
    """
    مصدر احتياطي ثالث (بعد ياهو فاينانس المباشر ثم الـ ISIN البديل): بيجيب آخر ~50 يوم تداول
    من صفحة السجل التاريخي في stockanalysis.com لو ياهو فاينانس فشل تماماً في جلب بيانات السهم.
    البيانات هنا صفحة واحدة بس (~2.5 شهر) فمش بديل كامل لياهو فاينانس، لكنها كافية كحل أخير
    عشان نقدر نحسب المؤشرات الأساسية بدل ما السهم يستبعد تماماً بسبب "لا توجد بيانات".
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        symbol = ticker_symbol.replace(".CA", "")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(f"https://stockanalysis.com/quote/egx/{symbol}/history/",
                             headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if table is None:
            return None

        headers_row = [th.get_text(strip=True) for th in table.find_all("th")]
        col_idx = {}
        for i, h in enumerate(headers_row):
            hl = h.lower()
            if "date" in hl:
                col_idx["date"] = i
            elif "open" in hl:
                col_idx["open"] = i
            elif "high" in hl:
                col_idx["high"] = i
            elif "low" in hl:
                col_idx["low"] = i
            elif hl == "close" or hl.startswith("close"):
                col_idx.setdefault("close", i)
            elif "volume" in hl:
                col_idx["volume"] = i

        required = {"date", "open", "high", "low", "close", "volume"}
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
                v_txt = cells[col_idx["volume"]].get_text(strip=True).replace(",", "")
                v = float(v_txt) if v_txt not in ("", "-") else 0.0
            except (ValueError, IndexError):
                continue
            rows.append({"Date": date, "Open": o, "High": h, "Low": l, "Close": c, "Volume": v})

        if not rows:
            return None

        result_df = pd.DataFrame(rows).set_index("Date").sort_index()
        # رفعنا الحد الأدنى من 15 لـ 45 صف (الصفحة بتدّي ~50 صف بحد أقصى) عشان متوسط 50 يوم
        # (SMA50) يتحسب من بيانات حقيقية كافية، مش نافذة مختصرة بتدّي إشارة مضلِّلة (لاحظنا
        # مشكلة حقيقية مع بعض الأسهم كانت بتدّي إشارة "قاع" غلط بسبب نافذة بيانات قصيرة).
        # كمان بنتأكد إن آخر تاريخ في البيانات مش قديم أكتر من أسبوع، عشان نرفض أي بيانات
        # قديمة/مخبأة (cached) بالغلط بدل ما نستخدمها وهي مش عاكسة للسعر الحالي فعلياً.
        if len(result_df) < 45 or result_df["Close"].nunique() <= 1:
            return None
        last_date = result_df.index.max()
        now = pd.Timestamp.now(tz=last_date.tz) if last_date.tz is not None else pd.Timestamp.now()
        days_old = (now - last_date).days
        if days_old > 7:
            return None
        return result_df
    except Exception:
        return None


