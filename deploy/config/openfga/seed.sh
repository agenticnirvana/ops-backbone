#!/bin/sh
set -eu
BASE="${OPENFGA_URL:-http://openfga:8080}"
echo "Seeding OpenFGA at $BASE"
i=0
while [ "$i" -lt 20 ]; do
  if curl -sf "$BASE/stores" >/dev/null; then
    break
  fi
  i=$((i + 1))
  sleep 2
done
STORE_JSON="$(curl -sf -X POST "$BASE/stores" -H 'Content-Type: application/json' -d '{"name":"agentops"}' || true)"
STORE_ID="$(printf '%s' "$STORE_JSON" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')"
if [ -z "$STORE_ID" ]; then
  STORE_ID="$(curl -sf "$BASE/stores" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -n 1)"
fi
echo "Store: $STORE_ID"
curl -sf -X POST "$BASE/stores/${STORE_ID}/authorization-models" -H 'Content-Type: application/json' -d '{
  "schema_version": "1.1",
  "type_definitions": [
    {"type": "user", "relations": {}},
    {
      "type": "action",
      "relations": {"execute": {"this": {}}},
      "metadata": {"relations": {"execute": {"directly_related_user_types": [{"type": "user"}]}}}
    }
  ]
}' >/dev/null
curl -sf -X POST "$BASE/stores/${STORE_ID}/write" -H 'Content-Type: application/json' -d '{
  "writes": {
    "tuple_keys": [
      {"user":"user:ops-agent","relation":"execute","object":"action:remediate"}
    ]
  }
}' >/dev/null || true
echo "OpenFGA seed complete."
