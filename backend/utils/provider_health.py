"""
نظام تتبّع صحة مصادر البيانات الخارجية (investing.com, mubasher.info, Google/Bing News,
Gemini/OpenRouter/Groq). أي مصدر يفشل مرة بيتسجّل، ولمدة PROVIDER_COOLDOWN_SECONDS بعدها
أي محاولة تانية بتتخطاه فوراً من غير ما تنتظر مهلة شبكة كاملة تانية.

ملحوظة معمارية: في نسخة Streamlit كانت الحالة دي متخزنة في st.session_state (لكل مستخدم
لوحده). هنا (سيرفر FastAPI دائم التشغيل) الحالة global بين كل المستخدمين - وده منطقي فعلاً
أكتر: لو mubasher.info واقع، هو واقع لكل المستخدمين مش لمستخدم بعينه.
"""
import time
import threading

_provider_health = {}
_health_lock = threading.Lock()

PROVIDER_COOLDOWN_SECONDS = 300  # 5 دقايق


def provider_recently_failed(provider_key):
    with _health_lock:
        failed_at = _provider_health.get(provider_key)
    return bool(failed_at and (time.time() - failed_at) < PROVIDER_COOLDOWN_SECONDS)


def mark_provider_failed(provider_key):
    with _health_lock:
        _provider_health[provider_key] = time.time()


def mark_provider_ok(provider_key):
    with _health_lock:
        _provider_health.pop(provider_key, None)
