"""
mubasher.info (النسخة العربية www.mubasher.info) - مصدر أساسي للسعر اللحظي، البيانات
الأساسية، الأخبار، وإعلانات السوق الرسمية. متخصص في سوق مصر تحديداً ومجاني بالكامل،
والرابط مباشر بكود السهم من غير أي بحث (مفيش خطر بورصة غلط زي investing.com).
"""
import re
from utils.provider_health import provider_recently_failed as _provider_recently_failed
from utils.provider_health import mark_provider_failed as _mark_provider_failed
from utils.provider_health import mark_provider_ok as _mark_provider_ok
from utils.cache import ttl_cache


@ttl_cache(300)
def fetch_mubasher_snapshot(ticker_symbol):
    """
    mubasher.info (النسخة العربية www.mubasher.info) كمصدر أساسي للسعر اللحظي والبيانات
    الأساسية: متخصص في بورصة مصر بس ومجاني بالكامل. الرابط مباشر بكود السهم (COMI مثلاً)
    من غير أي خطوة بحث - يعني مفيش خطر إنه يجيب سهم من بورصة تانية غلط زي المشكلة اللي
    واجهناها مع investing.com.
    مؤكدة من صفحة حقيقية فعلياً (النسخة العربية بالظبط): فتح، أعلى، أدنى، إغلاق سابق،
    حجم التداول، قيمة التداول، القيمة السوقية، القيمة الاسمية، القيمة الدفترية، مضاعف
    القيمة الدفترية، ربحية السهم، مضاعف الربحية - كلهم ظاهرين من غير أي قفل أو تسجيل دخول.
    الاستخراج بيعتمد على نص الصفحة الكامل (get_text) والبحث عن كل تسمية عربية متبوعة
    برقم مباشرة (زي "فتح 199.00")، بدل الاعتماد على ترتيب عناصر HTML اللي معندناش تأكيد
    عليه - النمط ده مؤكد فعلياً من صفحة حقيقية.
    """
    if _provider_recently_failed("mubasher_snapshot"):
        return {}
    try:
        import requests as req
        from bs4 import BeautifulSoup

        symbol = ticker_symbol.replace(".CA", "")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://www.mubasher.info/markets/EGX/stocks/{symbol}"
        resp = req.get(url, headers=headers, timeout=6)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        full_text = soup.get_text(separator=" ", strip=True)
        full_text = re.sub(r"\s+", " ", full_text)

        def _label_value(label_text):
            # التسمية العربية متبوعة مباشرة برقم (وممكن يبقى فيه فاصلة آلاف وكسر عشري)
            pattern = re.escape(label_text) + r"\s+(-?[\d,]+\.?\d*)"
            m = re.search(pattern, full_text)
            return m.group(1) if m else None

        data = {"url": url}
        for label, key in [
            ("فتح", "open"), ("إغلاق سابق", "prev_close"),
            ("أعلى", "high"), ("أدنى", "low"),
            ("حجم التداول", "volume"), ("قيمة التداول", "turnover"),
            ("القيمة الاسمية", "par_value"), ("القيمة السوقية", "market_cap"),
            ("القيمة الدفترية", "book_value"), ("مضاعف القيمة الدفترية", "pb_ratio"),
            ("ربحية السهم", "eps"), ("مضاعف الربحية", "pe_ratio"),
        ]:
            val = _label_value(label)
            if val:
                data[key] = val

        # السعر الحالي والتغيّر ونسبته: بيظهروا كتلاتة أرقام متتالية بعد "بتوقيت السوق"
        # مباشرة في الصفحة الحقيقية (مفيش تسمية صريحة "السعر:" قبل الرقم نفسه)
        price_match = re.search(
            r"بتوقيت السوق\s+(-?[\d,]+\.\d+)\s+(-?[\d,]+\.\d+)\s+(-?[\d,]+\.\d+)\s*%",
            full_text
        )
        if price_match:
            try:
                data["price"] = float(price_match.group(1).replace(",", ""))
                data["change"] = float(price_match.group(2).replace(",", ""))
                data["change_pct"] = float(price_match.group(3).replace(",", ""))
            except ValueError:
                pass

        _mark_provider_ok("mubasher_snapshot")
        return data
    except Exception:
        _mark_provider_failed("mubasher_snapshot")
        return {}


# أسماء الشهور العربية زي ما بتظهر فعلياً في تواريخ mubasher.info، لازمة لتحويل التاريخ
# النصي لكائن datetime عشان نقدر نرتب الأخبار زمنياً (الأحدث أولاً)
_ARABIC_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "مايو": 5, "يونيو": 6,
    "يوليو": 7, "أغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12
}


def _parse_mubasher_date(date_text):
    """
    بيحوّل تاريخ عربي بالصيغة اللي فعلياً ظاهرة على mubasher.info (زي "20 أغسطس 09:48 ص")
    لكائن datetime. السنة مش ظاهرة في الصيغة دي (الموقع بيفترض ضمنياً إنها أحدث سنة)،
    فبنفترض السنة الحالية إلا لو الشهر المذكور أكبر من الشهر الحالي (يبقى غالباً من السنة
    اللي فاتت - حالة نادرة بس بتحصل حوالين رأس السنة).
    بيرجع None لو التنسيق مش متطابق بدل ما يوقع بـ exception.
    """
    if not date_text:
        return None
    m = re.search(r"(\d{1,2})\s+(" + "|".join(_ARABIC_MONTHS.keys()) + r")\s+(\d{1,2}):(\d{2})\s*([صم])", date_text)
    if not m:
        return None
    day, month_name, hour, minute, ampm = m.groups()
    month = _ARABIC_MONTHS[month_name]
    hour = int(hour)
    if ampm == "م" and hour != 12:
        hour += 12
    elif ampm == "ص" and hour == 12:
        hour = 0

    from datetime import datetime as _dt
    now = _dt.now()
    year = now.year
    if month > now.month:
        year -= 1
    try:
        return _dt(year, month, int(day), hour, int(minute))
    except ValueError:
        return None


def fetch_mubasher_news(ticker_symbol, company_name=None, max_items=5):
    """
    أخبار الشركة من mubasher.info (النسخة العربية) - مصدر أساسي دلوقتي (بدل Google/Bing
    News) لأنه متخصص في السوق المصري تحديداً وبيدّي أخبار مالية حقيقية بعناوين وروابط
    ودرجة صلة أعلى بكتير من بحث عام.
    شرطين مهمين بيتطبقوا هنا:
    1. ترتيب زمني: بنحلل تاريخ كل خبر (نص عربي) لكائن datetime حقيقي، وبعدين نرتب القايمة
       تنازلياً (الأحدث أولاً) بدل ما نسيبها بترتيب ظهورها الخام في الصفحة.
    2. دقة/صرامة: بنستبعد أي رابط أخبار مالقيناش فيه ذكر صريح لكود السهم (زي "EFIC.CA"
       غالباً بتتحط في عنوان الخبر نفسه) أو لاسم الشركة، عشان نتجنب سحب أخبار عشوائية أو
       مقترحة من قوائم تانية في نفس الصفحة (زي "الأخبار الأكثر قراءة" في الشريط الجانبي).
    """
    if _provider_recently_failed("mubasher_news"):
        return [], None
    try:
        import requests as req
        from bs4 import BeautifulSoup

        symbol = ticker_symbol.replace(".CA", "")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://www.mubasher.info/markets/EGX/stocks/{symbol}/news"
        resp = req.get(url, headers=headers, timeout=6)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # كلمات دالة من اسم الشركة (بنستبعد كلمات عامة قصيرة زي "شركة"/"ش م م" عشان
        # الفلترة تبقى دقيقة على الاسم المميز فعلاً مش أي كلمة عامة بتتكرر في كل الأخبار)
        generic_words = {"شركة", "ش", "م", "القابضة", "المصرية", "مصر", "للاستثمار", "المصري"}
        name_words = []
        if company_name:
            name_words = [w for w in company_name.split() if w not in generic_words and len(w) >= 3]

        raw_items = []
        news_anchor = soup.find(lambda tag: tag.name in {"h1", "h2", "h3"}
                                and "أخبار السهم" in tag.get_text(" ", strip=True))
        news_scope = soup
        if news_anchor:
            news_scope = news_anchor.find_parent("section") or soup

        for link in news_scope.find_all("a", href=re.compile(r"/news/\d+/")):
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 8:
                continue

            # فلتر الدقة: الخبر لازم يذكر كود السهم صراحةً أو كلمة مميزة من اسم الشركة
            title_upper = title.upper()
            has_ticker = bool(re.search(rf"(?<![A-Z0-9]){re.escape(symbol.upper())}(?![A-Z0-9])", title_upper))
            is_relevant = has_ticker or any(w in title for w in name_words)
            if not is_relevant:
                continue

            href = str(link.get("href") or "")
            full_url = href if href.startswith("http") else "https://www.mubasher.info" + href

            date_text = ""
            prev_sib = link.find_previous(string=re.compile(
                r"\d{1,2}\s+(" + "|".join(_ARABIC_MONTHS.keys()) + r")\s+\d{1,2}:\d{2}\s*[صم]"))
            if prev_sib:
                m = re.search(
                    r"\d{1,2}\s+(" + "|".join(_ARABIC_MONTHS.keys()) + r")\s+\d{1,2}:\d{2}\s*[صم]", prev_sib)
                if m:
                    date_text = m.group(0)

            parsed_dt = _parse_mubasher_date(date_text)
            raw_items.append({
                "title": title, "date": date_text, "parsed_date": parsed_dt,
                "source": "مباشر", "link": full_url, "item_type": "خبر"
            })

        if not raw_items:
            _mark_provider_ok("mubasher_news")
            return [], "Mubasher News: رجّع رد من غير أي أخبار متعلقة فعلياً بالسهم ده"

        # الترتيب الزمني: الأحدث أولاً. أي خبر معرفناش نفسّر تاريخه بيتحط في الآخر (مش
        # بيتشال، بس مش بيتفرض إنه الأحدث)، بدل ما نفترض ترتيب غلط.
        from datetime import datetime as _dt
        raw_items.sort(key=lambda it: it["parsed_date"] or _dt.min, reverse=True)

        # إزالة parsed_date قبل الإرجاع (داخلي بس للترتيب، مش جزء من الشكل النهائي للنتيجة)
        items = [{"title": it["title"], "date": it["date"], "source": it["source"],
                  "link": it["link"], "item_type": it["item_type"]}
                 for it in raw_items[:max_items]]

        _mark_provider_ok("mubasher_news")
        return items, None
    except Exception as e:
        _mark_provider_failed("mubasher_news")
        return [], f"Mubasher News: {e}"


def fetch_mubasher_announcements(ticker_symbol, company_name=None, max_items=5):
    """
    إعلانات السوق (Market Disclosures) من mubasher.info - قسم منفصل عن "أخبار السهم"
    وبيحتوي على إفصاحات رسمية للشركة (قرارات مجلس إدارة، جمعيات عمومية، نتائج أعمال، إلخ).
    ملحوظة مهمة: القسم في النسخة العربية اسمه حرفياً "إعلانات السوق" - بنستخدم النص ده
    بالظبط كنقطة ارتكاز (anchor) في صفحة الإعلانات المخصصة للسهم عشان نتأكد إننا بنستخرج
    من القسم الصح، مش أي قسم تنقل عام تاني في الصفحة.
    نفس منطق التاريخ/الترتيب/الفلترة المستخدم في fetch_mubasher_news بالظبط.
    """
    if _provider_recently_failed("mubasher_announcements"):
        return [], None
    try:
        import requests as req
        from bs4 import BeautifulSoup

        symbol = ticker_symbol.replace(".CA", "")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://www.mubasher.info/markets/EGX/stocks/{symbol}/announcements"
        resp = req.get(url, headers=headers, timeout=6)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # صفحة Mubasher نفسها فيها قسماً بعنوان "إعلانات السوق". نحدد أقرب section
        # لهذا العنوان حتى لا تختلط إعلانات الشركة بقسم "الأخبار الأكثر" الجانبي.
        anchor = soup.find(lambda tag: tag.name in {"h1", "h2", "h3"}
                           and "إعلانات السوق" in tag.get_text(" ", strip=True))
        search_scope = soup
        if anchor:
            container = anchor.find_parent()
            while container and container.name != "section":
                container = container.find_parent()
            if container:
                search_scope = container
        else:
            # بعض نسخ صفحة السهم تعرض تبويباً واحداً بلا عنوان قسم؛ نختار أول مجموعة
            # روابط أخبار بعد استبعاد قائمة "الأخبار الأكثر".
            popular_heading = soup.find(lambda tag: tag.name in {"h2", "h3"}
                                        and "الأخبار الأكثر" in tag.get_text(" ", strip=True))
            if popular_heading:
                popular_section = popular_heading.find_parent("section")
                if popular_section:
                    popular_section.decompose()
            search_scope = soup

        generic_words = {"شركة", "ش", "م", "القابضة", "المصرية", "مصر", "للاستثمار", "المصري"}
        name_words = []
        if company_name:
            name_words = [w for w in company_name.split() if w not in generic_words and len(w) >= 3]

        raw_items = []
        for link in search_scope.find_all("a", href=re.compile(r"/news/\d+/")):
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 8:
                continue
            title_upper = title.upper()
            has_ticker = bool(re.search(rf"(?<![A-Z0-9]){re.escape(symbol.upper())}(?![A-Z0-9])", title_upper))
            is_relevant = has_ticker or any(w in title for w in name_words)
            if not is_relevant:
                continue
            href = str(link.get("href") or "")
            full_url = href if href.startswith("http") else "https://www.mubasher.info" + href
            date_text = ""
            card_text = ""
            card = link.find_parent("div")
            for _ in range(4):
                if card is None:
                    break
                card_text = card.get_text(" ", strip=True)
                if re.search(r"\d{1,2}\s+(" + "|".join(_ARABIC_MONTHS.keys()) + r")\s+\d{1,2}:\d{2}\s*[صم]", card_text):
                    break
                card = card.find_parent("div")
            date_match = re.search(
                r"\d{1,2}\s+(" + "|".join(_ARABIC_MONTHS.keys()) + r")\s+\d{1,2}:\d{2}\s*[صم]",
                card_text,
            )
            if date_match:
                date_text = date_match.group(0)
            parsed_dt = _parse_mubasher_date(date_text)
            raw_items.append({
                "title": title, "date": date_text, "parsed_date": parsed_dt,
                "source": "مباشر - إعلانات السوق", "link": full_url, "item_type": "إعلان"
            })

        if not raw_items:
            _mark_provider_ok("mubasher_announcements")
            return [], "Mubasher Announcements: رجّع رد من غير أي إعلانات متعلقة فعلياً بالسهم ده"

        from datetime import datetime as _dt
        raw_items.sort(key=lambda it: it["parsed_date"] or _dt.min, reverse=True)
        items = [{"title": it["title"], "date": it["date"], "source": it["source"],
                  "link": it["link"], "item_type": it["item_type"]}
                 for it in raw_items[:max_items]]

        _mark_provider_ok("mubasher_announcements")
        return items, None
    except Exception as e:
        _mark_provider_failed("mubasher_announcements")
        return [], f"Mubasher Announcements: {e}"


