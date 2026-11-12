#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Deploys the Custom BACEN MCP Server (mcp-bacen) to Google Cloud Run
# ==============================================================================

GCLOUD="${GCLOUD:-gcloud}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${PROJECT_ID:-$(${GCLOUD} config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-mcp-bacen}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-mcp-bacen-sa}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Error: set PROJECT_ID (e.g. export PROJECT_ID=my-gcp-project)"
  exit 1
fi

RUNTIME_SA="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> 1. Resolving PROJECT_NUMBER for ${PROJECT_ID}..."
PROJECT_NUMBER="$(${GCLOUD} projects describe "${PROJECT_ID}" --format="value(projectNumber)")"

echo "==> 2. Ensuring the runtime service account ${RUNTIME_SA} (telemetry only)..."
if ! ${GCLOUD} iam service-accounts describe "${RUNTIME_SA}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  ${GCLOUD} iam service-accounts create "${RUNTIME_SA_NAME}" \
    --project "${PROJECT_ID}" \
    --display-name "mcp-bacen runtime (Cloud Run)" \
    --description "Identity of the BACEN MCP server; writes traces, logs and metrics only."
fi

bind_role() {
  local role="$1" attempt
  for attempt in 1 2 3 4 5 6; do
    if ${GCLOUD} projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${RUNTIME_SA}" \
        --role="${role}" \
        --condition=None \
        --quiet >/dev/null 2>&1; then
      return 0
    fi
    sleep $((attempt * 5))
  done
  return 1
}
for role in roles/cloudtrace.agent roles/logging.logWriter roles/monitoring.metricWriter; do
  bind_role "${role}"
done

echo "==> 3. Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
${GCLOUD} run deploy "${SERVICE_NAME}" \
  --source "${SCRIPT_DIR}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --platform managed \
  --service-account "${RUNTIME_SA}" \
  --no-allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60s \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "ENVIRONMENT=production,LOG_LEVEL=INFO,CACHE_TTL_SECONDS=3600,HTTP_TIMEOUT_SECONDS=12.0,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},ENABLE_CLOUD_TRACE=true,ENABLE_LIVE_HTTP_FETCH=true"

SERVICE_URL="$(${GCLOUD} run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="value(status.url)")"

DISCOVERY_SA="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
${GCLOUD} projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${DISCOVERY_SA}" \
  --role="roles/run.invoker" \
  --condition=None \
  --quiet >/dev/null

echo "DEPLOY COMPLETE: ${SERVICE_URL}/mcp"
