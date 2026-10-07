import asyncio
from fastapi import APIRouter
from macro.macro_data import fetch_macro_prices, fetch_all_macro_news, fetch_macro_news
from news.ai_provider import analyze_fed_impact
from utils.executor import shared_executor

router = APIRouter(tags=["macro"])

@router.get("/api/macro/prices")
async def macro_prices():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(shared_executor, fetch_macro_prices)


@router.get("/api/macro/news")
async def macro_news():
    loop = asyncio.get_event_loop()
    items, error = await loop.run_in_executor(shared_executor, fetch_all_macro_news)
    return {"items": items, "error": error}


@router.get("/api/macro/fed-analysis")
async def fed_analysis():
    loop = asyncio.get_event_loop()
    news_items, news_error = await loop.run_in_executor(
        shared_executor, fetch_macro_news, "الاحتياطي الفيدرالي الأمريكي بيان أسعار فائدة", 5
    )
    if not news_items:
        return {"news": [], "analysis": None, "errors": [news_error] if news_error else []}
    analysis, ai_errors = await loop.run_in_executor(shared_executor, analyze_fed_impact, news_items)
    return {"news": news_items, "analysis": analysis, "errors": ai_errors}
