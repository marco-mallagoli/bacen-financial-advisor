"""Tool guard plugin for the BACEN Financial & Pix Advisor."""

from __future__ import annotations

from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from ..observability.logging import get_logger
from ..schemas import MCP_ARG_SCHEMAS, McpToolOutput

logger = get_logger(__name__)


def _validation_hint(tool_name: str, exc: ValidationError) -> dict[str, Any]:
    problems = [
        f"{'.'.join(str(p) for p in err['loc']) or 'args'}: {err['msg']}" for err in exc.errors()
    ]
    return {
        "status": "error",
        "error_type": "invalid_arguments",
        "tool": tool_name,
        "error_message": "; ".join(problems),
        "recovery_hint": (
            "Fix the arguments and call the tool again. If unsure about valid values, "
            "call list_supported_bacen_filters first. Never invent numbers."
        ),
    }


def _recovery_for_exception(error: Exception) -> str:
    text = f"{type(error).__name__}: {error}".lower()
    if "401" in text or "403" in text:
        return "The BACEN MCP service rejected the credentials. Do not retry."
    if "timeout" in text or "timed out" in text:
        return "The BACEN MCP service timed out. Retry once with a narrower filter."
    return "Unexpected BACEN tool failure. Explain the limitation without inventing data."


class ToolGuardPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="tool_guard")

    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ):
        schema = MCP_ARG_SCHEMAS.get(tool.name)
        if schema is None:
            return None
        try:
            validated = schema.model_validate(tool_args)
        except ValidationError as exc:
            logger.warning("bacen_tool_args_rejected", extra={"tool": tool.name, "rejected_args": tool_args})
            return _validation_hint(tool.name, exc)
        tool_args.clear()
        tool_args.update(validated.model_dump(exclude_none=True))
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict[str, Any],
    ):
        if tool.name not in MCP_ARG_SCHEMAS or not isinstance(result, dict):
            return None
        try:
            parsed = McpToolOutput.model_validate(result)
        except ValidationError:
            return {
                **result,
                "isError": True,
                "recovery_hint": "Malformed BACEN MCP payload. Do not invent figures.",
            }
        if parsed.isError:
            return {
                **result,
                "recovery_hint": "Adjust arguments (segmento, modalidade, instituicao, trimestre) and retry once.",
            }
        if parsed.structuredContent and parsed.structuredContent.registros == []:
            return {
                **result,
                "recovery_hint": (
                    "No records matched these filters. Broaden the query: use segmento='TODOS' "
                    "or drop trimestre/motivo. Never fabricate figures."
                ),
            }
        return None

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ):
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "tool": tool.name,
            "error_message": str(error)[:500],
            "recovery_hint": _recovery_for_exception(error),
        }
