"""
Custom Starlette endpoints mounted alongside the Streamlit app.

Routes are registered via the App class in app/run.py:

    from app.endpoints import routes
    app = App("app/main.py", routes=routes)
"""

import sys
import asyncio
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from app.f1_store import df_to_records, get_event_schedule, get_session_bundle


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
        schedule = await asyncio.to_thread(get_event_schedule, year)
        records = df_to_records(schedule[["RoundNumber", "EventName", "Country", "EventDate"]])
        return JSONResponse({"year": year, "schedule": records})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def f1_results(request: Request) -> JSONResponse:
    """GET /f1/results?year=2025&round=1&session=R"""
    try:
        year = int(request.query_params.get("year", 2025))
        round_num = int(request.query_params.get("round", 1))
        session_code = request.query_params.get("session", "R")
        laps, results = await asyncio.to_thread(get_session_bundle, year, round_num, session_code)
        payload = {"laps": df_to_records(laps), "results": df_to_records(results)}
        return JSONResponse(payload)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


_COMPONENTS_DIR = Path(__file__).parent / "components"

routes = [
    Route("/health", health, methods=["GET"]),
    Route("/custom/info", info, methods=["GET"]),
    Route("/custom/echo", echo, methods=["POST"]),
    Route("/f1/schedule", f1_schedule, methods=["GET"]),
    Route("/f1/results", f1_results, methods=["GET"]),
    Mount("/components", app=StaticFiles(directory=_COMPONENTS_DIR, html=True)),
]
