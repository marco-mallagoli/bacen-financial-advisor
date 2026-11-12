"""Agent graph for BACEN Financial & Pix Advisor (Coordinator + Specialists + 4-step Pipeline)."""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import VertexAiSearchTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .config import build_model, get_settings
from .prompts import (
    ANALYST_INSTRUCTION,
    COLLECTOR_INSTRUCTION,
    CONSTITUTION,
    CRITIC_INSTRUCTION,
    KNOWLEDGE_INSTRUCTION,
    PUBLISHER_INSTRUCTION,
    QUICK_DATA_INSTRUCTION,
)
from .schemas import CriticVerdict
from .tools.mcp_bacen import BACEN_DATA_TOOLS, build_bacen_toolset
from .tools.report_tools import (
    calculate_weighted_institution_ranking_tool,
    list_supported_bacen_filters_tool,
)

_DETERMINISTIC = types.GenerateContentConfig(temperature=0.1)
_NO_TRANSFER = {"disallow_transfer_to_parent": True, "disallow_transfer_to_peers": True}
_ANALYTICAL = types.GenerateContentConfig(temperature=0.3)


def build_knowledge_agent() -> LlmAgent:
    settings = get_settings()
    tools: list = [
        build_bacen_toolset(
            ["consultar_glossario_metodologia_bcb", "buscar_datasets_dados_abertos_bcb"]
        )
    ]
    if settings.vertex_search_datastore:
        tools.append(
            VertexAiSearchTool(
                data_store_id=settings.vertex_search_datastore,
                max_results=5,
                bypass_multi_tools_limit=True,
            )
        )
    return LlmAgent(
        **_NO_TRANSFER,
        name="knowledge_agent",
        description="Explains Banco Central (BCB/CMN) concepts, Pix SLAs (SPI, DICT, MED), CET, Ranking methodology and Olinda datasets.",
        model=build_model(settings.models.router),
        static_instruction=CONSTITUTION,
        instruction=KNOWLEDGE_INSTRUCTION,
        tools=tools,
        generate_content_config=_DETERMINISTIC,
    )


def build_quick_data_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        **_NO_TRANSFER,
        name="quick_data_agent",
        description="Fast factual lookups of one BACEN indicator for one institution or credit modality.",
        model=build_model(settings.models.collector),
        static_instruction=CONSTITUTION,
        instruction=QUICK_DATA_INSTRUCTION,
        tools=[
            PreloadMemoryTool(),
            build_bacen_toolset(BACEN_DATA_TOOLS),
            list_supported_bacen_filters_tool,
        ],
        generate_content_config=_DETERMINISTIC,
    )


def build_report_pipeline() -> SequentialAgent:
    settings = get_settings()

    collector = LlmAgent(
        **_NO_TRANSFER,
        name="data_collector",
        description="Retrieves all BACEN datasets (Reclamações, Pix/SPI, Juros Olinda, Tarifas) needed for a comparison or report.",
        model=build_model(settings.models.collector),
        static_instruction=CONSTITUTION,
        instruction=COLLECTOR_INSTRUCTION,
        tools=[
            PreloadMemoryTool(),
            build_bacen_toolset(BACEN_DATA_TOOLS),
            list_supported_bacen_filters_tool,
        ],
        output_key="collected_data",
        generate_content_config=_DETERMINISTIC,
    )
    analyst = LlmAgent(
        **_NO_TRANSFER,
        name="banking_analyst",
        description="Senior banking & central-bank analyst that synthesizes collected BACEN data into executive insights.",
        model=build_model(settings.models.analyst),
        static_instruction=CONSTITUTION,
        instruction=ANALYST_INSTRUCTION,
        tools=[calculate_weighted_institution_ranking_tool],
        output_key="analysis_draft",
        generate_content_config=_ANALYTICAL,
        include_contents="default",
    )
    critic = LlmAgent(
        **_NO_TRANSFER,
        name="quality_critic",
        description="LLM-as-judge that verifies every rate, SLA, index and seal in the draft against BACEN tool outputs.",
        model=build_model(settings.models.critic),
        static_instruction=CONSTITUTION,
        instruction=CRITIC_INSTRUCTION,
        output_schema=CriticVerdict,
        output_key="critic_verdict",
        include_contents="default",
        generate_content_config=_DETERMINISTIC,
    )
    publisher = LlmAgent(
        **_NO_TRANSFER,
        name="report_publisher",
        description="Applies critic fixes and presents the final grounded BACEN report.",
        model=build_model(settings.models.critic),
        static_instruction=CONSTITUTION,
        instruction=PUBLISHER_INSTRUCTION,
        output_key="final_report",
        include_contents="none",
        generate_content_config=_DETERMINISTIC,
    )
    return SequentialAgent(
        name="report_pipeline",
        description="Multi-pillar banking comparisons, credit rate rankings, Pix SLA diagnostics and audited reports.",
        sub_agents=[collector, analyst, critic, publisher],
    )
