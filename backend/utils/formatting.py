"""أدوات تنسيق نصوص وأرقام: فواصل الآلاف، وحماية اتجاه النص العربي المختلط بإنجليزي."""
import re

_LATIN_RUN_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9\.\-\+%/]*')


def fmt_thousands(value):
    """تنسيق الأرقام الكبيرة بفواصل الآلاف عشان تبقى سهلة القراءة (مثال: 1,250,000)."""
    try:
        return f"{value:,.0f}"
    except (TypeError, ValueError):
        return value


def bidi_safe(text):
    """
    يحيط أي جزء إنجليزي/رقمي (كود سهم، اسم مؤشر زي MACD، أرقام عشرية) بعلامات
    اتجاه غير مرئية (LRM) عشان مايحصلش تشويش في ترتيب العرض لما يترص جنب نص عربي RTL.
    ملحوظة: الفرونت إند الجديد بيعتمد على CSS (direction: rtl + unicode-bidi: plaintext)
    بدل كده أساساً، لكن الدالة دي متسيبة متاحة لأي استخدام نصي إضافي محتاج نفس الحماية.
    """
    if not isinstance(text, str):
        return text
    return _LATIN_RUN_RE.sub(lambda m: "\u200e" + m.group(0) + "\u200e", text)
