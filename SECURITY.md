# Security Policy — BACEN Financial & Pix Advisor

## Security Design Matrix

| Area | Control |
|---|---|
| **Identity & Least Privilege** | Dedicated runtime SA (`bacen-advisor-sa`) on Agent Runtime, separate CI/CD deployer SA (`bacen-advisor-deployer`), and telemetry-only Cloud Run SA (`mcp-bacen-sa`). No service-account keys in repository. |
| **Secrets Management** | BACEN MCP endpoint resolved from Google Secret Manager (`bacen-mcp-url`). Local overrides (`BACEN_MCP_URL`, `MCP_ID_TOKEN`) are ignored when `K_SERVICE` or `GOOGLE_CLOUD_AGENT_ENGINE_ID` is set. |
| **Service-to-Service Auth** | Private Cloud Run MCP service (`--no-allow-unauthenticated`) authenticated with cached Google-signed OIDC ID tokens scoped to the service URL audience. |
| **Prompt & Output Guardrails** | `GuardrailsPlugin` screens every user prompt and model response using deterministic injection/leak rules plus **Google Cloud Model Armor** (`SanitizeUserPrompt` / `SanitizeModelResponse`). |
| **Tool Input/Output Safety** | `ToolGuardPlugin` enforces strict Pydantic validation (`extra="forbid"`) before network calls and attaches safe `recovery_hint` instructions on empty or failed responses so the LLM never fabricates figures. |
| **Human-in-the-Loop (HITL)** | `export_report_to_gcs` is wrapped with `require_confirmation=True` and attached exclusively to `bacen_coordinator`. |
| **PII & Banking Privacy (LGPD)** | `pii.py` scrubs Brazilian CPF, CNPJ, credit card numbers, phone numbers, and emails via local regex + Cloud Sensitive Data Protection (DLP) before structured logging and before long-term Memory Bank storage. |
| **Telemetry Privacy** | Prompts, model answers, and raw tool payloads are excluded from OpenTelemetry spans (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT`). |
