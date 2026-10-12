"""
كاش على القرص لتحليل مشاعر الأخبار: كل خبر بيتحلل مرة واحدة بس (بالـ AI)، ولو نفس الخبر
ظهر تاني في أي rerun أو فحص جديد، بيتقرا من هنا بدل ما يتبعت للـ AI تاني (توفير توكينز).
"""
import json
from pathlib import Path

# لا تعتمد على مجلد التشغيل؛ Render والتشغيل المحلي قد يبدآن التطبيق من مسارين مختلفين.
NEWS_CACHE_FILE = Path(__file__).resolve().parent.parent / "news_sentiment_cache.json"

def load_news_cache():
    try:
        with NEWS_CACHE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_news_cache(cache, max_items=2000):
    try:
        if len(cache) > max_items:
            # Keep the most recently added/updated items at the end
            cache = dict(list(cache.items())[-max_items:])
            
        # الكتابة الذرّية تمنع ملف JSON ناقصاً إذا توقف السيرفر أثناء الحفظ.
        temporary_file = NEWS_CACHE_FILE.with_suffix(".tmp")
        temporary_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        temporary_file.replace(NEWS_CACHE_FILE)
    except Exception:
        pass

