import argparse
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from src import __version__
from src.api.health import router as health_router
from src.api.mcp_server import mcp
from src.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import setup_logging
from src.core.tracing import configure_tracing

setup_logging(settings.log_level)
configure_tracing()


class NormalizeMcpTrailingSlashMiddleware:
    """Serves both ``POST /mcp`` and ``POST /mcp/`` without a 307 redirect."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == "/mcp/":
            scope = dict(scope)
            scope["path"] = "/mcp"
            if "raw_path" in scope:
                scope["raw_path"] = b"/mcp"
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    mcp_http_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",
    )
    session_manager = mcp.session_manager

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with session_manager.run():
            yield

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Custom MCP Server (StreamableHTTP /mcp) para consulta em memória aos Dados Abertos "
            "do Banco Central do Brasil (BACEN / API Olinda): Ranking de Reclamações, Pix/SPI, "
            "Taxas de Juros de Crédito e Tarifas Bancárias."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(NormalizeMcpTrailingSlashMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)

    @app.get("/")
    async def root() -> dict[str, object]:
        return {
            "service": settings.app_name,
            "version": __version__,
            "environment": settings.environment,
            "mcp_endpoint": "/mcp",
            "transport": "StreamableHTTP (stateless JSON-RPC)",
            "gemini_enterprise_compatible": True,
            "health_probes": {"liveness": "/healthz", "readiness": "/readyz"},
        }

    app.mount("/", mcp_http_app)
    return app


app = create_app()


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="BACEN MCP server - Ranking, Pix, Juros & Tarifas")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=settings.port)
    args = parser.parse_args()

    if args.transport == "stdio":
        setup_logging(settings.log_level, use_stderr=True)
        mcp.run(transport="stdio")
    else:
        setup_logging(settings.log_level, use_stderr=False)
        uvicorn.run("src.main:app", host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    run_cli()
