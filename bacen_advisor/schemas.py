"""Explicit Pydantic schemas for the BACEN Financial & Pix Advisor."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

KNOWN_INSTITUTIONS: tuple[str, ...] = (
    "ITAU",
    "BRADESCO",
    "BANCO DO BRASIL",
    "CAIXA",
    "SANTANDER",
    "NUBANK",
    "INTER",
    "BTG PACTUAL",
    "C6 BANK",
    "SICREDI",
)

SEGMENT_ALIASES: dict[str, str] = {
    "TODOS": "TODOS",
    "TODAS": "TODOS",
    "GERAL": "TODOS",
    "BANCOS_VAREJO": "BANCOS_VAREJO",
    "VAREJO": "BANCOS_VAREJO",
    "TRADICIONAIS": "BANCOS_VAREJO",
    "BANCOS TRADICIONAIS": "BANCOS_VAREJO",
    "S1": "BANCOS_VAREJO",
    "BANCOS_DIGITAIS": "BANCOS_DIGITAIS",
    "DIGITAIS": "BANCOS_DIGITAIS",
    "BANCOS DIGITAIS": "BANCOS_DIGITAIS",
    "FINTECHS": "BANCOS_DIGITAIS",
    "IP": "BANCOS_DIGITAIS",
    "COOPERATIVAS_ATACADO": "COOPERATIVAS_ATACADO",
    "COOPERATIVAS": "COOPERATIVAS_ATACADO",
    "ATACADO": "COOPERATIVAS_ATACADO",
}

MODALITY_ALIASES: dict[str, str] = {
    "CONSIGNADO_INSS": "CONSIGNADO_INSS",
    "CONSIGNADO": "CONSIGNADO_INSS",
    "CONSIGNADO INSS": "CONSIGNADO_INSS",
    "INSS": "CONSIGNADO_INSS",
    "CREDITO_PESSOAL": "CREDITO_PESSOAL",
    "CREDITO PESSOAL": "CREDITO_PESSOAL",
    "PESSOAL": "CREDITO_PESSOAL",
    "CARTAO_ROTATIVO": "CARTAO_ROTATIVO",
    "ROTATIVO": "CARTAO_ROTATIVO",
    "CARTAO": "CARTAO_ROTATIVO",
    "FINANCIAMENTO_IMOBILIARIO": "FINANCIAMENTO_IMOBILIARIO",
    "IMOBILIARIO": "FINANCIAMENTO_IMOBILIARIO",
    "CAPITAL_GIRO_PJ": "CAPITAL_GIRO_PJ",
    "CAPITAL DE GIRO": "CAPITAL_GIRO_PJ",
    "PJ": "CAPITAL_GIRO_PJ",
}

PIX_INDICATORS: tuple[str, ...] = (
    "disponibilidade_spi_pct",
    "tempo_liquidacao_p95_seg",
    "tempo_consulta_dict_p99_ms",
    "taxa_sucesso_transacional_pct",
    "indice_med_contestacao_100k",
)

GLOSSARY_TOPICS: tuple[str, ...] = (
    "geral",
    "ranking_reclamacoes",
    "indicadores_pix_spi",
    "taxas_juros_credito",
    "tarifas_servicos_essenciais",
    "segmentos_instituicoes",
)

_ANO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_TRIMESTRE = re.compile(r"^\d{4}-Q[1-4]$", re.IGNORECASE)


def normalize_segment(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().upper()
    if key in SEGMENT_ALIASES:
        return SEGMENT_ALIASES[key]
    for alias, canonical in SEGMENT_ALIASES.items():
        if alias in key:
            return canonical
    raise ValueError(
        f"Invalid segmento '{value}'. Use TODOS, BANCOS_VAREJO, BANCOS_DIGITAIS or COOPERATIVAS_ATACADO."
    )


def normalize_modality(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().upper()
    if key in MODALITY_ALIASES:
        return MODALITY_ALIASES[key]
    for alias, canonical in MODALITY_ALIASES.items():
        if alias in key:
            return canonical
    raise ValueError(
        f"Invalid modalidade '{value}'. Use CONSIGNADO_INSS, CREDITO_PESSOAL, CARTAO_ROTATIVO, "
        "FINANCIAMENTO_IMOBILIARIO or CAPITAL_GIRO_PJ."
    )


class _BacenMcpArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("segmento", mode="before", check_fields=False)
    @classmethod
    def _seg(cls, v: str | None) -> str | None:
        return normalize_segment(v)

    @field_validator("trimestre", mode="before", check_fields=False)
    @classmethod
    def _trim(cls, v: str | None) -> str | None:
        if v is None:
            return None
        val = v.strip().upper()
        if not _TRIMESTRE.match(val):
            raise ValueError(f"Invalid trimestre '{v}'. Use YYYY-QN format, e.g. 2026-Q3.")
        return val

    @field_validator("ano_mes", mode="before", check_fields=False)
    @classmethod
    def _am(cls, v: str | None) -> str | None:
        if v is None:
            return None
        val = v.strip()
        if not _ANO_MES.match(val):
            raise ValueError(f"Invalid ano_mes '{v}'. Use YYYY-MM format, e.g. 2026-09.")
        return val


class RankingReclamacoesArgs(_BacenMcpArgs):
    instituicao: str | None = Field(default=None, description="Institution name, e.g. 'Nubank' or 'Itaú'.")
    segmento: str | None = Field(default=None, description="BANCOS_VAREJO, BANCOS_DIGITAIS, COOPERATIVAS_ATACADO or TODOS.")
    motivo: str | None = Field(default=None, description="Optional complaint driver keyword.")
    trimestre: str | None = Field(default=None, description="Quarter in YYYY-QN format, e.g. 2026-Q3.")
    limite: int = Field(default=25, ge=1, le=200)


class IndicadoresPixArgs(_BacenMcpArgs):
    instituicao: str | None = Field(default=None, description="Institution name.")
    segmento: str | None = Field(default=None, description="Segment filter.")
    indicador: Literal[PIX_INDICATORS] | None = Field(default=None, description="Pix operational indicator id.")  # type: ignore[valid-type]
    trimestre: str | None = Field(default=None, description="Quarter in YYYY-QN format, e.g. 2026-Q3.")
    limite: int = Field(default=25, ge=1, le=200)


class TaxasJurosArgs(_BacenMcpArgs):
    instituicao: str | None = Field(default=None, description="Institution name.")
    segmento: str | None = Field(default=None, description="Segment filter.")
    modalidade: str | None = Field(default=None, description="Credit modality code.")
    ano_mes: str | None = Field(default=None, description="Reference month YYYY-MM.")
    limite: int = Field(default=25, ge=1, le=200)

    @field_validator("modalidade", mode="before")
    @classmethod
    def _mod(cls, v: str | None) -> str | None:
        return normalize_modality(v)


class TarifasSatisfacaoArgs(_BacenMcpArgs):
    instituicao: str | None = Field(default=None, description="Institution name.")
    segmento: str | None = Field(default=None, description="Segment filter.")
    ano_referencia: int | None = Field(default=None, ge=2020, le=2100)
    limite: int = Field(default=25, ge=1, le=200)


class CompararInstituicoesArgs(_BacenMcpArgs):
    segmento: str = Field(default="TODOS", description="Segment filter (TODOS, BANCOS_VAREJO, BANCOS_DIGITAIS, COOPERATIVAS_ATACADO).")
    modalidade_credito: str = Field(default="CREDITO_PESSOAL", description="Credit modality used for interest comparison.")
    instituicoes: list[str] | None = Field(default=None, max_length=12)

    @field_validator("modalidade_credito", mode="before")
    @classmethod
    def _mod_cred(cls, v: str | None) -> str:
        return normalize_modality(v) or "CREDITO_PESSOAL"


class BuscarDatasetsBcbArgs(_BacenMcpArgs):
    termo_busca: str = Field(default="pix reclamacoes juros tarifas", min_length=2, max_length=200)
    limite: int = Field(default=10, ge=1, le=50)


class GlossarioBcbArgs(_BacenMcpArgs):
    topico: Literal[GLOSSARY_TOPICS] | None = Field(default="geral")  # type: ignore[valid-type]


MCP_ARG_SCHEMAS: dict[str, type[BaseModel]] = {
    "consultar_ranking_reclamacoes_bcb": RankingReclamacoesArgs,
    "consultar_indicadores_pix": IndicadoresPixArgs,
    "consultar_taxas_juros_credito": TaxasJurosArgs,
    "consultar_tarifas_satisfacao_bcb": TarifasSatisfacaoArgs,
    "comparar_instituicoes_bcb": CompararInstituicoesArgs,
    "buscar_datasets_dados_abertos_bcb": BuscarDatasetsBcbArgs,
    "consultar_glossario_metodologia_bcb": GlossarioBcbArgs,
}


class McpSourceMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    pilar: str | None = None
    origem_leitura: str | None = None


class McpStructuredContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    registros: list[dict] | None = None
    metadados_fonte: McpSourceMetadata | None = None


class McpToolOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    isError: bool = False
    structuredContent: McpStructuredContent | None = None
    recovery_hint: str | None = None


class SupportedBacenFiltersResult(BaseModel):
    status: Literal["success"] = "success"
    instituicoes: list[str]
    segmentos: dict[str, str]
    modalidades_credito: dict[str, str]
    indicadores_pix: list[str]
    topicos_glossario: list[str]
    formato_trimestre: str
    formato_ano_mes: str


class InstitutionScores(BaseModel):
    instituicao: str = Field(description="Institution name, e.g. 'NUBANK' or 'ITAU'.")
    nota_qualidade_atendimento: float | None = Field(default=None, ge=0, le=100, description="BCB customer service score 0-100.")
    nota_estabilidade_pix_0_10: float | None = Field(default=None, ge=0, le=10, description="Pix/SPI operational score 0-10.")
    nota_competitividade_custo_0_10: float | None = Field(default=None, ge=0, le=10, description="Interest rate competitiveness score 0-10.")
    nota_satisfacao_app_0_10: float | None = Field(default=None, ge=0, le=10, description="Digital app & fee satisfaction score 0-10.")


class BacenRankingWeights(BaseModel):
    atendimento: float = Field(default=0.35, ge=0, description="Weight for BCB Ouvidoria / Complaints score (default 0.35).")
    pix: float = Field(default=0.25, ge=0, description="Weight for Pix/SPI stability (default 0.25).")
    custo_juros: float = Field(default=0.20, ge=0, description="Weight for credit interest competitiveness (default 0.20).")
    satisfacao_tarifas: float = Field(default=0.20, ge=0, description="Weight for digital satisfaction & fees (default 0.20).")


class RankedInstitution(BaseModel):
    position: int = Field(ge=1)
    instituicao: str
    weighted_score_0_10: float = Field(ge=0, le=10)
    pillars_used: list[str]


class BacenRankingResult(BaseModel):
    status: Literal["success", "error"]
    ranking: list[RankedInstitution] = Field(default_factory=list)
    weights_normalized: dict[str, float] = Field(default_factory=dict)
    error_message: str | None = None
    recovery_hint: str | None = None


class ExportReportResult(BaseModel):
    status: Literal["success", "error", "rejected"]
    gcs_uri: str | None = None
    report_id: str | None = None
    error_message: str | None = None
    recovery_hint: str | None = None


class CriticIssue(BaseModel):
    claim: str
    problem: Literal[
        "number_not_in_tool_output",
        "missing_source_or_period",
        "wrong_interpretation",
        "unsupported_recommendation",
        "off_topic_or_unsafe",
    ]
    fix: str


class CriticVerdict(BaseModel):
    approved: bool
    groundedness_score: int = Field(ge=1, le=5)
    issues: list[CriticIssue] = Field(default_factory=list)
    summary: str


TOOL_JSON_SCHEMAS: dict[str, dict[str, dict]] = {
    **{
        name: {
            "input": model.model_json_schema(),
            "output": McpToolOutput.model_json_schema(),
        }
        for name, model in MCP_ARG_SCHEMAS.items()
    },
    "list_supported_bacen_filters": {
        "input": {"type": "object", "properties": {}, "additionalProperties": False},
        "output": SupportedBacenFiltersResult.model_json_schema(),
    },
    "calculate_weighted_institution_ranking": {
        "input": {
            "type": "object",
            "properties": {
                "institutions": {"type": "array", "items": InstitutionScores.model_json_schema()},
                "weights": BacenRankingWeights.model_json_schema(),
            },
            "required": ["institutions"],
            "additionalProperties": False,
        },
        "output": BacenRankingResult.model_json_schema(),
    },
    "export_report_to_gcs": {
        "input": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "markdown_report": {"type": "string"},
            },
            "required": ["title", "markdown_report"],
            "additionalProperties": False,
        },
        "output": ExportReportResult.model_json_schema(),
    },
}
