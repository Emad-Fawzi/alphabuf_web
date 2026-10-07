from fastapi import APIRouter
import config

router = APIRouter(tags=["meta"])

@router.get("/api/health")
def health():
    return {"status": "ok", "total_tickers": sum(len(v) for v in config.EGX_MARKET_BY_SECTOR.values())}

@router.get("/api/sectors")
def get_sectors():
    return {
        "sectors": {
            sector: [{"ticker": item["ticker"].replace(".CA", ""), "name": item["name"]} for item in items]
            for sector, items in config.EGX_MARKET_BY_SECTOR.items()
        }
    }

@router.get("/api/timeframes")
def get_timeframes():
    return {"timeframes": list(config.TIMEFRAME_CONFIG.keys())}
