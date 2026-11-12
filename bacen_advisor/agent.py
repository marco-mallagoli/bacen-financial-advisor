"""Root agent and ADK ``App`` for the BACEN Financial & Pix Advisor."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .config import build_model, get_settings
from .memory import MemoryPlugin
from .observability import configure_logging, configure_tracing
from .plugins import GuardrailsPlugin, ObservabilityPlugin, ToolGuardPlugin
from .prompts import CONSTITUTION, COORDINATOR_INSTRUCTION
from .sub_agents import build_knowledge_agent, build_quick_data_agent, build_report_pipeline
from .tools.report_tools import export_report_to_gcs_tool

configure_logging()
configure_tracing()

settings = get_settings()

root_agent = LlmAgent(
    name="bacen_coordinator",
    description="Entry point for Banco Central (BACEN) queries: classifies intent and delegates to the right specialist.",
    model=build_model(settings.models.router),
    static_instruction=CONSTITUTION,
    instruction=COORDINATOR_INSTRUCTION,
    tools=[PreloadMemoryTool(), export_report_to_gcs_tool],
    sub_agents=[build_knowledge_agent(), build_quick_data_agent(), build_report_pipeline()],
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

app = App(
    name=settings.app_name,
    root_agent=root_agent,
    plugins=[ObservabilityPlugin(), GuardrailsPlugin(), ToolGuardPlugin(), MemoryPlugin()],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=settings.compaction_interval,
        overlap_size=settings.compaction_overlap,
        summarizer=LlmEventSummarizer(llm=build_model(settings.models.summarizer)),
    ),
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
)
