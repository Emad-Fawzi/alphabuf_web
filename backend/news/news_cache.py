"""
كاش على القرص لتحليل مشاعر الأخبار: كل خبر بيتحلل مرة واحدة بس (بالـ AI)، ولو نفس الخبر
ظهر تاني في أي rerun أو فحص جديد، بيتقرا من هنا بدل ما يتبعت للـ AI تاني (توفير توكينز).
"""
import json

NEWS_CACHE_FILE = "news_sentiment_cache.json"

def load_news_cache():
    try:
        with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_news_cache(cache, max_items=2000):
    try:
        if len(cache) > max_items:
            # Keep the most recently added/updated items at the end
            cache = dict(list(cache.items())[-max_items:])
            
        with open(NEWS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


