"""Structural tests: BACEN agent graph, model routing, HITL wiring, memory redaction, prod hardening."""

import asyncio
import json
import sys
import types as pytypes
from pathlib import Path
from types import SimpleNamespace

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.events.event import Event
from google.adk.sessions.session import Session
from google.genai import types

from bacen_advisor import secrets
from bacen_advisor.agent import app, root_agent
from bacen_advisor.memory import MemoryPlugin, RedactingMemoryService
from bacen_advisor.plugins import GuardrailsPlugin, ObservabilityPlugin, ToolGuardPlugin
from bacen_advisor.prompts import CONSTITUTION, PUBLISHER_INSTRUCTION
from bacen_advisor.schemas import MCP_ARG_SCHEMAS, CriticVerdict
from bacen_advisor.tools import mcp_bacen, report_tools


def _by_name(agent, name):
    if agent.name == name:
        return agent
    for sub in agent.sub_agents:
        found = _by_name(sub, name)
        if found:
            return found
    return None


def test_coordinator_routes_to_specialists():
    names = [a.name for a in root_agent.sub_agents]
    assert names == ["knowledge_agent", "quick_data_agent", "report_pipeline"]


def test_report_pipeline_is_sequential_with_critic():
    pipeline = _by_name(root_agent, "report_pipeline")
    assert isinstance(pipeline, SequentialAgent)
    assert [a.name for a in pipeline.sub_agents] == [
        "data_collector",
        "banking_analyst",
        "quality_critic",
        "report_publisher",
    ]
    critic = _by_name(root_agent, "quality_critic")
    assert critic.output_schema is CriticVerdict


def test_model_routing_flash_vs_pro():
    analyst = _by_name(root_agent, "banking_analyst")
    collector = _by_name(root_agent, "data_collector")
    assert "pro" in analyst.model.model
    assert "flash" in collector.model.model
    assert analyst.model.retry_options.attempts >= 3


def test_hitl_export_only_on_coordinator():
    for agent in [root_agent, *root_agent.sub_agents]:
        tools = [getattr(t, "name", "") for t in getattr(agent, "tools", [])]
        if agent is root_agent:
            assert "export_report_to_gcs" in tools
        else:
            assert "export_report_to_gcs" not in tools


def test_app_wires_plugins_compaction_and_cache():
    kinds = {type(p) for p in app.plugins}
    assert {GuardrailsPlugin, ToolGuardPlugin, ObservabilityPlugin, MemoryPlugin} <= kinds
    assert isinstance(app.plugins[0], ObservabilityPlugin)
    assert app.events_compaction_config is not None
    assert app.context_cache_config is not None


def test_all_llm_agents_share_constitution_and_no_specialist_transfer():
    def walk(a):
        yield a
        for s in a.sub_agents:
            yield from walk(s)

    for agent in walk(root_agent):
        if isinstance(agent, LlmAgent):
            assert "Hard rules" in agent.static_instruction
            if agent is not root_agent:
                assert agent.disallow_transfer_to_parent and agent.disallow_transfer_to_peers


class _CaptureMemory:
    def __init__(self):
        self.session = None

    async def add_session_to_memory(self, session):
        self.session = session

    async def search_memory(self, **_):
        return None


async def test_memory_is_redacted_before_storage():
    inner = _CaptureMemory()
    svc = RedactingMemoryService(inner)
    session = Session(
        id="s1",
        app_name="bacen_advisor",
        user_id="u1",
        events=[
            Event(
                author="user",
                content=types.Content(
                    role="user",
                    parts=[types.Part(text="Sou do Nubank, meu CPF é 123.456.789-09 e email ana@nu.com")],
                ),
            )
        ],
    )
    await svc.add_session_to_memory(session)
    stored = inner.session.events[0].content.parts[0].text
    assert "123.456.789-09" not in stored
    assert "ana@nu.com" not in stored
    assert "Nubank" in stored


def test_dev_overrides_ignored_in_managed_runtime(monkeypatch):
    class _FakeSM:
        def access_secret_version(self, request):
            payload = SimpleNamespace(data=b"https://mcp-bacen-from-sm.run.app")
            return SimpleNamespace(payload=payload)

    fake_module = pytypes.SimpleNamespace(SecretManagerServiceClient=lambda: _FakeSM())
    monkeypatch.setitem(sys.modules, "google.cloud.secretmanager", fake_module)
    monkeypatch.setenv("GOOGLE_CLOUD_AGENT_ENGINE_ID", "123")
    monkeypatch.setenv("BACEN_MCP_URL", "https://attacker.example")
    secrets.get_secret.cache_clear()
    try:
        value = secrets.get_secret("bacen-mcp-url", env_override="BACEN_MCP_URL")
    finally:
        secrets.get_secret.cache_clear()
    assert value == "https://mcp-bacen-from-sm.run.app"


def test_export_sanitizes_user_id(monkeypatch):
    monkeypatch.setattr(report_tools, "get_settings", lambda: SimpleNamespace(reports_bucket="", project_id="p"))
    out = report_tools.export_report_to_gcs("t", "r", SimpleNamespace(user_id="../x", state={}))
    assert out["status"] == "error"


async def test_memory_plugin_persists_every_invocation():
    inner = _CaptureMemory()
    session = Session(id="s1", app_name="bacen_advisor", user_id="u1", events=[])
    ctx = SimpleNamespace(memory_service=inner, session=session, invocation_id="i1")
    await MemoryPlugin().after_run_callback(invocation_context=ctx)
    await asyncio.sleep(0)
    assert inner.session is session


def test_no_proactive_save_offer_in_instructions():
    assert "Never proactively offer or suggest saving/exporting" in CONSTITUTION
    assert "Do not offer, suggest or ask about\n  saving, exporting or sharing" in PUBLISHER_INSTRUCTION


def test_mcp_url_uses_offline_placeholder_outside_managed_runtime(monkeypatch):
    monkeypatch.delenv("BACEN_MCP_URL", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_AGENT_ENGINE_ID", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.setattr(
        mcp_bacen,
        "get_secret",
        lambda *_a, **_kw: (_ for _ in ()).throw(secrets.SecretNotFoundError("no secret")),
    )
    assert mcp_bacen._resolve_mcp_url() == mcp_bacen._OFFLINE_PLACEHOLDER_URL


def test_golden_dataset_trajectories_and_schemas_are_valid():
    data_dir = Path(__file__).resolve().parents[1] / "eval" / "data"
    evalset = json.loads((data_dir / "bacen_golden.evalset.json").read_text(encoding="utf-8"))
    config = json.loads((data_dir / "test_config.json").read_text(encoding="utf-8"))

    assert "tool_trajectory_avg_score" in config["criteria"]
    assert "final_response_match_v2" in config["criteria"]
    assert len(evalset["eval_cases"]) >= 4

    specialist_names = {a.name for a in root_agent.sub_agents}
    for case in evalset["eval_cases"]:
        assert case["session_input"]["app_name"] == app.name
        for turn in case["conversation"]:
            assert turn["user_content"]["parts"][0]["text"]
            assert turn["final_response"]["parts"][0]["text"]
            for tool_use in turn["intermediate_data"]["tool_uses"]:
                name = tool_use["name"]
                args = tool_use.get("args", {})
                if name == "transfer_to_agent":
                    assert args["agent_name"] in specialist_names
                elif name in MCP_ARG_SCHEMAS:
                    MCP_ARG_SCHEMAS[name].model_validate(args)
                else:
                    raise AssertionError(f"Unknown tool in golden dataset: {name}")
