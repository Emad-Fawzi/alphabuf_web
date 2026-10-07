"""
سلسلة مزوّدين AI مجانية (Gemini -> OpenRouter -> Groq) كل واحد باكاب للتاني، مع تحليل
نسب مئوية للمشاعر (إيجابي/سلبي/محايد) للأخبار، وتحليل أثر تصريحات الفيدرالي الأمريكي.
المفاتيح بتتقرا من environment variables (نفس الأسامي المستخدمة في نسخة Streamlit).
"""
import os
import re
from utils.secrets import get_secret as _get_secret
from utils.provider_health import provider_recently_failed as _provider_recently_failed
from utils.provider_health import mark_provider_failed as _mark_provider_failed
from utils.provider_health import mark_provider_ok as _mark_provider_ok

def analyze_fed_impact(fed_headlines):
    """
    تحليل بالـ AI (نفس سلسلة Gemini->OpenRouter->Groq المستخدمة في باقي الأداة) لأثر آخر
    تصريحات/قرارات الفيدرالي الأمريكي على: البورصة المصرية، الدولار، الذهب، الفضة.
    """
    if not fed_headlines:
        return None, []
    headlines_text = "\n".join(f"- {h['title']}" for h in fed_headlines[:5])
    prompt = (
        "دول آخر عناوين أخبار عن الاحتياطي الفيدرالي الأمريكي:\n"
        f"{headlines_text}\n\n"
        "اكتب تحليل مختصر (٤ نقاط بالظبط) بالعربي عن الأثر المحتمل لده على: "
        "١) البورصة المصرية، ٢) سعر الدولار، ٣) الذهب، ٤) الفضة. "
        "كل نقطة سطر واحد بس، ابدأ كل نقطة بالرقم."
    )
    reply, errors = call_ai_with_fallback(prompt)
    return reply, errors



def call_ai_with_fallback(prompt):
    """
    بينادي أول مزوّد AI شغال من التلاتة بالترتيب: Gemini -> OpenRouter -> Groq.
    لو الأول فشل (مفتاح مش موجود، انتهت الحصة المجانية، أو أي خطأ شبكة) بيجرب اللي بعده تلقائي.
    بيرجع (النص, لستة أخطاء) — لو الثلاثة فشلوا بيرجع (None, أخطاء التلاتة) عشان تقدر تشخّص
    المشكلة بدل ما تفشل بصمت من غير أي تفاصيل.
    """
    import requests as req

    errors = []
    gemini_key = _get_secret("GEMINI_API_KEY")
    openrouter_key = _get_secret("OPENROUTER_API_KEY")
    groq_key = _get_secret("GROQ_API_KEY")

    if gemini_key and not _provider_recently_failed("ai_gemini"):
        try:
            resp = req.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
                f"?key={gemini_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=8
            )
            resp.raise_for_status()
            _mark_provider_ok("ai_gemini")
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip(), errors
        except Exception as e:
            _mark_provider_failed("ai_gemini")
            body = getattr(getattr(e, "response", None), "text", "")
            errors.append(f"Gemini: {e} {body[:200]}")
    elif gemini_key:
        errors.append("Gemini: تم تخطيه مؤقتاً (فشل قبل كده في آخر 5 دقايق بنفس الجلسة)")
    else:
        errors.append("Gemini: مفتاح GEMINI_API_KEY مش موجود في environment variables")

    if openrouter_key and not _provider_recently_failed("ai_openrouter"):
        try:
            resp = req.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_key}"},
                json={"model": "openrouter/free",
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=8
            )
            resp.raise_for_status()
            _mark_provider_ok("ai_openrouter")
            return resp.json()["choices"][0]["message"]["content"].strip(), errors
        except Exception as e:
            _mark_provider_failed("ai_openrouter")
            body = getattr(getattr(e, "response", None), "text", "")
            errors.append(f"OpenRouter: {e} {body[:200]}")
    elif openrouter_key:
        errors.append("OpenRouter: تم تخطيه مؤقتاً (فشل قبل كده في آخر 5 دقايق بنفس الجلسة)")
    else:
        errors.append("OpenRouter: مفتاح OPENROUTER_API_KEY مش موجود في environment variables")

    if groq_key and not _provider_recently_failed("ai_groq"):
        try:
            resp = req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={"model": "openai/gpt-oss-20b",
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=8
            )
            resp.raise_for_status()
            _mark_provider_ok("ai_groq")
            return resp.json()["choices"][0]["message"]["content"].strip(), errors
        except Exception as e:
            _mark_provider_failed("ai_groq")
            body = getattr(getattr(e, "response", None), "text", "")
            errors.append(f"Groq: {e} {body[:200]}")
    elif groq_key:
        errors.append("Groq: تم تخطيه مؤقتاً (فشل قبل كده في آخر 5 دقايق بنفس الجلسة)")
    else:
        errors.append("Groq: مفتاح GROQ_API_KEY مش موجود في environment variables")

    return None, errors



def _parse_sentiment_percentages(reply_text):
    """
    بيحلل رد الـ AI ويستخرج نسب إيجابي/سلبي/محايد منه (لو موجودة بالصيغة المطلوبة).
    بيرجع None لو الرد مش متطابق مع الصيغة (يبقى نرجع للنص الخام كـ fallback في المكان
    اللي بينادي الدالة دي). بيطبّع النسب عشان مجموعها يساوي 100 بالظبط حتى لو الـ AI
    جاب مجموع مختلف شوية (بيحصل أحياناً مع بعض الموديلات).
    """
    if not reply_text:
        return None
    pos_m = re.search(r"إيجابي\s*:?\s*(\d+)", reply_text)
    neg_m = re.search(r"سلبي\s*:?\s*(\d+)", reply_text)
    neu_m = re.search(r"محايد\s*:?\s*(\d+)", reply_text)
    if not (pos_m and neg_m and neu_m):
        return None
    pos, neg, neu = int(pos_m.group(1)), int(neg_m.group(1)), int(neu_m.group(1))
    total = pos + neg + neu
    if total <= 0:
        return None
    pos_norm = round(pos * 100 / total)
    neg_norm = round(neg * 100 / total)
    neu_norm = 100 - pos_norm - neg_norm
    return {"positive": pos_norm, "negative": neg_norm, "neutral": neu_norm}


def _parse_news_analysis(reply_text):
    """
    يحلل رد الـ AI ويستخرج:
    1) نسب المشاعر (إيجابي / سلبي / محايد)
    2) تصنيف الأثر الأساسي (fundamental_type) إن وجد
    3) ملخص الأثر الأساسي (fundamental_impact) إن وجد
    """
    if not reply_text:
        return None, None, None
    sentiment_pct = _parse_sentiment_percentages(reply_text)

    # استخراج تصنيف الأثر الأساسي
    type_m = re.search(r"تصنيف\s*:?\s*([^\n\r]+)", reply_text)
    fundamental_type = type_m.group(1).strip() if type_m else None
    if fundamental_type:
        fundamental_type = re.sub(r"[\[\]\(\)\*\#]", "", fundamental_type).strip()
        # تنظيف أي زيادات
        if len(fundamental_type) > 40:
            fundamental_type = fundamental_type[:40]

    # استخراج ملخص الأثر الأساسي
    impact_m = re.search(r"الأثر\s*:?\s*([^\n\r]+)", reply_text)
    fundamental_impact = impact_m.group(1).strip() if impact_m else None
    if fundamental_impact:
        fundamental_impact = re.sub(r"[\[\]\(\)\*\#]", "", fundamental_impact).strip()
        if len(fundamental_impact) > 200:
            fundamental_impact = fundamental_impact[:200]

    return sentiment_pct, fundamental_type, fundamental_impact


