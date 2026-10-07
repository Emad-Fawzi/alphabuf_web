"""
أداة استخراج وتحليل ملفات الـ PDF المرفقة مع إعلانات السوق والأخبار (mubasher.info / EGX).
تستخرج النصوص وتلخصها لتوفير التوكينز مع حفظ الروابط والنتائج في الكاش.
"""
import re
import hashlib
from io import BytesIO
from typing import Optional, Tuple

try:
    import pypdf
    PdfReader = pypdf.PdfReader
    HAS_PDF_PARSER = True
except ImportError:
    try:
        import PyPDF2
        PdfReader = PyPDF2.PdfReader
        HAS_PDF_PARSER = True
    except ImportError:
        PdfReader = None
        HAS_PDF_PARSER = False


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def download_pdf(url: str, timeout: int = 10) -> Optional[bytes]:
    """تحميل ملف PDF وإرجاع البيانات الخام، أو None في حالة الفشل."""
    if not url:
        return None
    try:
        import requests as req
        resp = req.get(url, timeout=timeout, headers=HEADERS)
        resp.raise_for_status()
        content = resp.content
        if content and content.startswith(b"%PDF"):
            return content
        return None
    except Exception:
        return None


def extract_text_from_pdf(pdf_bytes: bytes, max_pages: int = 5, max_chars: int = 3500) -> str:
    """
    استخراج النص الصافي من ملف الـ PDF حتى max_pages أو max_chars.
    تنظيف المسافات والأسطر الفارغة لتوفير التوكينز في استدعاءات الـ AI.
    """
    if not HAS_PDF_PARSER or not pdf_bytes or PdfReader is None:
        return ""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        num_pages = min(len(reader.pages), max_pages)
        extracted = []
        total_len = 0
        for i in range(num_pages):
            page = reader.pages[i]
            try:
                page_text = page.extract_text() or ""
                # تنظيف الأسطر المكررة والمسافات الزائدة
                page_text = re.sub(r"[ \t]+", " ", page_text)
                page_text = re.sub(r"\n\s*\n+", "\n", page_text).strip()
                if page_text:
                    extracted.append(page_text)
                    total_len += len(page_text)
                    if total_len >= max_chars:
                        break
            except Exception:
                continue

        full_text = "\n".join(extracted).strip()
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "..."
        return full_text
    except Exception:
        return ""


def find_pdf_url_in_page(page_url: str, timeout: int = 7) -> Optional[str]:
    """
    البحث عن رابط ملف الـ PDF المرفق داخل صفحة إعلان مباشر أو الخبر.
    الموقع يعتمد روابط من static.mubasher.info أو egx.com.eg لملف الإفصاح الرسمي.
    """
    if not page_url:
        return None
    if page_url.lower().endswith(".pdf"):
        return page_url

    try:
        import requests as req
        from bs4 import BeautifulSoup

        resp = req.get(page_url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = str(a.get("href") or "").strip()
            if re.search(r"\.pdf(\?|$)", href, re.I):
                full_href = href if href.startswith("http") else "https://www.mubasher.info" + href
                pdf_links.append(full_href)

        if not pdf_links:
            return None

        # نفضل روابط static.mubasher.info لأن خوادم البورصة المباشرة قد ترفض الطلبات أحياناً
        for link in pdf_links:
            if "mubasher.info" in link:
                return link
        return pdf_links[0]
    except Exception:
        return None


def get_pdf_text_and_url(
    url: str,
    cache: dict,
    ticker_symbol: str,
    max_pages: int = 5,
    max_chars: int = 3500
) -> Tuple[Optional[str], Optional[str]]:
    """
    جلب النص المستخرج ورابط الـ PDF المباشر مع استغلال الكاش لتجنب تكرار التحميل والتوكينز.
    الكاش يحفظ كـ `{ticker}:pdf_meta:{hash}` ويحتوي على النص ورابط الـ PDF.
    """
    if not url:
        return None, None

    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cache_key = f"{ticker_symbol}:pdf_meta:{url_hash}"

    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached.get("text"), cached.get("pdf_url")

    # تحديد رابط الـ PDF المباشر
    direct_pdf_url = find_pdf_url_in_page(url)
    if not direct_pdf_url:
        # حفظ نتيجة سلبية لتجنب إعادة الفحص في نفس الجلسة
        cache[cache_key] = {"text": None, "pdf_url": None}
        return None, None

    pdf_bytes = download_pdf(direct_pdf_url)
    text = extract_text_from_pdf(pdf_bytes, max_pages=max_pages, max_chars=max_chars) if pdf_bytes else None

    # حفظ في الكاش
    cache[cache_key] = {
        "text": text if text else None,
        "pdf_url": direct_pdf_url
    }
    return (text if text else None), direct_pdf_url


def get_pdf_text(url: str, cache: dict, ticker_symbol: str, max_pages: int = 5) -> Optional[str]:
    """دالة للتوافق مع الإصدارات السابقة ترجع النص فقط."""
    text, _ = get_pdf_text_and_url(url, cache, ticker_symbol, max_pages=max_pages)
    return text
