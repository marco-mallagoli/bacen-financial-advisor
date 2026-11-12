"""Response entities shared by every BACEN tool (field names are the API contract).

Field names stay in Portuguese on purpose: they are the wire contract consumed by the
ADK agent (``bacen_advisor/schemas.py``: ``registros``, ``metadados_fonte``,
``origem_leitura`` ...) and by Gemini Enterprise actions.
"""

from typing import Any

from pydantic import BaseModel, Field


class FonteMetadados(BaseModel):
    """Provenance metadata for the BACEN (Banco Central) data source behind a response."""

    pilar: str = Field(description="BACEN regulatory/financial pillar that was queried")
    url_oficial_bcb: str = Field(description="Official dataset/API URL on BCB's open-data portal (Olinda/CKAN)")
    origem_leitura: str = Field(
        description="Effective data origin: 'cache_ram_http', 'http_olinda_bcb' or 'fallback_seed_ram'"
    )
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    total_registros_encontrados: int = Field(description="Total rows matched before pagination")
    registros_retornados: int = Field(description="Rows returned in this response")


class RespostaPadraoBacen(BaseModel):
    """Standard JSON output of every BACEN MCP tool / Gemini Enterprise action."""

    resumo_executivo: str = Field(
        description="Direct analytical summary answering the query with the main highlights"
    )
    estatisticas_agregadas: dict[str, Any] = Field(
        description="Consolidated metrics (averages, best/worst institutions, SLA compliance)"
    )
    registros: list[dict[str, Any]] = Field(
        description="Main filtered and sorted rows (limited to 25-50 rows)"
    )
    tabela_markdown: str = Field(
        description="Markdown table ready to be shown to the user"
    )
    metadados_fonte: FonteMetadados = Field(
        description="Official BCB source, in-memory cache state and applied filters"
    )
