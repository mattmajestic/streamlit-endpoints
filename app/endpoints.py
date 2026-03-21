"""
Custom Starlette endpoints mounted alongside the Streamlit app.

Routes are registered via the App class in app/run.py:

    from app.endpoints import routes
    app = App("app/main.py", routes=routes)
"""

import sys
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


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


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/custom/info", info, methods=["GET"]),
    Route("/custom/echo", echo, methods=["POST"]),
]
