"""
المحرك الأساسي للتحليل الفني: بيحمّل بيانات سهم واحد، يحسب المؤشرات القياسية (SMA، RSI،
MACD، Bollinger Bands، Stochastic، OBV، نسبة السيولة)، وبيولّد توصية سوينغ (مضاربة قصيرة
المدى) وتوصية مالك (استثمار متوسط/طويل المدى) مع مستويات دخول/خروج ووقف خسارة، وتصنيف
نوع السهم (مضاربي/نمو/استثماري) بناءً على التقلب والاتجاه.
"""
import pandas as pd
import numpy as np
from utils.formatting import fmt_thousands, bidi_safe
from data_sources.yfinance_source import get_stock_data
from data_sources.mubasher_source import fetch_mubasher_snapshot


def _classify_stock_profile(close_price, sma_20, sma_50, sma_200, daily_volatility):
    """Classify the chart's growth/trend and volatility profile; this is not a business-quality rating."""
    has_long_history = pd.notna(sma_200)
    strong_long_trend = has_long_history and close_price > sma_200 and sma_50 > sma_200
    positive_medium_trend = close_price > sma_50 and sma_20 > sma_50

    if daily_volatility >= 3.5:
        profile = "مضاربي عالي المخاطر"
        risk = "مرتفع جدًا"
        rationale = "تذبذب يومي تاريخي مرتفع (3.5% أو أكثر)؛ يلزم حجم مركز صغير وحد خسارة واضح."
    elif daily_volatility >= 2.5:
        profile = "مضاربي"
        risk = "مرتفع"
        rationale = "تذبذبه اليومي مرتفع نسبيًا؛ مناسب لوصف حركة السعر لا لجودة الشركة."
    elif strong_long_trend and daily_volatility < 2.5:
        profile = "نمو فني قوي"
        risk = "متوسط"
        rationale = "السعر ومتوسط 50 يوم فوق متوسط 200 يوم، مع تذبذب يومي دون 2.5%."
    elif strong_long_trend:
        profile = "نمو فني متقلب"
        risk = "مرتفع"
        rationale = "الاتجاه الطويل إيجابي لكن التذبذب اليومي أعلى من 2.5%."
    elif positive_medium_trend:
        profile = "اتجاه صاعد متوسط الأجل"
        risk = "متوسط"
        rationale = "متوسطا 20 و50 يوم يدعمان الاتجاه، لكن تأكيد الاتجاه الطويل غير مكتمل."
    elif has_long_history and close_price < sma_200:
        profile = "اتجاه هابط / تعافٍ غير مؤكد"
        risk = "مرتفع"
        rationale = "السعر دون متوسط 200 يوم؛ لا يصنف كنمو فني حتى يظهر تأكيد اتجاه."
    else:
        profile = "غير محسوم — تاريخ غير كافٍ"
        risk = "غير محدد"
        rationale = "لا تتوفر بيانات طويلة كافية لتأكيد تصنيف نمو أو استثمار."

    return profile, risk, rationale


def _screen_sharia_by_activity(sector):
    """Preliminary business-activity screen only; accounting ratios and Sharia review are not available."""
    if sector in {"تبغ", "مشروبات كحولية"}:
        return "غير متوافق مبدئيًا — نشاط محظور", "تنبيه نشاط أولي فقط، وليس فتوى أو تدقيقًا شرعيًا معتمدًا."
    if sector == "البنوك":
        return "غير محسوم — نشاط مصرفي مختلط", "يضم القطاع بنوكًا مختلفة؛ يلزم فحص نشاط البنك نفسه ومعياره الشرعي ونسبه المالية."
    if sector == "التأمين":
        return "مراجعة شرعية لازمة — التأمين", "تصنيف النشاط وحده لا يحسم نوع التأمين أو آلية الاستثمار."
    if sector in {"الخدمات المالية غير المصرفية والصناديق", "استثمار وتمويل وائتمان", "الأنشطة المالية المتنوعة", "وساطة وإدارة أصول"}:
        return "غير محسوم — نشاط مالي مختلط", "يلزم فحص مصادر الإيراد والديون والنسب المالية وفق معيار شرعي محدد."
    return "غير محسوم — النسب المالية غير مفحوصة", "لم تُفحص القوائم المالية أو الديون أو النقد/الفوائد أو الإيرادات غير المتوافقة؛ هذا ليس اعتمادًا شرعيًا."


def _estimate_daily_move_ranges(df, close_price, timeframe_cfg):
    """Estimate one-standard-deviation price-move ranges from daily history, not target profits."""
    if timeframe_cfg.get("interval") != "1d" or timeframe_cfg.get("resample") is not None:
        return {label: None for label in ("أسبوع", "شهر", "ربع سنوي", "نصف سنوي", "سنوي")}

    returns = df["Close"].pct_change().tail(60).replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 15:
        return {label: None for label in ("أسبوع", "شهر", "ربع سنوي", "نصف سنوي", "سنوي")}

    periods = {"أسبوع": 5, "شهر": 21, "ربع سنوي": 63, "نصف سنوي": 126, "سنوي": 252}
    daily_drift = float(returns.mean())
    daily_volatility = float(returns.std())
    ranges = {}
    for label, trading_days in periods.items():
        center_pct = daily_drift * trading_days
        radius_pct = daily_volatility * np.sqrt(trading_days)
        low_pct = max(-95.0, (center_pct - radius_pct) * 100)
        high_pct = (center_pct + radius_pct) * 100
        ranges[label] = {
            "low_pct": round(float(low_pct), 1),
            "high_pct": round(float(high_pct), 1),
            "low_price": round(float(close_price * (1 + low_pct / 100)), 2),
            "high_price": round(float(close_price * (1 + high_pct / 100)), 2),
        }
    return ranges


def _historical_price_returns(df, timeframe_cfg):
    """Calculate observed price changes from past daily closes; unavailable for non-daily scans."""
    labels = {"ربع سنوي": 63, "نصف سنوي": 126, "سنوي": 252}
    if timeframe_cfg.get("interval") != "1d" or timeframe_cfg.get("resample") is not None:
        return {label: None for label in labels}

    returns = {}
    for label, trading_bars in labels.items():
        if len(df) <= trading_bars:
            returns[label] = None
            continue
        past_close = float(df["Close"].iloc[-(trading_bars + 1)])
        current_close = float(df["Close"].iloc[-1])
        if not np.isfinite(past_close) or past_close <= 0 or not np.isfinite(current_close):
            returns[label] = None
            continue
        returns[label] = round((current_close / past_close - 1) * 100, 2)
    return returns


def analyze_stock(sector, item, timeframe_cfg, min_daily_turnover, rate_limit_delay=0.0, price_snapshot=None,
                   use_investing_primary=False):
    """يحمّل بيانات سهم واحد، يحسب المؤشرات الفنية، ويرجّع نتيجة مقبولة أو سبب استبعاد."""
    ticker_symbol = item["ticker"]
    arabic_name = item["name"]

    df = get_stock_data(ticker_symbol, timeframe_cfg, rate_limit_delay=rate_limit_delay,
                         company_name=arabic_name, use_investing_primary=use_investing_primary)

    if df is None or df.empty:
        return None, {"القطاع": sector, "اسم الشركة": arabic_name, "الرمز": ticker_symbol,
                       "سبب الاستبعاد": "بيانات فارغة / غير مسجل في ياهو فاينانس"}

    if len(df) < 15:
        return None, {"القطاع": sector, "اسم الشركة": arabic_name, "الرمز": ticker_symbol,
                       "سبب الاستبعاد": f"عدد الشمعات المتاحة غير كافٍ ({len(df)} شمعة فقط)"}

    try:
        window_20 = min(20, len(df))
        window_50 = min(50, len(df))
        window_14 = min(14, len(df))

        df['SMA_20'] = df['Close'].rolling(window=window_20).mean()
        df['SMA_50'] = df['Close'].rolling(window=window_50).mean()
        # متوسط 200 يوم: مش بنقصّر النافذة زي الـ20/50 لو البيانات ناقصة - لازم 200 يوم
        # حقيقية بالظبط، وإلا القيمة تفضل NaN (مؤشر "أسهم النمو" مبني عليه محتاج دقة حقيقية
        # مش نافذة مختصرة ممكن تدّي إشارة "تقاطع ذهبي" وهمية).
        df['SMA_200'] = df['Close'].rolling(window=200).mean()

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window_14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window_14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # مؤشر تدفق الأموال (MFI) - زي RSI بس بياخد الحجم في الاعتبار كمان، فبيعكس
        # دخول/خروج سيولة حقيقي مش مجرد تذبذب سعري بحجم عادي
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        raw_money_flow = typical_price * df['Volume']
        price_direction = typical_price.diff()
        positive_flow = raw_money_flow.where(price_direction > 0, 0).rolling(window=window_14).sum()
        negative_flow = raw_money_flow.where(price_direction < 0, 0).rolling(window=window_14).sum()
        money_flow_ratio = positive_flow / negative_flow
        df['MFI'] = 100 - (100 / (1 + money_flow_ratio))
        df['MFI'] = df['MFI'].replace([np.inf, -np.inf], 100)

        df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['BB_Mid'] = df['Close'].rolling(window=window_20).mean()
        df['BB_Std'] = df['Close'].rolling(window=window_20).std()
        df['BB_Up'] = df['BB_Mid'] + (2 * df['BB_Std'])
        df['BB_Low'] = df['BB_Mid'] - (2 * df['BB_Std'])
        df['BB_Squeeze'] = (df['BB_Up'] - df['BB_Low']) / df['BB_Mid']

        df['Low_14'] = df['Low'].rolling(window=window_14).min()
        df['High_14'] = df['High'].rolling(window=window_14).max()
        df['Stoch_K'] = 100 * ((df['Close'] - df['Low_14']) / (df['High_14'] - df['Low_14']))
        df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()

        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_Avg'] = df['OBV'].rolling(window=window_20).mean()

        df['Vol_Avg_20'] = df['Volume'].rolling(window=window_20).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close_price = latest['Close']
        volume = latest['Volume']

        # مصدر السعر: مباشر (mubasher.info) أولوية لأنه متخصص في سوق مصر ومجاني بالكامل
        # ورابط مباشر بالرمز من غير أي بحث. لو فشل لسهم معين (أو للإطارات غير اليومية)،
        # بنرجع لـ stockanalysis.com كباكاب. العمود بيوريك اسم الموقع الفعلي مش مجرد علامة
        # صح، عشان تعرف مصدر كل سعر بالظبط.
        price_source = ""
        is_daily_timeframe = timeframe_cfg.get("interval") == "1d" and timeframe_cfg.get("resample") is None
        snap = None
        mubasher_snap = None
        if is_daily_timeframe:
            mubasher_snap = fetch_mubasher_snapshot(ticker_symbol)
            if mubasher_snap and mubasher_snap.get("price"):
                snap = {"price": mubasher_snap["price"], "change_pct": mubasher_snap.get("change_pct")}
                price_source = "mubasher.info"
            elif price_snapshot:
                stockanalysis_snap = price_snapshot.get(ticker_symbol.replace(".CA", ""))
                if stockanalysis_snap and stockanalysis_snap.get("price"):
                    snap = stockanalysis_snap
                    price_source = "stockanalysis.com"
        if snap and snap.get("price"):
            close_price = snap["price"]

        # القيمة السوقية: من نفس استدعاء mubasher.info اللي جبنا منه السعر أصلاً (مفيش
        # تكلفة شبكة إضافية) - مطلوبة لفلتر "أسهم النمو" (شركات وزن حقيقي، مش أسهم صغيرة)
        market_cap = None
        if mubasher_snap and mubasher_snap.get("market_cap"):
            try:
                market_cap = float(str(mubasher_snap["market_cap"]).replace(",", ""))
            except (ValueError, TypeError):
                market_cap = None

        daily_turnover = close_price * volume

        if pd.isna(daily_turnover) or daily_turnover < min_daily_turnover:
            return None, {"القطاع": sector, "اسم الشركة": arabic_name, "الرمز": ticker_symbol,
                           "سبب الاستبعاد": f"السيولة أقل من الحد المطلوب ({fmt_thousands(daily_turnover)} ج.م)"}

        vol_ratio = volume / latest['Vol_Avg_20'] if latest['Vol_Avg_20'] > 0 else 0
        if snap and snap.get("change_pct") is not None:
            change_pct = snap["change_pct"]
        else:
            change_pct = ((close_price - prev['Close']) / prev['Close']) * 100

        rsi_val = latest['RSI']
        macd_val = latest['MACD']
        macd_sig = latest['MACD_Signal']
        stoch_k = latest['Stoch_K']
        stoch_d = latest['Stoch_D']
        bb_squeeze = latest['BB_Squeeze']
        obv_trend = "صاعد" if latest['OBV'] > latest['OBV_Avg'] else "هابط"

        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        sma_200 = latest['SMA_200']  # ممكن يبقى NaN لو مفيش 200 يوم بيانات حقيقية متاحة
        mfi_val = latest['MFI']
        bb_low_val = float(latest['BB_Low'])
        bb_up_val = float(latest['BB_Up'])
        low_14 = float(latest['Low_14'])
        high_14 = float(latest['High_14'])

        # === مستويات دخول/خروج وقف خسارة مقترحة (بتُحسب دايماً بغض النظر عن القرار،
        # عشان تصلح سواء كنت هتدخل جديد أو ماسك السهم بالفعل) ===
        support_level = low_14
        resistance_level = high_14
        suggested_buy = round(min(close_price, sma_20), 2)
        suggested_sell = round(max(close_price, bb_up_val), 2)
        stop_loss_level = round(support_level * 0.98, 2)
        take_profit_level = round(resistance_level * 1.03, 2)

        # === تصنيف نوع السهم (تصنيف فني مقترح بناءً على التقلب والاتجاه فقط —
        # مش بيشمل نوع "توزيعات" لأن ده محتاج بيانات عائد توزيعات مش متوفرة في هذا المصدر) ===
        daily_ret_std = df['Close'].pct_change().tail(20).std() * 100
        if pd.isna(daily_ret_std):
            daily_ret_std = 0
        stock_type, risk_level, profile_reason = _classify_stock_profile(
            close_price, sma_20, sma_50, sma_200, daily_ret_std
        )
        sharia_status, sharia_reason = _screen_sharia_by_activity(sector)
        estimated_moves = _estimate_daily_move_ranges(df, close_price, timeframe_cfg)
        historical_returns = _historical_price_returns(df, timeframe_cfg)

        # عدد الإشارات الصاعدة المتوافقة حالياً (لتقييم قوة القرار)
        bullish_signals = sum([
            close_price > sma_20,
            macd_val > macd_sig,
            obv_trend == "صاعد",
            stoch_k > stoch_d,
            rsi_val > 50
        ])
        if bullish_signals >= 4:
            confluence_note = "توافق قوي (4-5 من 5 مؤشرات صاعدة)"
        elif bullish_signals == 3:
            confluence_note = "توافق متوسط (3 من 5 مؤشرات صاعدة)"
        elif bullish_signals == 2:
            confluence_note = "توافق ضعيف (2 من 5 مؤشرات صاعدة)"
        else:
            confluence_note = "توافق هابط (مؤشر واحد أو صفر صاعد من 5)"

        swing_context = (
            f"📌 قراءة اللحظة: RSI عند {rsi_val:.1f}، ستوكاستيك K={stoch_k:.1f} وD={stoch_d:.1f}، "
            f"السيولة {vol_ratio:.2f}x المتوسط، عرض بولينجر (Squeeze)={bb_squeeze:.3f} "
            f"(نطاق بولينجر من {bb_low_val:.2f} إلى {bb_up_val:.2f})، "
            f"والسعر {'فوق' if close_price > sma_20 else 'تحت'} متوسط 20 يوم ({sma_20:.2f}). "
            f"أعلى وأدنى سعر في آخر 14 شمعة: {low_14:.2f} - {high_14:.2f}. قوة التوافق بين المؤشرات: {confluence_note}. "
        )

        if rsi_val <= 30 and stoch_k < 20 and stoch_k > stoch_d:
            speculation_rec = "🟢 اشترِ الآن (قاع محقق)"
            swing_explanation = swing_context + (
                f"القرار: اشترِ الآن (قاع محقق) — RSI دخل منطقة التشبع البيعي (تحت 30) وده معناه إن "
                f"ضغط البيع اللي كان حاصل بدأ يفقد قوته، وفي نفس الوقت الستوكاستيك K ({stoch_k:.1f}) "
                f"لسه تحت مستوى 20 (تشبع بيعي) بس عدّى فوق خط D ({stoch_d:.1f}) وده تقاطع صاعد مبكر "
                f"بيرمز لاحتمال ارتداد قريب. الدخول هنا بيكون على أساس مضاربي قصير المدى. "
                f"🎯 مستويات تقريبية: وقف خسارة تحت قاع الـ14 شمعة ({low_14:.2f})، وأول هدف عند متوسط "
                f"20 يوم ({sma_20:.2f}) أو الحد العلوي لبولينجر ({bb_up_val:.2f}) لمن يحتمل مخاطرة أعلى. "
                f"مستوى المخاطرة: متوسط إلى مرتفع (دخول مبكر على إشارة انعكاس لسه بتتأكد)."
            )
        elif vol_ratio >= 1.5 and bb_squeeze < 0.10 and close_price > sma_20:
            speculation_rec = "🔥 اشترِ الآن (انفجار متوقع)"
            swing_explanation = swing_context + (
                f"القرار: اشترِ الآن (انفجار متوقع) — نطاق بولينجر ضيق جداً (Squeeze={bb_squeeze:.3f}، "
                f"تحت 0.10) وده بيعني إن التذبذب قل جداً وعادة بيسبق حركة سعرية قوية في أي اتجاه، وحجم "
                f"التداول جه {vol_ratio:.2f} ضعف متوسطه (فوق 1.5x) وهي إشارة دخول سيولة حقيقية، والسعر "
                f"فوق متوسط 20 يوم يعني الاتجاه الحالي صاعد. التجميع في المنطقة دي بيكون قبل الانفجار "
                f"السعري المتوقع. "
                f"🎯 مستويات تقريبية: وقف خسارة تحت متوسط 20 يوم ({sma_20:.2f})، والهدف الأول عند كسر "
                f"أعلى الـ14 شمعة ({high_14:.2f}) مع احتمال امتداد الحركة لو استمر دخول السيولة. "
                f"مستوى المخاطرة: متوسط (الإشارة فنياً قوية بس التوقيت الدقيق للانفجار غير مؤكد)."
            )
        elif rsi_val > 75 or stoch_k > 80:
            speculation_rec = "⛔ لا تشترِ (تشبع شراء)"
            swing_explanation = swing_context + (
                f"القرار: لا تشترِ (تشبع شراء) — RSI عند {rsi_val:.1f}" +
                (" (فوق 75)" if rsi_val > 75 else "") +
                f" و/أو الستوكاستيك K عند {stoch_k:.1f}" + (" (فوق 80)" if stoch_k > 80 else "") +
                f"، وده معناه إن السهم اتشترى بسرعة وقوة أكبر من طبيعته وبقى معرّض لتصحيح أو جني أرباح "
                f"قريب. الدخول جديد في المنطقة دي مخاطرة عالية لأن أغلب الحركة الصاعدة السريعة اتاكلت "
                f"بالفعل. لو معاك السهم بالفعل، فكر في تسييل جزء وتحريك وقف الخسارة لمستوى متوسط "
                f"20 يوم ({sma_20:.2f}) لحماية المكسب. مستوى المخاطرة: مرتفع لأي دخول جديد الآن."
            )
        elif obv_trend == "هابط" and close_price < sma_20:
            speculation_rec = "❌ لا تشترِ (خروج سيولة)"
            swing_explanation = swing_context + (
                f"القرار: لا تشترِ (خروج سيولة) — مؤشر OBV بيقول إن حجم التداول بيتحرك في اتجاه هابط "
                f"رغم حركة السعر، وده علامة على إن كبار المتعاملين بيسحبوا سيولتهم من السهم، وبالإضافة "
                f"إن السعر حالياً تحت متوسط 20 يوم يعني الاتجاه قصير المدى ضعيف. الدخول هنا مش منطقي "
                f"لحد ما يرجع السعر يقفل فوق المتوسط بحجم تداول داعم. نقطة المتابعة القادمة: قفل يومي "
                f"فوق {sma_20:.2f} بحجم أعلى من المتوسط يبطّل الإشارة السلبية دي. مستوى المخاطرة: مرتفع "
                f"لأي دخول قبل ما تتأكد إشارة الانعكاس."
            )
        else:
            speculation_rec = "⏸️ انتظر (استقرار)"
            swing_explanation = swing_context + (
                f"القرار: انتظر (استقرار) — القراءات الحالية مش بتدّي إشارة واضحة لا للشراء ولا للبيع. "
                f"RSI ({rsi_val:.1f}) في المنطقة المحايدة، والستوكاستيك والحجم مش مؤكدين اتجاه معين. "
                f"الأفضل الانتظار لحد ما يظهر تقاطع واضح أو اختراق حقيقي بحجم تداول يدعمه. "
                f"نطاق المراقبة الحالي بين {low_14:.2f} (دعم) و{high_14:.2f} (مقاومة) — كسر أي منهم "
                f"بحجم تداول واضح ممكن يحدد الاتجاه القادم."
            )

        investor_context = (
            f"📌 السياق: السعر {close_price:.2f} مقابل متوسط 50 يوم {sma_50:.2f} "
            f"({'فوق' if close_price >= sma_50 else 'تحت'} بنسبة {abs(close_price / sma_50 - 1) * 100:.1f}%)، "
            f"MACD {'إيجابي' if macd_val > macd_sig else 'سلبي'} (MACD={macd_val:.3f} مقابل خط الإشارة "
            f"{macd_sig:.3f})، واتجاه السيولة (OBV) {obv_trend}. "
        )

        if rsi_val > 78 or close_price >= bb_up_val:
            investor_action = "💰 جني أرباح"
            investor_explanation = investor_context + (
                f"القرار: جني أرباح — " +
                (f"RSI وصل لـ {rsi_val:.1f} (منطقة تشبع شراء قوي فوق 78)" if rsi_val > 78 else "") +
                (" و" if rsi_val > 78 and close_price >= bb_up_val else "") +
                (f"السعر لمس أو تخطى الحد العلوي لبولينجر ({bb_up_val:.2f})" if close_price >= bb_up_val else "") +
                f". ده معناه إن السهم بقى ممدود سعرياً بشكل غير طبيعي وأغلب الصعود المتوقع حصل بالفعل، "
                f"فالأفضل تسييل جزء من المركز أو كله بدل ما تنتظر تصحيح يرجّع المكسب. لو قررت تحتفظ "
                f"بجزء، اعتبر متوسط 20 يوم ({sma_20:.2f}) خط الدفاع التالي لوقف الخسارة على الباقي."
            )
        elif close_price < sma_50 * 0.93:
            drop_pct = (1 - close_price / sma_50) * 100
            investor_action = "🚨 اخرج ووقف خسارة"
            investor_explanation = investor_context + (
                f"القرار: اخرج ووقف خسارة — السعر تحت متوسط 50 يوم بنسبة {drop_pct:.1f}% (تجاوز حد "
                f"الأمان 7%)، وده كسر واضح للاتجاه المتوسط وبيدل على ضعف هيكلي في السهم مش مجرد تصحيح "
                f"عادي. الاستمرار في الاحتفاظ هنا بيزود من احتمالية خسارة أكبر. لو عايز تراجع قرارك، "
                f"لازم السعر يقفل تاني فوق {sma_50:.2f} بحجم تداول داعم كإشارة تعافي حقيقية."
            )
        elif close_price >= sma_50 and macd_val > macd_sig and obv_trend == "صاعد":
            investor_action = "📈 استمر وزود كميات"
            investor_explanation = investor_context + (
                f"القرار: استمر وزود كميات — السعر فوق متوسط 50 يوم، MACD ({macd_val:.3f}) فوق خط "
                f"الإشارة ({macd_sig:.3f}) يعني الزخم صاعد، وOBV بيأكد إن السيولة بتدخل مش بتخرج. "
                f"التقاء الثلاث إشارات دي (اتجاه + زخم + سيولة) بيدي ثقة أعلى في استمرار الصعود، "
                f"فزيادة المركز هنا منطقية لمن يتحمل المخاطرة. وقف الخسارة المقترح على المركز الكامل "
                f"عند كسر متوسط 50 يوم ({sma_50:.2f})، والهدف التالي عند الحد العلوي لبولينجر "
                f"({bb_up_val:.2f}) إن استمر الزخم."
            )
        elif close_price >= sma_50:
            investor_action = "🛡️ احتفظ"
            investor_explanation = investor_context + (
                f"القرار: احتفظ — السعر لسه فوق متوسط 50 يوم يعني الاتجاه المتوسط سليم، بس باقي "
                f"المؤشرات (MACD أو OBV) مش بتدّي تأكيد كافي لزيادة المركز. الأنسب تثبيت الوضع الحالي "
                f"والمتابعة، مع اعتبار {sma_50:.2f} خط دفاع لو حصل كسر واضح تحته."
            )
        else:
            investor_action = "⏳ اصبر واستحمل"
            investor_explanation = investor_context + (
                f"القرار: اصبر واستحمل — السهم تحت متوسط 50 يوم بس لسه ما كسرش حد وقف الخسارة (7%). "
                f"المركز في منطقة رمادية: مش لازم خروج فوري، بس محتاج متابعة قريبة لأي كسر إضافي للدعم. "
                f"خط الإنذار: لو السعر قفل تحت {sma_50 * 0.93:.2f} (نسبة الـ7% من متوسط 50 يوم) بيتحول "
                f"القرار لـ«اخرج ووقف خسارة»."
            )

        # نظرة مزدوجة: بتفترض إنك "مش ماسك السهم" و"ماسك السهم بالفعل" في نفس الوقت،
        # عشان تدّيك نقطة دخول ونقطة خروج واضحة في كل الحالتين مهما كان القرار العام
        dual_strategy = bidi_safe(
            f"🅰️ لو مش ماسك السهم دلوقتي: نقطة دخول تقريبية عند {suggested_buy:.2f} أو أقرب "
            f"للدعم ({support_level:.2f})، وقف خسارة عند {stop_loss_level:.2f}، وهدف جني أرباح أول "
            f"عند {take_profit_level:.2f}. "
            f"🅱️ لو ماسك السهم بالفعل: استمر طالما السعر فوق {stop_loss_level:.2f}، فكّر في تسييل "
            f"جزء عند الاقتراب من {suggested_sell:.2f}، واعتبر {stop_loss_level:.2f} خط دفاعك الأخير "
            f"لو حصل كسر واضح تحته."
        )

        result = {
            "اسم الشركة": arabic_name,
            "الرمز": ticker_symbol.replace(".CA", ""),
            "القطاع": sector,
            "نوع السهم": stock_type,
            "مستوى المخاطرة": risk_level,
            "سبب التصنيف": profile_reason,
            "الفلتر الشرعي (أولي)": sharia_status,
            "شرح الفلتر الشرعي": sharia_reason,
            "السعر": round(float(close_price), 2),
            "مصدر السعر": price_source,
            "التغير %": round(float(change_pct), 2),
            "القيمة": round(float(daily_turnover), 0),
            "القيمة السوقية": round(market_cap, 0) if market_cap is not None else None,
            "الدعم": round(float(support_level), 2),
            "المقاومة": round(float(resistance_level), 2),
            "سعر شراء مقترح": suggested_buy,
            "سعر بيع مقترح": suggested_sell,
            "وقف الخسارة": stop_loss_level,
            "هدف جني الأرباح": take_profit_level,
            "تقدير أسبوع": estimated_moves["أسبوع"],
            "تقدير شهر": estimated_moves["شهر"],
            "تقدير ربع سنوي": estimated_moves["ربع سنوي"],
            "تقدير نصف سنوي": estimated_moves["نصف سنوي"],
            "تقدير سنوي": estimated_moves["سنوي"],
            "أداء تاريخي ربع سنوي %": historical_returns["ربع سنوي"],
            "أداء تاريخي نصف سنوي %": historical_returns["نصف سنوي"],
            "أداء تاريخي سنوي %": historical_returns["سنوي"],
            "قرار السوينغ": speculation_rec,
            "نصيحة المالك": investor_action,
            "RSI": round(float(rsi_val), 2),
            "MFI": round(float(mfi_val), 2) if pd.notna(mfi_val) else None,
            "Stoch K": round(float(stoch_k), 2),
            "OBV": obv_trend,
            "السيولة": round(float(vol_ratio), 2),
            "متوسط 50 يوم": round(float(sma_50), 2) if pd.notna(sma_50) else None,
            "متوسط 200 يوم": round(float(sma_200), 2) if pd.notna(sma_200) else None,
            "استراتيجية الدخول والخروج": dual_strategy,
            "شرح السوينغ": bidi_safe(swing_explanation),
            "شرح نصيحة المالك": bidi_safe(investor_explanation)
        }
        return result, None

    except Exception as e:
        return None, {"القطاع": sector, "اسم الشركة": arabic_name, "الرمز": ticker_symbol,
                       "سبب الاستبعاد": f"خطأ في حساب المؤشرات ({str(e)})"}


