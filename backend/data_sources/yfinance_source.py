"""
ياهو فاينانس: المصدر الأساسي للتاريخ الطويل ولبيانات الإطارات غير اليومية. نستخدم
stockanalysis للتحقق من السعر اللحظي وكمسار احتياطي فقط، لأنه لا يقدم تاريخاً كافياً
لعوائد 3/6/12 شهراً أو SMA200.
"""
import time
import pandas as pd
import yfinance as yf
from config import ISIN_BACKUP_MAP
from data_sources.investing_source import fetch_investing_history
from data_sources.stockanalysis_source import fetch_stockanalysis_history
from utils.cache import ttl_cache

@ttl_cache(300)
def fetch_raw_history(ticker_symbol, interval, period, company_name=None, use_investing_primary=False):
    """
    ترتيب المصادر للإطار اليومي:
    1) investing.com (لو مفعّل من الشريط الجانبي)
    2) ياهو فاينانس المباشر (التاريخ الطويل للمؤشرات والعوائد)
    3) ياهو فاينانس بالـ ISIN البديل
    4) stockanalysis.com كاحتياط أخير يومي؛ صفحته لا تعطي عادة إلا ~50 جلسة.
    الإطارات غير اليومية تعتمد على ياهو لأنه المصدر المجاني المتاح للشموع داخل اليوم.
    مع كاش لمدة 5 دقائق عشان لو المستخدم بدّل الإطار الزمني ميحصلش تحميل متكرر.
    """
    if interval == "1d":
        if use_investing_primary and company_name:
            df = fetch_investing_history(ticker_symbol, company_name)
            if df is not None and not df.empty:
                return df

    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period=period, interval=interval)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    if ticker_symbol in ISIN_BACKUP_MAP:
        isin_ticker = ISIN_BACKUP_MAP[ticker_symbol]
        try:
            stock = yf.Ticker(isin_ticker)
            df = stock.history(period=period, interval=interval)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

    if interval == "1d":
        df = fetch_stockanalysis_history(ticker_symbol)
        if df is not None and not df.empty:
            return df

    return None


def get_stock_data(ticker_symbol, timeframe_cfg, rate_limit_delay=0.0, company_name=None, use_investing_primary=False):
    """يحمّل بيانات السهم بالإطار الزمني المطلوب، وبيعمل تجميع (Resample) لو مطلوب (ساعتين/4 ساعات)."""
    if rate_limit_delay:
        time.sleep(rate_limit_delay)

    df = fetch_raw_history(ticker_symbol, timeframe_cfg["interval"], timeframe_cfg["period"],
                            company_name=company_name, use_investing_primary=use_investing_primary)
    if df is None or df.empty:
        return None

    resample_rule = timeframe_cfg.get("resample")
    if resample_rule:
        try:
            df = df.resample(resample_rule, label="right", closed="right").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            })
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
        except Exception:
            return None

    return df

