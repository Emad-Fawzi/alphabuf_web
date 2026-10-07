"""
كاش بسيط بمهلة زمنية (TTL) - بديل لـ st.cache_data بتاع Streamlit، مناسب لسيرفر FastAPI
دائم التشغيل (مش سكريبت بيعيد تشغيل نفسه زي Streamlit). الكاش هنا مشترك بين كل المستخدمين
(مناسب لبيانات سوق عامة زي الأسعار، مش بيانات خاصة بمستخدم معين).
"""
import time
import functools
import threading

_cache_store = {}
_cache_lock = threading.Lock()


def ttl_cache(ttl_seconds=300):
    """
    ديكوريتور بيكاش نتيجة الدالة لمدة ttl_seconds. المفتاح مبني على اسم الدالة + قيم
    الـ arguments (لازم تكون hashable). Thread-safe عشان FastAPI ممكن يشغّل أكتر من
    طلب في نفس الوقت (async / thread pool).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__module__, func.__qualname__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            with _cache_lock:
                cached = _cache_store.get(key)
                if cached and (now - cached[1]) < ttl_seconds:
                    return cached[0]
            result = func(*args, **kwargs)
            with _cache_lock:
                _cache_store[key] = (result, now)
            return result
        return wrapper
    return decorator


def clear_cache():
    """بتمسح الكاش كله - مفيدة لو محتاج فحص فوري من غير الاعتماد على نتايج قديمة."""
    with _cache_lock:
        _cache_store.clear()
