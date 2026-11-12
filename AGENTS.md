# BACEN Financial & Pix Advisor — AI Coding Agent Instructions

This is a standalone Python 3.12+ **Google ADK 2.x + Model Context Protocol (MCP)** multi-agent project adapted for **Banco Central do Brasil (BACEN / BCB)** Open Data (API Olinda OData, SGS, CKAN).

## 1. Environment & Commands

Always execute Python, pytest, ruff, and ADK commands through the local virtual environment `.venv`:

- **Run all offline unit & MCP tests**:
  ```bash
  .venv/bin/python3 -m pytest tests/unit -q
  PYTHONPATH=mcp_bacen .venv/bin/python3 -m pytest mcp_bacen/tests -q
  ```
  *(or `make test`)*
- **Run static lint checks**:
  ```bash
  .venv/bin/python3 -m ruff check bacen_advisor mcp_bacen tests deployment
  ```
  *(or `make lint`)*
- **Start local MCP server (`18081`) + Executive Web UI (`/app` on `18000`) + ADK Dev UI (`/dev-ui` on `18000`)**:
  ```bash
  bash scripts/start_local.sh
  ```
  *(or `make ui`)*

## 2. Project Architecture

- `bacen_advisor/`: Multi-agent ADK 2.x package (`bacen_coordinator` -> `knowledge_agent`, `quick_data_agent`, and 4-stage `report_pipeline`: `data_collector` -> `banking_analyst` [Gemini Pro] -> `quality_critic` [LLM-as-Judge] -> `report_publisher`).
- `bacen_advisor/plugins/`: Defense-in-depth plugins (`ObservabilityPlugin` first, `GuardrailsPlugin`, `ToolGuardPlugin`, `MemoryPlugin`).
- `bacen_advisor/pii.py`: Regex + Google Cloud DLP redaction of CPF, CNPJ, credit cards, phone numbers, and emails before logs and Memory Bank.
- `mcp_bacen/`: Stateless `StreamableHTTP` (`/mcp`) FastAPI + `MCPServer` + **Polars** in-memory engine serving 7 tools across BCB's 4 pillars (Ranking de Reclamações, Pix/SPI/DICT/MED, Taxas de Juros API Olinda, Tarifas & Satisfação Digital), with live OData ingestion + RAM cache + deterministic seed fallback.
- `.ui/`: Executive End-User Web UI (`/app`) that hides intermediate agent drafts and raw `CriticVerdict` JSON behind an audit badge and collapsible drawer.
- `docs/`: Methodology knowledge base (`docs/knowledge/bacen_methodology.txt`).
- `terraform/` & `deployment/`: Infrastructure as Code and idempotent Vertex AI Agent Runtime deployment scripts.

## 3. Guardrails for Future Edits

- Never commit or hardcode API keys or `.env` secrets.
- Keep `ObservabilityPlugin()` as the **first** plugin in `bacen_advisor/agent.py` (ADK stops at the first plugin returning a value).
- Keep `_NO_TRANSFER = {"disallow_transfer_to_parent": True, "disallow_transfer_to_peers": True}` on every specialist sub-agent so only `bacen_coordinator` routes.
- Whenever adding or modifying an MCP tool in `mcp_bacen/src/api/mcp_server.py`, update its Pydantic input schema in `bacen_advisor/schemas.py` (`MCP_ARG_SCHEMAS` and `TOOL_JSON_SCHEMAS`) and run `make test`.
