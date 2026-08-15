#!/usr/bin/env bash
# Design 2 — Weaviate + Elasticsearch + VictoriaMetrics + Phoenix
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CMD="${1:-help}"
PHASE="${2:-}"

COMPOSE=(docker compose --env-file "${ENV_FILE:-.env}")

ensure_env() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example"
  fi
}

PHASE1=(postgres runbook-ingestion elasticsearch kibana filebeat victoriametrics grafana metrics-exporter weaviate minio)
PHASE2=(ollama agent mcp-server mcp-policy-server mcp-rag-server agentregistry-db agentregistry agentregistry-seed gateway)
PHASE3=(mlflow otel-collector phoenix)
PHASE4=(openfga openfga-seed presidio)
PHASE5=(ticket-api alert-receiver governance)

ALL=("${PHASE1[@]}" "${PHASE2[@]}" "${PHASE3[@]}" "${PHASE4[@]}" "${PHASE5[@]}")

services_for_phase() {
  case "$1" in
    phase1|1) printf '%s\n' "${PHASE1[@]}" ;;
    phase2|2) printf '%s\n' "${PHASE2[@]}" ;;
    phase3|3) printf '%s\n' "${PHASE3[@]}" ;;
    phase4|4) printf '%s\n' "${PHASE4[@]}" ;;
    phase5|5) printf '%s\n' "${PHASE5[@]}" ;;
    *) return 1 ;;
  esac
}

usage() {
  cat <<'EOF'
Design 2 deploy — Weaviate + Elasticsearch + VictoriaMetrics + Phoenix

  ./deploy.sh up              Start full Design 2 stack (no rebuild — fast)
  ./deploy.sh up --build      Rebuild images then start (slow; after code changes)
  ./deploy.sh up-d3           Start Design 3 tool UIs (OpenSearch, Mimir, Tempo, Langfuse)
  ./deploy.sh up phase1       Start only Phase 1 ingestion services
  ./deploy.sh up phase2       Start Phase 1 deps + Phase 2 orchestration
  ./deploy.sh down            Stop stack (keep volumes)
  ./deploy.sh down -v         Stop and remove volumes
  ./deploy.sh verify          Health-check all phases
  ./deploy.sh demo            Capstone: checkout-redis-pool alert
  ./deploy.sh reindex [mode] Trigger on-demand runbook ingestion (incremental|full)
  ./deploy.sh logs [service]  Tail compose logs
  ./deploy.sh ps              Show service status
  ./deploy.sh help            This message

URLs after `up`:
  Grafana        http://localhost:3001  (admin / admin)
  Kibana         http://localhost:5601
  Phoenix        http://localhost:6006
  Weaviate       http://localhost:8088/v1/schema
  Elasticsearch  http://localhost:9200
  VictoriaMetrics http://localhost:8428/vmui
  MinIO          http://localhost:9001  (agentops / agentopsminio)
  OpenFGA        http://localhost:8085
  Presidio       http://localhost:8084
  MLflow         http://localhost:5001
  Platform UI    http://localhost:8080

Design 3 (`./deploy.sh up-d3`) — native UIs alongside D2:
  OpenSearch Dashboards  http://localhost:5602
  OpenSearch API         http://localhost:9201
  Mimir                  http://localhost:9009
  Tempo                  http://localhost:3200
  Langfuse               http://localhost:3000  (a@ex.com / 123456789) · v3 Tracing / Playground / Prompts / Datasets / Evaluation
  OPA                    http://localhost:8181
  AgentRegistry  http://localhost:12121
  Agent API      http://localhost:8002
  MCP Ops        http://localhost:8081
  Alert webhook  http://localhost:8090
  Ticket API     http://localhost:8091
  Governance     http://localhost:8093
  Runbook ingest http://localhost:8092
EOF
}

pull_ollama_model() {
  if [[ "${MOCK_LLM:-false}" == "true" ]]; then
    return 0
  fi
  local model="${LLM_MODEL:-llama3.2}"
  if docker compose exec -T ollama ollama list 2>/dev/null | grep -q "^${model}"; then
    echo "Ollama model ${model} already present — skipping pull"
    return 0
  fi
  echo "Pulling Ollama model: ${model}"
  docker compose exec -T ollama ollama pull "${model}" || true
}

check_url() {
  local name="$1"
  local url="$2"
  if curl -sf "$url" >/dev/null; then
    echo "  OK  $name"
    return 0
  fi
  echo "  FAIL $name ($url)"
  return 1
}

check_url_basic_auth() {
  local name="$1"
  local url="$2"
  local user="$3"
  local pass="$4"
  if curl -sf -u "${user}:${pass}" "$url" >/dev/null; then
    echo "  OK  $name"
    return 0
  fi
  echo "  FAIL $name ($url)"
  return 1
}

verify_stack() {
  local failed=0
  set -a
  # shellcheck disable=SC1091
  source .env 2>/dev/null || true
  set +a
  local mcp_user="${MCP_BASIC_USER:-mcp}"
  local mcp_pass="${MCP_BASIC_PASSWORD:-mcp-secret}"
  echo "=== Phase 1 — Ingestion ==="
  check_url "Elasticsearch" "http://localhost:9200" || failed=1
  check_url "VictoriaMetrics" "http://localhost:8428/health" || failed=1
  check_url "Grafana" "http://localhost:3001/api/health" || failed=1
  check_url "Weaviate" "http://localhost:8088/v1/.well-known/ready" || failed=1
  check_url "Runbook ingestion" "http://localhost:8092/health" || failed=1
  if curl -sf "http://localhost:9201/_cluster/health" >/dev/null; then
    echo "=== Design 3 tool UIs ==="
    check_url "OpenSearch" "http://localhost:9201/_cluster/health" || true
    check_url "OpenSearch Dashboards" "http://localhost:5602/api/status" || true
    check_url "Mimir" "http://localhost:9009/ready" || true
    check_url "Tempo" "http://localhost:3200/ready" || true
    check_url "Langfuse" "http://localhost:3000/api/public/health" || true
  fi

  echo "=== Phase 2 — Orchestration ==="
  check_url "Agent" "http://localhost:8002/health" || failed=1
  check_url "Gateway" "http://localhost:8080/api/health" || failed=1
  check_url_basic_auth "MCP server (ops)" "http://localhost:8081/health" "$mcp_user" "$mcp_pass" || failed=1
  check_url_basic_auth "MCP server (policy)" "http://localhost:8082/health" "$mcp_user" "$mcp_pass" || failed=1
  check_url_basic_auth "MCP server (rag)" "http://localhost:8083/health" "$mcp_user" "$mcp_pass" || failed=1
  check_url "AgentRegistry" "http://localhost:12121/v0/ping" || failed=1

  echo "=== Phase 3 — Evaluation ==="
  check_url "MLflow" "http://localhost:5001" || failed=1
  check_url "Phoenix" "http://localhost:6006" || failed=1

  echo "=== Phase 4 — Guardrails ==="
  check_url "OpenFGA" "http://localhost:8085/healthz" || failed=1

  echo "=== Phase 5 — Action ==="
  check_url "Ticket API" "http://localhost:8091/health" || failed=1
  check_url "Governance" "http://localhost:8093/health" || failed=1
  check_url "Alert receiver" "http://localhost:8090/health" || failed=1

  if [[ "$failed" -eq 0 ]]; then
    echo "All health checks passed."
  else
    echo "Some checks failed."
    exit 1
  fi
}

run_demo() {
  echo "=== Capstone demo: checkout-redis-pool ==="
  RESP="$(curl -sf -X POST "http://localhost:8090/webhook/alert/checkout-redis-pool.json")"
  echo "$RESP" | python3 -m json.tool
  THREAD="$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['agent_response']['thread_id'])")"
  echo "Thread: $THREAD"
  if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['agent_response']; exit(0 if d.get('requires_hitl') else 1)"; then
    echo "Approving HITL..."
    curl -sf -X POST "http://localhost:8002/approve" \
      -H "Content-Type: application/json" \
      -d "{\"thread_id\":\"${THREAD}\",\"approved\":true}" | python3 -m json.tool
  fi
  echo "Tickets:"
  curl -sf "http://localhost:8091/tickets" | python3 -m json.tool
}

case "$CMD" in
  up)
    ensure_env
    set -a && source .env && set +a
    DO_BUILD=0
    PHASE_ARG="$PHASE"
    if [[ "${PHASE:-}" == "--build" ]]; then
      DO_BUILD=1
      PHASE_ARG=""
    elif [[ "${2:-}" == "--build" || "${3:-}" == "--build" ]]; then
      DO_BUILD=1
    fi
    compose_up() {
      if [[ "$DO_BUILD" -eq 1 ]]; then
        "${COMPOSE[@]}" up -d --build "$@"
      else
        "${COMPOSE[@]}" up -d "$@"
      fi
    }
    if [[ -n "$PHASE_ARG" ]]; then
      mapfile -t TARGET < <(services_for_phase "$PHASE_ARG" || true)
      if [[ ${#TARGET[@]} -eq 0 ]]; then
        echo "Unknown phase: $PHASE_ARG"
        exit 1
      fi
      # Always include postgres for phases that need persistence
      DEPS=(postgres)
      case "$PHASE_ARG" in
        phase2|2) DEPS+=(postgres ticket-api mlflow opa runbook-ingestion "${PHASE1[@]}") ;;
        phase3|3) DEPS+=(postgres) ;;
        phase4|4) DEPS+=(postgres) ;;
        phase5|5) DEPS+=(postgres ticket-api agent mlflow opa "${PHASE1[@]}") ;;
      esac
      compose_up "${DEPS[@]}" "${TARGET[@]}"
    else
      compose_up "${ALL[@]}"
      pull_ollama_model
    fi
    echo "Stack starting. Run ./deploy.sh verify when ready."
    ;;
  up-d3)
    ensure_env
    set -a && source .env && set +a
    echo "Starting Design 3 tool UIs (OpenSearch, Dashboards, Mimir, Tempo, Langfuse)…"
    "${COMPOSE[@]}" --profile design-1 --profile design-3 up -d \
      opensearch opensearch-dashboards mimir tempo fluent-bit opensearch-seed \
      langfuse-postgres-init langfuse-minio-init langfuse-clickhouse langfuse-redis langfuse-worker langfuse \
      prometheus alertmanager opa
    echo "D3 UIs:"
    echo "  OpenSearch Dashboards  http://localhost:5602"
    echo "  OpenSearch API         http://localhost:9201"
    echo "  Mimir                  http://localhost:9009"
    echo "  Tempo                  http://localhost:3200"
    echo "  Langfuse               http://localhost:3000"
    echo "  Grafana (shared)       http://localhost:3001"
    echo "Agent RAG still uses Design 2 Weaviate. Switch the header to D3 to explore these UIs."
    ;;
  down)
    if [[ "${PHASE:-}" == "-v" ]]; then
      "${COMPOSE[@]}" down -v
    else
      "${COMPOSE[@]}" down
    fi
    ;;
  verify)
    verify_stack
    ;;
  demo)
    run_demo
    ;;
  eval)
    ensure_env
    (cd ../agent && MOCK_LLM=true python -m evals.run_evals)
    ;;
  reindex)
    ensure_env
    set -a && source .env && set +a
    MODE="${PHASE:-incremental}"
    TOKEN="${INGESTION_API_TOKEN:-design1-ingestion-token-change-me}"
    curl -sf -X POST "http://localhost:8092/v1/ingest/reindex" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"mode\":\"${MODE}\",\"sync_drive\":true}" | python3 -m json.tool
    ;;
  logs)
    if [[ -n "$PHASE" ]]; then
      "${COMPOSE[@]}" logs -f "$PHASE"
    else
      "${COMPOSE[@]}" logs -f
    fi
    ;;
  ps)
    "${COMPOSE[@]}" ps
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "Unknown command: $CMD"
    usage
    exit 1
    ;;
esac
