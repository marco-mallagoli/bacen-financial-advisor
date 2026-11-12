"""Connection to the BACEN MCP server as an ADK ``McpToolset``."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from urllib.parse import urlparse

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from ..config import get_settings, is_managed_runtime
from ..secrets import SecretNotFoundError, get_secret

logger = logging.getLogger(__name__)

BACEN_DATA_TOOLS: list[str] = [
    "consultar_ranking_reclamacoes_bcb",
    "consultar_indicadores_pix",
    "consultar_taxas_juros_credito",
    "consultar_tarifas_satisfacao_bcb",
    "comparar_instituicoes_bcb",
]
BACEN_REFERENCE_TOOLS: list[str] = [
    "consultar_glossario_metodologia_bcb",
    "buscar_datasets_dados_abertos_bcb",
]
ALL_BACEN_TOOLS: list[str] = BACEN_DATA_TOOLS + BACEN_REFERENCE_TOOLS
_OFFLINE_PLACEHOLDER_URL = "http://127.0.0.1:18081/mcp"
_TOKEN_TTL_SECONDS = 45 * 60


class _IdTokenProvider:
    def __init__(self, audience: str):
        self._audience = audience
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def _fetch(self) -> str:
        if os.getenv("MCP_ID_TOKEN") and not is_managed_runtime():
            return os.environ["MCP_ID_TOKEN"]
        try:
            import google.auth.transport.requests
            import google.oauth2.id_token

            request = google.auth.transport.requests.Request()
            return google.oauth2.id_token.fetch_id_token(request, self._audience)
        except Exception as exc:  # noqa: BLE001
            logger.info("id_token_metadata_unavailable", extra={"error": str(exc)})
        gcloud = shutil.which("gcloud")
        if gcloud and not is_managed_runtime():
            out = subprocess.run(
                [gcloud, "auth", "print-identity-token"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return out.stdout.strip()
        return "local-dev"

    def get(self) -> str:
        with self._lock:
            if not self._token or time.time() >= self._expires_at:
                self._token = self._fetch()
                self._expires_at = time.time() + _TOKEN_TTL_SECONDS
            return self._token


def _resolve_mcp_url() -> str:
    try:
        url = get_secret(get_settings().mcp_url_secret_id, env_override="BACEN_MCP_URL")
    except SecretNotFoundError:
        if is_managed_runtime():
            raise
        return _OFFLINE_PLACEHOLDER_URL
    return url if url.rstrip("/").endswith("/mcp") else url.rstrip("/") + "/mcp"


def build_bacen_toolset(tool_filter: list[str] | None = None) -> McpToolset:
    url = _resolve_mcp_url()
    parsed = urlparse(url)
    audience = f"{parsed.scheme}://{parsed.netloc}"
    token_provider = _IdTokenProvider(audience)

    def _auth_headers(_ctx: ReadonlyContext) -> dict[str, str]:
        return {"Authorization": f"Bearer {token_provider.get()}"}

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            timeout=get_settings().mcp_timeout_seconds,
        ),
        tool_filter=tool_filter or ALL_BACEN_TOOLS,
        header_provider=_auth_headers,
        tool_list_cache_ttl_seconds=600,
    )
