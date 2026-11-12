"""Local function tools used by the BACEN analysis and reporting agents."""

from __future__ import annotations

import datetime as dt
import logging
import re
import uuid

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from ..config import get_settings
from ..observability.tracing import get_tracer
from ..pii import redact
from ..schemas import (
    GLOSSARY_TOPICS,
    KNOWN_INSTITUTIONS,
    MODALITY_ALIASES,
    PIX_INDICATORS,
    SEGMENT_ALIASES,
    BacenRankingResult,
    BacenRankingWeights,
    ExportReportResult,
    InstitutionScores,
    RankedInstitution,
    SupportedBacenFiltersResult,
)

logger = logging.getLogger(__name__)
_MAX_REPORT_CHARS = 200_000


def list_supported_bacen_filters() -> dict:
    """Lists the filter values accepted by the Banco Central (BACEN) MCP tools."""
    return SupportedBacenFiltersResult(
        instituicoes=list(KNOWN_INSTITUTIONS),
        segmentos=SEGMENT_ALIASES,
        modalidades_credito=MODALITY_ALIASES,
        indicadores_pix=list(PIX_INDICATORS),
        topicos_glossario=list(GLOSSARY_TOPICS),
        formato_trimestre="YYYY-QN (ex.: 2026-Q3)",
        formato_ano_mes="YYYY-MM (ex.: 2026-09)",
    ).model_dump()


def calculate_weighted_institution_ranking(
    institutions: list[InstitutionScores],
    weights: BacenRankingWeights | None = None,
) -> dict:
    """Ranks financial institutions with custom weights over the 4 BACEN pillars.

    Default weights match the BCB consolidated score:
    atendimento 35%, pix 25%, custo_juros 20%, satisfacao_tarifas 20%.
    ``nota_qualidade_atendimento`` (0-100) is rescaled to 0-10 before weighting.
    """
    try:
        insts = [
            i if isinstance(i, InstitutionScores) else InstitutionScores.model_validate(i)
            for i in institutions
        ]
        w = (
            weights
            if isinstance(weights, BacenRankingWeights)
            else BacenRankingWeights.model_validate(weights or {})
        )
    except ValidationError as exc:
        return BacenRankingResult(
            status="error",
            error_message=f"Invalid input: {exc.errors()[0]['msg']}",
            recovery_hint=(
                "Pass scores verbatim from comparar_instituicoes_bcb: "
                "nota_qualidade_atendimento (0-100) and the 0-10 pillar scores."
            ),
        ).model_dump()

    if not insts:
        return BacenRankingResult(
            status="error",
            error_message="No institutions provided.",
            recovery_hint="Call comparar_instituicoes_bcb first and pass its records.",
        ).model_dump()

    total = w.atendimento + w.pix + w.custo_juros + w.satisfacao_tarifas
    if total <= 0:
        return BacenRankingResult(
            status="error",
            error_message="All weights are zero.",
            recovery_hint="Provide at least one positive weight.",
        ).model_dump()

    norm = {
        "atendimento": w.atendimento / total,
        "pix": w.pix / total,
        "custo_juros": w.custo_juros / total,
        "satisfacao_tarifas": w.satisfacao_tarifas / total,
    }

    scored: list[tuple[str, float, list[str]]] = []
    for item in insts:
        pillars = {
            "atendimento": (
                item.nota_qualidade_atendimento / 10.0
                if item.nota_qualidade_atendimento is not None
                else None
            ),
            "pix": item.nota_estabilidade_pix_0_10,
            "custo_juros": item.nota_competitividade_custo_0_10,
            "satisfacao_tarifas": item.nota_satisfacao_app_0_10,
        }
        available = {k: v for k, v in pillars.items() if v is not None and norm[k] > 0}
        if not available:
            continue
        weight_sum = sum(norm[k] for k in available)
        score = sum(v * norm[k] for k, v in available.items()) / weight_sum
        scored.append((item.instituicao.upper(), round(score, 2), sorted(available)))

    if not scored:
        return BacenRankingResult(
            status="error",
            error_message="No institution has scores for the selected weights.",
            recovery_hint="Fetch pillar scores via comparar_instituicoes_bcb first.",
        ).model_dump()

    scored.sort(key=lambda t: t[1], reverse=True)
    ranking = [
        RankedInstitution(
            position=i + 1, instituicao=n, weighted_score_0_10=s, pillars_used=p
        )
        for i, (n, s, p) in enumerate(scored)
    ]
    with get_tracer().start_as_current_span("bacen.tool.calculate_weighted_institution_ranking"):
        return BacenRankingResult(
            status="success",
            ranking=ranking,
            weights_normalized={k: round(v, 3) for k, v in norm.items()},
        ).model_dump()


def export_report_to_gcs(title: str, markdown_report: str, tool_context: ToolContext) -> dict:
    """Publishes the final, critic-approved BACEN Markdown report to Cloud Storage (HITL)."""
    settings = get_settings()
    if not settings.reports_bucket:
        return ExportReportResult(
            status="error",
            error_message="REPORTS_BUCKET is not configured.",
            recovery_hint="Tell the user export is unavailable in this local environment and keep the report inline.",
        ).model_dump()
    if not title.strip() or not markdown_report.strip():
        return ExportReportResult(
            status="error",
            error_message="Empty title or report.",
            recovery_hint="Pass non-empty title and markdown_report.",
        ).model_dump()
    if len(markdown_report) > _MAX_REPORT_CHARS:
        return ExportReportResult(
            status="error",
            error_message="Report too large.",
            recovery_hint="Summarize below 200,000 chars.",
        ).model_dump()

    report_id = f"{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    user_id = re.sub(r"[^A-Za-z0-9_-]", "_", getattr(tool_context, "user_id", None) or "anonymous")[:64]
    blob_name = f"bacen_reports/{user_id}/{report_id}.md"
    body = f"# {title}\n\n{markdown_report}\n"
    try:
        from google.cloud import storage

        blob = storage.Client(project=settings.project_id).bucket(settings.reports_bucket).blob(blob_name)
        blob.metadata = {"title": redact(title) or "", "report_id": report_id}
        blob.upload_from_string(redact(body) or "", content_type="text/markdown; charset=utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.error("bacen_report_export_failed", extra={"report_id": report_id, "error": str(exc)})
        return ExportReportResult(
            status="error",
            report_id=report_id,
            error_message=f"Upload failed: {exc}",
            recovery_hint="Show the report inline and tell the user export failed.",
        ).model_dump()

    uri = f"gs://{settings.reports_bucket}/{blob_name}"
    tool_context.state["last_report_uri"] = uri
    return ExportReportResult(status="success", gcs_uri=uri, report_id=report_id).model_dump()


list_supported_bacen_filters_tool = FunctionTool(list_supported_bacen_filters)
calculate_weighted_institution_ranking_tool = FunctionTool(calculate_weighted_institution_ranking)
export_report_to_gcs_tool = FunctionTool(export_report_to_gcs, require_confirmation=True)
