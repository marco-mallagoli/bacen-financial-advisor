"""Guardrails plugin for the BACEN Financial & Pix Advisor."""

from __future__ import annotations

import asyncio
import re
from functools import lru_cache

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

from ..config import get_settings
from ..observability.logging import get_logger
from ..observability.tracing import get_tracer

logger = get_logger(__name__)

_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all |the )?(previous|prior|above) (instructions|rules)",
        r"ignore (todas )?(as )?instru[cç][oõ]es (anteriores|acima)",
        r"esque[cç]a (todas )?(as )?(suas )?(regras|instru[cç][oõ]es)",
        r"(reveal|show|print|mostre|revele).{0,30}(system prompt|prompt do sistema|instru[cç][oõ]es internas)",
        r"you are now (dan|developer mode|unfiltered)",
        r"\bjailbreak\b",
    )
]

_BLOCK_MESSAGE = (
    "Não posso ajudar com esse pedido. Sou um assistente especializado exclusivamente nos Dados "
    "Abertos oficiais do Banco Central do Brasil (BACEN): Ranking de Reclamações, indicadores "
    "operacionais do Pix (SPI/DICT/MED), taxas de juros de crédito e tarifas bancárias."
)

_OUTPUT_LEAK_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"#\s*Hard rules \(never break\)",
        r"static_instruction\s*=\s*CONSTITUTION",
    )
]


def detect_prompt_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def detect_unsafe_output(text: str) -> bool:
    return any(p.search(text) for p in _OUTPUT_LEAK_PATTERNS)


@lru_cache(maxsize=1)
def _model_armor_client():  # pragma: no cover
    from google.cloud import modelarmor_v1

    location = get_settings().location
    return modelarmor_v1.ModelArmorClient(
        client_options={"api_endpoint": f"modelarmor.{location}.rep.googleapis.com"}
    )


def _model_armor_blocks(text: str, *, is_prompt: bool) -> bool:  # pragma: no cover
    template = get_settings().model_armor_template
    if not template or not text:
        return False
    try:
        from google.cloud import modelarmor_v1

        client = _model_armor_client()
        data = modelarmor_v1.DataItem(text=text)
        if is_prompt:
            result = client.sanitize_user_prompt(
                request=modelarmor_v1.SanitizeUserPromptRequest(name=template, user_prompt_data=data)
            )
        else:
            result = client.sanitize_model_response(
                request=modelarmor_v1.SanitizeModelResponseRequest(name=template, model_response_data=data)
            )
        return (
            result.sanitization_result.filter_match_state
            == modelarmor_v1.FilterMatchState.MATCH_FOUND
        )
    except Exception as exc:  # noqa: BLE001
        fail_closed = get_settings().guardrails_fail_mode == "closed"
        logger.warning("model_armor_unavailable", extra={"error": str(exc), "fail_closed": fail_closed})
        return fail_closed


def _blocked_response() -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=_BLOCK_MESSAGE)]))


class GuardrailsPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="guardrails")
        self._blocked_invocations: set[str] = set()

    async def on_user_message_callback(
        self, *, invocation_context: InvocationContext, user_message: types.Content
    ) -> types.Content | None:
        text = "\n".join(p.text for p in (user_message.parts or []) if p.text)
        if not text:
            return None
        invocation_id = invocation_context.invocation_id
        layer = None
        with get_tracer().start_as_current_span("bacen.guardrails.screen_prompt") as span:
            if detect_prompt_injection(text):
                layer = "local_rules"
            elif await asyncio.to_thread(_model_armor_blocks, text, is_prompt=True):
                layer = "model_armor"
            span.set_attribute("bacen.guardrails.blocked", bool(layer))
        if layer:
            self._blocked_invocations.add(invocation_id)
            if len(self._blocked_invocations) > 10_000:
                self._blocked_invocations.clear()
        return None

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        if callback_context.invocation_id in self._blocked_invocations:
            return _blocked_response()
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        if not llm_response.content or not llm_response.content.parts:
            return None
        text = "\n".join(p.text for p in llm_response.content.parts if p.text and not p.thought)
        if not text:
            return None
        layer = None
        with get_tracer().start_as_current_span("bacen.guardrails.screen_response"):
            if detect_unsafe_output(text):
                layer = "local_rules"
            elif await asyncio.to_thread(_model_armor_blocks, text, is_prompt=False):
                layer = "model_armor"
        if layer:
            return _blocked_response()
        return None
