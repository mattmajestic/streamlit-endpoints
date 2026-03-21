"""
Custom Starlette endpoints mounted alongside the Streamlit app.

Routes are registered via the App class in app/run.py:

    from app.endpoints import routes
    app = App("app/main.py", routes=routes)
"""

import os
import sys
import json
import asyncio
import numpy as np
import fastf1
import pandas as pd
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


def _safe_json(obj):
    """Recursively convert numpy/pandas types to plain Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float) and (obj != obj):  # NaN check
        return None
    return obj


def _df_to_records(df: pd.DataFrame) -> list:
    return [_safe_json(row) for row in df.where(pd.notnull(df), None).to_dict(orient="records")]

_CACHE_DIR = "/tmp/fastf1_cache"
os.makedirs(_CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(_CACHE_DIR)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def info(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "app": "streamlit-starlette",
            "python": sys.version,
            "server": "starlette (experimental)",
        }
    )


async def echo(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    return JSONResponse({"echo": body})


# ── F1 endpoints ──────────────────────────────────────────────────────────────

async def f1_schedule(request: Request) -> JSONResponse:
    """GET /f1/schedule?year=2025"""
    try:
        year = int(request.query_params.get("year", 2025))
        schedule = await asyncio.to_thread(
            fastf1.get_event_schedule, year, include_testing=False
        )
        records = (
            schedule[["RoundNumber", "EventName", "Country", "EventDate"]]
            .assign(EventDate=lambda df: df["EventDate"].astype(str))
            .to_dict(orient="records")
        )
        return JSONResponse({"year": year, "schedule": records})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def f1_results(request: Request) -> JSONResponse:
    """GET /f1/results?year=2025&round=1&session=R"""
    try:
        year = int(request.query_params.get("year", 2025))
        round_num = int(request.query_params.get("round", 1))
        session_code = request.query_params.get("session", "R")

        def _load():
            session = fastf1.get_session(year, round_num, session_code)
            session.load(telemetry=False, weather=False, messages=False)
            lap_cols = [c for c in ["Driver", "Team", "LapNumber", "LapTime", "Compound", "IsPersonalBest", "Position"] if c in session.laps.columns]
            laps = session.laps[lap_cols].copy()
            laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
            laps = laps.drop(columns=["LapTime"])
            results = session.results.copy()
            return laps, results

        laps, results = await asyncio.to_thread(_load)

        # Serialise — convert timedeltas and numpy types
        result_cols = [c for c in ["Position", "Abbreviation", "FullName", "TeamName", "GridPosition", "Points", "Status", "Q1", "Q2", "Q3"] if c in results.columns]
        res = results[result_cols].copy()
        for col in ["Q1", "Q2", "Q3"]:
            if col in res.columns:
                res[col] = res[col].apply(lambda t: t.total_seconds() if hasattr(t, "total_seconds") and pd.notnull(t) else None)

        payload = json.dumps({
            "laps": _df_to_records(laps),
            "results": _df_to_records(res),
        })
        return Response(payload, media_type="application/json")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/custom/info", info, methods=["GET"]),
    Route("/custom/echo", echo, methods=["POST"]),
    Route("/f1/schedule", f1_schedule, methods=["GET"]),
    Route("/f1/results", f1_results, methods=["GET"]),
]
