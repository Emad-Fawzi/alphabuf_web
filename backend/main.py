"""
AlphaBuf API - سيرفر FastAPI بيعرض كل منطق التحليل والفحص (اللي كان جوه Streamlit) كـ
REST API. الفرونت إند (frontend/) بيستهلك الـ API ده بـ fetch() عادي، فالتفاعل (فلاتر،
ترتيب، فتح تفاصيل سهم) بيحصل في المتصفح نفسه من غير أي طلب جديد للسيرفر - أسرع بكتير من
نموذج Streamlit اللي بيعيد تشغيل السكريبت كله مع كل تفاعل.
"""
try:
    from dotenv import load_dotenv
    load_dotenv()  # بيحمّل .env لو موجود (تطوير محلي) - بيتجاهل بهدوء لو مش موجود أو
                    # python-dotenv مش متثبتة (منصات الاستضافة بتحقن المتغيرات مباشرة عادةً)
except ImportError:
    pass

import asyncio
import concurrent.futures
from contextlib import asynccontextmanager
import hashlib
import json
import logging
import math
import numbers
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
from analysis.stock_analyzer import analyze_stock
from data_sources.stockanalysis_source import fetch_price_verification_snapshot
from ui.excel_export import apply_excel_formatting
from utils.executor import shared_executor
import routers.meta
import routers.macro
import routers.stocks

import pandas as pd
import io

app = FastAPI(title="AlphaBuf API", description="محرك فحص البورصة المصرية")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.meta.router)
app.include_router(routers.macro.router)
app.include_router(routers.stocks.router)

_executor = shared_executor
_scan_cache = {}
_scan_inflight = {}
_scan_cache_lock = threading.Lock()
_scan_progress = {}
_SCAN_TTL_SECONDS = {
    "يومي": 24 * 60 * 60,
    "أسبوعي": 7 * 24 * 60 * 60,
    "4 ساعات": 4 * 60 * 60,
    "ساعتين": 2 * 60 * 60,
    "ساعة": 60 * 60,
    "ربع ساعة": 15 * 60,
}
logger = logging.getLogger(__name__)
_SCAN_HISTORY_FILE = Path(__file__).with_name("scan_history.json")
_SCAN_CACHE_FILE = Path(__file__).with_name("scan_cache.json")
_SCAN_CACHE_SCHEMA = 6
_SECTOR_TAXONOMY_VERSION = 5
_scan_history_lock = threading.Lock()


def _load_scan_history():
    try:
        with _SCAN_HISTORY_FILE.open("r", encoding="utf-8") as history_file:
            history = json.load(history_file)
        return history if isinstance(history, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


_scan_history = _load_scan_history()


def _cache_key_from_json(raw_key):
    if not isinstance(raw_key, list) or len(raw_key) != 4:
        return None
    sectors, timeframe, turnover, investing = raw_key
    if not isinstance(sectors, list):
        return None
    return (tuple(sectors), timeframe, float(turnover), bool(investing))


def _load_scan_cache():
    try:
        with _SCAN_CACHE_FILE.open("r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        return {}

    cache = {}
    if not isinstance(data, dict) or data.get("schema_version") != _SCAN_CACHE_SCHEMA:
        return cache
    now = time.time()
    for item in data.get("entries", {}).values():
        if not isinstance(item, dict):
            continue
        key = _cache_key_from_json(item.get("key"))
        result = item.get("result")
        cached_at = item.get("cached_at")
        ttl_seconds = item.get("ttl_seconds")
        if key is None or not isinstance(result, dict):
            continue
        if not isinstance(cached_at, (int, float)) or not isinstance(ttl_seconds, (int, float)):
            continue
        if now < cached_at + ttl_seconds:
            cache[key] = (result, cached_at, ttl_seconds)
    return cache


_scan_cache.update(_load_scan_cache())


class ScanRequest(BaseModel):
    sectors: list[str] = []
    timeframe: str = "يومي"
    min_daily_turnover: float = 0
    use_investing_primary: bool = False
    force_refresh: bool = False


def _default_scan_request():
    return ScanRequest()


def _scan_cache_entry_is_fresh(entry, now=None):
    checked_at = time.time() if now is None else now
    cached_at, ttl_seconds = entry[1], entry[2]
    return checked_at < cached_at + ttl_seconds


def _get_fresh_all_market_daily_scan():
    key = ((), "يومي", 0.0, False)
    with _scan_cache_lock:
        entry = _scan_cache.get(key)
        if entry and _scan_cache_entry_is_fresh(entry):
            return entry

        if entry:
            if key not in _scan_inflight:
                req = _default_scan_request()
                args = (req.sectors, req.timeframe, req.min_daily_turnover, req.use_investing_primary)
                _scan_inflight[key] = _executor.submit(_execute_and_cache_scan, key, args, _SCAN_TTL_SECONDS["يومي"])
            return entry

        future = _scan_inflight.get(key)
        if future is None:
            req = _default_scan_request()
            args = (req.sectors, req.timeframe, req.min_daily_turnover, req.use_investing_primary)
            future = _executor.submit(_execute_and_cache_scan, key, args, _SCAN_TTL_SECONDS["يومي"])
            _scan_inflight[key] = future
        return future





@app.get("/api/scan/latest")
def latest_scan():
    scan_state = _get_fresh_all_market_daily_scan()
    if isinstance(scan_state, concurrent.futures.Future):
        key = ((), "يومي", 0.0, False)
        return {"status": "running", "timeframe": "يومي", "progress": _scan_progress.get(_history_id(key))}

    result, cached_at, ttl_seconds = scan_state
    history_key = ((), "يومي", 0.0, False)
    if not _get_scan_history(history_key):
        _record_scan_history(history_key, "يومي", result)
    expires_at = cached_at + ttl_seconds
    if not _scan_cache_entry_is_fresh(scan_state):
        response = _with_scan_metadata(result, "refreshing", cached_at, expires_at, history_key)
        response["status"] = "refreshing"
        response["progress"] = _scan_progress.get(_history_id(history_key))
        return response

    response = _with_scan_metadata(result, "cached", cached_at, expires_at, history_key)
    response["status"] = "ready"
    return response


@app.post("/api/scan/status")
def scan_status(req: ScanRequest):
    key = _scan_key(req)
    with _scan_cache_lock:
        entry = _scan_cache.get(key)
        is_running = key in _scan_inflight
    if entry:
        cached_at, ttl_seconds = entry[1], entry[2]
        expires_at = cached_at + ttl_seconds
        status = "refreshing" if is_running or not _scan_cache_entry_is_fresh(entry) else "ready"
        return {
            "status": status,
            "cache": {"cached_at": datetime.fromtimestamp(cached_at, timezone.utc).isoformat(),
                      "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat()},
            "progress": _scan_progress.get(_history_id(key)),
        }

    if is_running:
        return {"status": "running", "progress": _scan_progress.get(_history_id(key))}
    return {"status": "missing", "progress": None}


@asynccontextmanager
async def _lifespan(app):
    """ابدأ الفحص اليومي الافتراضي، ثم حدّث أي نتائج منتهية الصلاحية بالخلفية."""
    _get_fresh_all_market_daily_scan()
    refresh_task = asyncio.create_task(_refresh_expired_scan_cache())
    app.state.scan_cache_refresh_task = refresh_task
    try:
        yield
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


async def _refresh_expired_scan_cache():
    while True:
        now = time.time()
        with _scan_cache_lock:
            expired_entries = [
                (key, entry)
                for key, entry in _scan_cache.items()
                if now >= entry[1] + entry[2] and key not in _scan_inflight
            ]
            for key, entry in expired_entries:
                if _scan_cache_entry_is_fresh(entry, now):
                    continue
                sectors, timeframe, turnover, investing = key
                args = (list(sectors), timeframe, turnover, investing)
                ttl_seconds = _SCAN_TTL_SECONDS.get(timeframe, 60 * 60)
                _scan_inflight[key] = _executor.submit(_execute_and_cache_scan, key, args, ttl_seconds)
        await asyncio.sleep(30)


app.router.lifespan_context = _lifespan


def _run_scan(sectors, timeframe, min_daily_turnover, use_investing_primary, progress_key=None):
    timeframe_cfg = config.TIMEFRAME_CONFIG.get(timeframe, config.TIMEFRAME_CONFIG["يومي"])
    selected_sectors = sectors if sectors else list(config.EGX_MARKET_BY_SECTOR.keys())

    tasks = [(sector, item) for sector, companies in config.EGX_MARKET_BY_SECTOR.items()
             if sector in selected_sectors for item in companies]
    total_stocks = len(tasks)
    if progress_key:
        _scan_progress[progress_key] = {"completed": 0, "total": total_stocks, "percent": 0}

    if total_stocks == 0:
        return {"results": [], "dropped": [], "total_stocks": 0, "elapsed_seconds": 0}

    start_time = time.time()
    price_snapshot = fetch_price_verification_snapshot()

    results, dropped = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(analyze_stock, sector, item, timeframe_cfg, min_daily_turnover, 0.0,
                        price_snapshot, use_investing_primary): item
            for sector, item in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                result, drop = future.result()
            except Exception as e:
                result, drop = None, {"القطاع": "-", "اسم الشركة": item["name"],
                                       "الرمز": item["ticker"], "سبب الاستبعاد": f"خطأ غير متوقع ({e})"}
            if result:
                results.append(result)
            if drop:
                dropped.append(drop)
            if progress_key:
                progress = _scan_progress.get(progress_key, {"completed": 0, "total": total_stocks})
                progress["completed"] += 1
                progress["percent"] = round(progress["completed"] * 100 / total_stocks)
                _scan_progress[progress_key] = progress

    elapsed = time.time() - start_time
    return {"results": results, "dropped": dropped, "total_stocks": total_stocks, "elapsed_seconds": round(elapsed, 1)}


def _scan_key(req):
    return (tuple(sorted(req.sectors)), req.timeframe, req.min_daily_turnover, req.use_investing_primary)


def _history_id(key):
    encoded_key = json.dumps(
        {"taxonomy_version": _SECTOR_TAXONOMY_VERSION, "scan_key": key},
        ensure_ascii=False,
        separators=(",", ":"),
        default=list,
    )
    return hashlib.sha256(encoded_key.encode("utf-8")).hexdigest()


def _valid_number(value):
    if not isinstance(value, numbers.Real) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _make_history_snapshot(timeframe, result):
    result_rows = result.get("results", [])
    changes = [change for row in result_rows if (change := _valid_number(row.get("التغير %"))) is not None]
    overall_average = sum(changes) / len(changes) if changes else None
    by_sector = {}
    for row in result_rows:
        sector = row.get("القطاع") or "غير مصنف"
        change = _valid_number(row.get("التغير %"))
        summary = by_sector.setdefault(sector, {"changes": [], "leader": None, "historical_returns": {}})
        if change is not None:
            summary["changes"].append(change)
            if summary["leader"] is None or change > summary["leader"]["change_pct"]:
                summary["leader"] = {
                    "company": row.get("اسم الشركة"),
                    "ticker": row.get("الرمز"),
                    "change_pct": change,
                }
        for label, field in (
            ("quarter_pct", "أداء تاريخي ربع سنوي %"),
            ("half_year_pct", "أداء تاريخي نصف سنوي %"),
            ("year_pct", "أداء تاريخي سنوي %"),
        ):
            historical_return = _valid_number(row.get(field))
            if historical_return is not None:
                summary["historical_returns"].setdefault(label, []).append(historical_return)

    sectors = {}
    for sector, summary in by_sector.items():
        sector_changes = summary["changes"]
        sectors[sector] = {
            "matched_count": len(sector_changes),
            "average_change": sum(sector_changes) / len(sector_changes) if sector_changes else None,
            "leader": summary["leader"],
            "historical_returns": {
                label: {"average_pct": sum(values) / len(values), "count": len(values)}
                for label, values in summary["historical_returns"].items()
            },
        }

    sector_performance = {}
    for sector, summary in by_sector.items():
        sector_changes = summary["changes"]
        sector_performance[sector] = sum(sector_changes) / len(sector_changes) if sector_changes else None

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "timeframe": timeframe,
        "matched_count": len(result_rows),
        "total_stocks": result.get("total_stocks", 0),
        "average_change": overall_average,
        "sectors": sectors,
        "sector_performance": sector_performance,
    }


def _sector_horizon_performance(key, current_result):
    history = _get_scan_history(key)
    comparable = [
        snapshot for snapshot in history
        if snapshot.get("timeframe") == "يومي" and snapshot.get("sector_performance")
    ]
    as_of = datetime.now(timezone.utc)
    horizons = {"ربع سنوي": 90, "نصف سنوي": 182, "سنوي": 365}
    current_sectors = {}
    current_sector_horizons = {}
    for row in current_result.get("results", []):
        change = _valid_number(row.get("التغير %"))
        if change is not None:
            current_sectors.setdefault(row.get("القطاع") or "غير مصنف", []).append(change)
        sector = row.get("القطاع") or "غير مصنف"
        horizon_values = current_sector_horizons.setdefault(sector, {"ربع سنوي": [], "نصف سنوي": [], "سنوي": []})
        for label, field in (
            ("ربع سنوي", "أداء تاريخي ربع سنوي %"),
            ("نصف سنوي", "أداء تاريخي نصف سنوي %"),
            ("سنوي", "أداء تاريخي سنوي %"),
        ):
            historical_return = _valid_number(row.get(field))
            if historical_return is not None:
                horizon_values[label].append(historical_return)

    summaries = {}
    for sector, changes in current_sectors.items():
        now_average = sum(changes) / len(changes)
        sector_summary = {"current_average": now_average, "periods": {}}
        for label, days in horizons.items():
            current_returns = current_sector_horizons.get(sector, {}).get(label, [])
            current_horizon_average = sum(current_returns) / len(current_returns) if current_returns else None
            target_date = as_of - timedelta(days=days)
            candidate = None
            for snapshot in comparable:
                try:
                    snapshot_date = datetime.fromisoformat(snapshot["captured_at"])
                except (KeyError, ValueError):
                    continue
                if snapshot_date <= target_date:
                    candidate = snapshot
            prior_average = candidate.get("sector_performance", {}).get(sector) if candidate else None
            historical_key = {"ربع سنوي": "quarter_pct", "نصف سنوي": "half_year_pct", "سنوي": "year_pct"}[label]
            prior_historical = candidate.get("sectors", {}).get(sector, {}).get("historical_returns", {}).get(historical_key) if candidate else None
            observed_average = prior_historical.get("average_pct") if prior_historical else None
            observed_count = prior_historical.get("count", 0) if prior_historical else 0
            sector_summary["periods"][label] = {
                "current_return": current_horizon_average,
                "captured_at": candidate.get("captured_at") if candidate else None,
                "average_change": observed_average if observed_average is not None else prior_average,
                "observed_stock_count": observed_count,
                "change_points": round(current_horizon_average - observed_average, 2)
                    if current_horizon_average is not None and observed_average is not None else None,
            }
        summaries[sector] = sector_summary
    return summaries


def _record_scan_history(key, timeframe, result):
    history_id = _history_id(key)
    snapshot = _make_history_snapshot(timeframe, result)
    with _scan_history_lock:
        entries = _scan_history.setdefault(history_id, [])
        same_period = False
        if entries and timeframe == "يومي":
            same_period = entries[-1].get("captured_at", "")[:10] == snapshot["captured_at"][:10]
        elif entries and timeframe == "أسبوعي":
            try:
                old_date = datetime.fromisoformat(entries[-1]["captured_at"])
                new_date = datetime.fromisoformat(snapshot["captured_at"])
                same_period = old_date.isocalendar()[:2] == new_date.isocalendar()[:2]
            except (KeyError, ValueError):
                same_period = False
        if same_period:
            entries[-1] = snapshot
        else:
            entries.append(snapshot)
        _scan_history[history_id] = entries[-400:]

        if len(_scan_history) > 50:
            oldest_keys = sorted(
                _scan_history,
                key=lambda item: _scan_history[item][-1]["captured_at"] if _scan_history[item] else "",
            )
            for old_key in oldest_keys[:len(_scan_history) - 50]:
                _scan_history.pop(old_key, None)

        try:
            temporary_file = _SCAN_HISTORY_FILE.with_suffix(".tmp")
            temporary_file.write_text(json.dumps(_scan_history, ensure_ascii=False), encoding="utf-8")
            temporary_file.replace(_SCAN_HISTORY_FILE)
        except OSError:
            logger.exception("Could not persist scan history")


def _get_scan_history(key):
    with _scan_history_lock:
        return list(_scan_history.get(_history_id(key), []))


def _make_json_safe(value):
    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        numeric_value = float(value)
        return numeric_value if math.isfinite(numeric_value) else None
    return value


def _persist_scan_cache():
    with _scan_cache_lock:
        entries = sorted(_scan_cache.items(), key=lambda item: item[1][1], reverse=True)[:12]
        serialized = {}
        for key, (result, cached_at, ttl_seconds) in entries:
            serialized[_history_id(key)] = {
                "key": [list(key[0]), key[1], key[2], key[3]],
                "result": _make_json_safe(result),
                "cached_at": cached_at,
                "ttl_seconds": ttl_seconds,
            }

        try:
            temporary_file = _SCAN_CACHE_FILE.with_suffix(".tmp")
            temporary_file.write_text(
                json.dumps({"schema_version": _SCAN_CACHE_SCHEMA, "entries": serialized}, ensure_ascii=False, allow_nan=False),
                encoding="utf-8",
            )
            temporary_file.replace(_SCAN_CACHE_FILE)
        except OSError:
            logger.exception("Could not persist scan result cache")


def _execute_and_cache_scan(key, args, ttl_seconds):
    try:
        result = _run_scan(*args, progress_key=_history_id(key))
        _record_scan_history(key, args[1], result)
        now = time.time()
        with _scan_cache_lock:
            _scan_cache[key] = (result, now, ttl_seconds)
        _persist_scan_cache()
        return result
    except Exception:
        logger.exception("Market scan failed for cache key %s", key)
        raise
    finally:
        with _scan_cache_lock:
            _scan_inflight.pop(key, None)
            _scan_progress.pop(_history_id(key), None)


def _with_scan_metadata(result, cache_status, cached_at, expires_at, history_key):
    response = _make_json_safe(result)
    response["cache"] = {
        "status": cache_status,
        "cached_at": datetime.fromtimestamp(cached_at, timezone.utc).isoformat() if cached_at else None,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat() if expires_at else None,
    }
    response["history"] = _make_json_safe(_get_scan_history(history_key)[-10:])
    response["sector_horizons"] = _make_json_safe(_sector_horizon_performance(history_key, result))
    sectors, timeframe, min_daily_turnover, use_investing_primary = history_key
    response["scan_config"] = {
        "sectors": list(sectors),
        "timeframe": timeframe,
        "min_daily_turnover": min_daily_turnover,
        "use_investing_primary": use_investing_primary,
    }
    return response


@app.post("/api/scan")
async def scan(req: ScanRequest):
    key = _scan_key(req)
    args = (req.sectors, req.timeframe, req.min_daily_turnover, req.use_investing_primary)
    ttl_seconds = _SCAN_TTL_SECONDS.get(req.timeframe, 60 * 60)
    now = time.time()

    with _scan_cache_lock:
        cached = _scan_cache.get(key)
        if req.force_refresh:
            future = _scan_inflight.get(key)
            if future is None:
                future = _executor.submit(_execute_and_cache_scan, key, args, ttl_seconds)
                _scan_inflight[key] = future
        elif cached:
            result, cached_at, cached_ttl = cached
            expires_at = cached_at + cached_ttl
            if not _get_scan_history(key):
                _record_scan_history(key, req.timeframe, result)
            if now < expires_at:
                return _with_scan_metadata(result, "cached", cached_at, expires_at, key)

            if key not in _scan_inflight:
                _scan_inflight[key] = _executor.submit(_execute_and_cache_scan, key, args, ttl_seconds)
            return _with_scan_metadata(result, "refreshing", cached_at, expires_at, key)

        future = _scan_inflight.get(key)
        if future is None:
            future = _executor.submit(_execute_and_cache_scan, key, args, ttl_seconds)
            _scan_inflight[key] = future

    try:
        result = await asyncio.wrap_future(future)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"فشل فحص السوق: {exc}") from exc

    cached_at = time.time()
    return _with_scan_metadata(result, "fresh", cached_at, cached_at + ttl_seconds, key)


@app.post("/api/scan/excel")
async def scan_excel(req: ScanRequest):
    scan_result = await scan(req)
    if not scan_result["results"]:
        raise HTTPException(status_code=404, detail="مفيش نتائج للتصدير")
    df = pd.DataFrame(scan_result["results"])
    excel_bytes = apply_excel_formatting(df)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=AlphaBuf_Scan.xlsx"}
    )




_frontend_dir = str(Path(__file__).resolve().parent.parent / "frontend")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

