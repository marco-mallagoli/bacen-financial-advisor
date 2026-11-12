"""Serves both the End-User Executive Web UI (/app) and the ADK Dev UI (/dev-ui) on port 18000."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
import uvicorn

from google.adk.cli.fast_api import get_fast_api_app

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(__file__).resolve().parent


async def serve_end_user_ui(_request):
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


async def serve_ui_config(_request):
    cfg = json.loads((FRONTEND_DIR / "ui_config.json").read_text(encoding="utf-8"))
    return JSONResponse(content=cfg)


def build_app():
    app = get_fast_api_app(
        agents_dir=str(BASE_DIR),
        session_service_uri=f"sqlite:///{BASE_DIR}/.adk/sessions.db",
        allow_origins=["regex:https?://.*"],
        web=True,
        host="0.0.0.0",
        bind_host="0.0.0.0",
        port=18000,
    )
    # Prepend /app routes before ADK's catch-all static mount
    custom_routes = [
        Route("/app", endpoint=serve_end_user_ui, methods=["GET"]),
        Route("/app/", endpoint=serve_end_user_ui, methods=["GET"]),
        Route("/app/config", endpoint=serve_ui_config, methods=["GET"]),
    ]
    app.router.routes = custom_routes + list(app.router.routes)
    return app


app = build_app()

if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        print("Routes OK:", [getattr(r, "path", "") for r in app.router.routes[:6]])
    else:
        uvicorn.run(app, host="0.0.0.0", port=18000)
