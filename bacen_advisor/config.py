"""Centralized runtime configuration for the BACEN Financial & Pix Advisor."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ModelRouting:
    router: str = field(default_factory=lambda: os.getenv("MODEL_ROUTER", "gemini-flash-latest"))
    collector: str = field(default_factory=lambda: os.getenv("MODEL_COLLECTOR", "gemini-flash-latest"))
    analyst: str = field(default_factory=lambda: os.getenv("MODEL_ANALYST", "gemini-pro-latest"))
    critic: str = field(default_factory=lambda: os.getenv("MODEL_CRITIC", "gemini-flash-latest"))
    summarizer: str = field(
        default_factory=lambda: os.getenv("MODEL_SUMMARIZER", "gemini-flash-latest")
    )


@dataclass(frozen=True)
class Settings:
    project_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    location: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    app_name: str = field(default_factory=lambda: os.getenv("BACEN_APP_NAME", "bacen_advisor"))

    mcp_url_secret_id: str = field(
        default_factory=lambda: os.getenv("BACEN_MCP_URL_SECRET_ID", "bacen-mcp-url")
    )
    mcp_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("MCP_TIMEOUT_SECONDS", "30"))
    )

    reports_bucket: str = field(default_factory=lambda: os.getenv("REPORTS_BUCKET", ""))
    vertex_search_datastore: str = field(
        default_factory=lambda: (
            os.getenv("BACEN_AGENT_SEARCH_DATASTORE") or os.getenv("VERTEX_SEARCH_DATASTORE", "")
        )
    )

    model_armor_template: str = field(
        default_factory=lambda: os.getenv("MODEL_ARMOR_TEMPLATE", "")
    )
    guardrails_fail_mode: str = field(
        default_factory=lambda: os.getenv("GUARDRAILS_FAIL_MODE", "open").lower()
    )

    pii_redaction_mode: str = field(
        default_factory=lambda: os.getenv("PII_REDACTION_MODE", "regex")
    )
    enable_cloud_trace: bool = field(
        default_factory=lambda: _env_bool("ENABLE_CLOUD_TRACE", False)
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    compaction_interval: int = field(
        default_factory=lambda: int(os.getenv("COMPACTION_INTERVAL", "6"))
    )
    compaction_overlap: int = field(
        default_factory=lambda: int(os.getenv("COMPACTION_OVERLAP", "1"))
    )

    models: ModelRouting = field(default_factory=ModelRouting)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def is_managed_runtime() -> bool:
    return bool(os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID") or os.getenv("K_SERVICE"))


def build_model(model_name: str):
    from google.adk.models import Gemini
    from google.genai import types

    return Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(
            attempts=4,
            initial_delay=1.0,
            max_delay=20.0,
            exp_base=2.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
    )
