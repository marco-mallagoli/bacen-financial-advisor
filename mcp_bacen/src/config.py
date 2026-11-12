from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the BACEN (Banco Central do Brasil) MCP server.

    The service runs 100% in memory (RAM): Polars DataFrames + live Olinda OData / CKAN
    with instant seed fallback.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "mcp-bacen"
    environment: str = "production"
    port: int = 18081
    log_level: str = "INFO"

    google_cloud_project: str = ""
    enable_cloud_trace: bool | None = None
    otel_service_name: str = "mcp-bacen"

    cache_ttl_seconds: int = 3600
    http_timeout_seconds: float = 12.0
    default_max_rows: int = 25
    max_allowed_rows: int = 50
    enable_live_http_fetch: bool = False

    # Official Banco Central do Brasil (BCB) Open Data / Olinda OData / SGS endpoints
    bcb_ckan_api_url: str = "https://dadosabertos.bcb.gov.br/api/3/action"
    bcb_olinda_base_url: str = "https://olinda.bcb.gov.br/olinda/servico"
    bcb_ranking_reclamacoes_url: str = "https://www.bcb.gov.br/ranking/index.asp"
    bcb_pix_estatisticas_url: str = (
        "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
    )
    bcb_taxas_juros_url: str = (
        "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosMensalPorMes?$top=100&$format=json"
    )
    bcb_tarifas_url: str = (
        "https://olinda.bcb.gov.br/olinda/servico/informes_lista_tarifas_por_instituicao_financeira/versao/v1/odata"
    )


settings = Settings()
