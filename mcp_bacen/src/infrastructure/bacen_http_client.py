import logging
from collections.abc import Callable
from typing import Any

import httpx
import polars as pl

from src.config import settings
from src.infrastructure.fallback_seed import (
    FALLBACK_BCB_DATASETS,
    build_fallback_indicadores_pix,
    build_fallback_ranking_reclamacoes,
    build_fallback_tarifas_satisfacao,
    build_fallback_taxas_juros,
)
from src.infrastructure.memory_cache import memory_cache

logger = logging.getLogger(__name__)


class BacenHttpClient:
    """Async HTTP client for Banco Central do Brasil's Olinda OData & CKAN APIs, fully in memory.

    Supports live OData JSON ingestion (``$format=json`` -> ``value`` array -> Polars DataFrame)
    when ``ENABLE_LIVE_HTTP_FETCH=true`` and falls back deterministically to the embedded
    seed snapshot so latency stays < 3 s and offline environments work seamlessly.
    """

    def __init__(self, timeout_seconds: float = settings.http_timeout_seconds) -> None:
        self._timeout = timeout_seconds

    async def _try_fetch_odata_json(
        self,
        url: str,
        required_columns: set[str],
    ) -> pl.DataFrame | None:
        if not settings.enable_live_http_fetch:
            return None

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": "mcp-bacen/0.1.0 (+https://dadosabertos.bcb.gov.br)"},
            ) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None
                payload = response.json()
                rows = payload.get("value", []) if isinstance(payload, dict) else []
                if not rows:
                    return None
                df = pl.DataFrame(rows)
                normalized_cols = {c.strip().lower() for c in df.columns}
                if required_columns.issubset(normalized_cols):
                    return df
                return None
        except Exception as exc:
            logger.info(
                "bcb_live_fetch_failed_using_seed",
                extra={"url": url, "error_type": type(exc).__name__, "error": str(exc)},
            )
            return None

    async def _get_or_load_dataframe(
        self,
        cache_key: str,
        url: str,
        required_columns: set[str],
        fallback_builder: Callable[[], pl.DataFrame],
    ) -> tuple[pl.DataFrame, str]:
        cached = memory_cache.get(cache_key)
        if cached is not None:
            return cached

        live_df = await self._try_fetch_odata_json(url, required_columns)
        if live_df is not None:
            memory_cache.set(cache_key, live_df, source_type="http_olinda_bcb")
            return live_df, "http_olinda_bcb"

        fallback_df = fallback_builder()
        memory_cache.set(cache_key, fallback_df, source_type="fallback_seed_ram")
        return fallback_df, "fallback_seed_ram"

    async def get_ranking_reclamacoes_df(self) -> tuple[pl.DataFrame, str]:
        return await self._get_or_load_dataframe(
            cache_key="bcb_df_ranking_reclamacoes",
            url=settings.bcb_ranking_reclamacoes_url,
            required_columns={"trimestre", "instituicao", "segmento", "indice_reclamacoes_bcb"},
            fallback_builder=build_fallback_ranking_reclamacoes,
        )

    async def get_indicadores_pix_df(self) -> tuple[pl.DataFrame, str]:
        return await self._get_or_load_dataframe(
            cache_key="bcb_df_indicadores_pix",
            url=settings.bcb_pix_estatisticas_url,
            required_columns={"trimestre", "instituicao", "indicador", "valor_medido"},
            fallback_builder=build_fallback_indicadores_pix,
        )

    async def get_taxas_juros_df(self) -> tuple[pl.DataFrame, str]:
        return await self._get_or_load_dataframe(
            cache_key="bcb_df_taxas_juros",
            url=settings.bcb_taxas_juros_url,
            required_columns={"ano_mes", "instituicao", "modalidade", "taxa_juros_mensal_pct"},
            fallback_builder=build_fallback_taxas_juros,
        )

    async def get_tarifas_satisfacao_df(self) -> tuple[pl.DataFrame, str]:
        return await self._get_or_load_dataframe(
            cache_key="bcb_df_tarifas_satisfacao",
            url=settings.bcb_tarifas_url,
            required_columns={"ano_referencia", "instituicao", "cesta_servicos_mensal_brl"},
            fallback_builder=build_fallback_tarifas_satisfacao,
        )

    async def search_bcb_datasets(
        self,
        termo_busca: str = "pix reclamacoes juros tarifas",
        limite: int = 10,
    ) -> tuple[list[dict[str, Any]], str]:
        if settings.enable_live_http_fetch:
            try:
                async with httpx.AsyncClient(
                    timeout=min(self._timeout, 6.0),
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(
                        f"{settings.bcb_ckan_api_url}/package_search",
                        params={"q": termo_busca, "rows": min(limite, 25)},
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        results = payload.get("result", {}).get("results", [])
                        if results:
                            parsed = []
                            for pkg in results[:limite]:
                                resources = pkg.get("resources", [])
                                first_url = resources[0].get("url", "") if resources else ""
                                parsed.append(
                                    {
                                        "id": pkg.get("id", ""),
                                        "name": pkg.get("name", ""),
                                        "title": pkg.get("title", ""),
                                        "notes": (pkg.get("notes") or "")[:300],
                                        "organization": (pkg.get("organization") or {}).get(
                                            "title", "Banco Central do Brasil"
                                        ),
                                        "url": first_url or settings.bcb_olinda_base_url,
                                        "format": resources[0].get("format", "OData/JSON")
                                        if resources
                                        else "OData/JSON",
                                    }
                                )
                            return parsed, "http_olinda_bcb"
            except Exception as exc:
                logger.info(
                    "bcb_ckan_search_failed_using_seed",
                    extra={"termo_busca": termo_busca, "error": str(exc)},
                )

        term_tokens = [t.lower() for t in termo_busca.split() if len(t) > 2]
        filtered = []
        for item in FALLBACK_BCB_DATASETS:
            haystack = f"{item['title']} {item['notes']} {item['name']}".lower()
            if not term_tokens or any(tok in haystack for tok in term_tokens):
                filtered.append(item)
        return (filtered or FALLBACK_BCB_DATASETS)[:limite], "fallback_seed_ram"


bacen_http_client = BacenHttpClient()
