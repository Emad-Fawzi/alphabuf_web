import asyncio
from fastapi import APIRouter, HTTPException, Query
from data_sources.mubasher_source import fetch_mubasher_snapshot
from news.news_aggregator import analyze_news_for_stock
from utils.executor import shared_executor

router = APIRouter(tags=["stocks"])

@router.get("/api/stock/{ticker}/news")
async def stock_news(ticker: str, company_name: str = Query(...)):
    if not ticker or len(ticker) > 20 or not ticker.replace(".", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="رمز سهم غير صالح")
    company_name = company_name.strip()[:160]
    if not company_name:
        raise HTTPException(status_code=400, detail="اسم الشركة مطلوب")
    loop = asyncio.get_event_loop()
    mubasher_data, (news_items, ai_errors) = await asyncio.gather(
        loop.run_in_executor(shared_executor, fetch_mubasher_snapshot, f"{ticker}.CA"),
        loop.run_in_executor(shared_executor, analyze_news_for_stock, f"{ticker}.CA", company_name),
    )
    return {"mubasher": mubasher_data, "news": news_items, "errors": ai_errors}
