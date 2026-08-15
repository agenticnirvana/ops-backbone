"""Runbook RAG retrieval tool."""

from __future__ import annotations

import json
import math
import os

from rag.embeddings import embed_text
from rag.indexer import chroma_path, read_active_collection

INDEX_DIR = chroma_path()

# Cosine similarity below this is "nearest neighbor", not a grounded runbook.
MIN_RUNBOOK_SIMILARITY = float(os.getenv("RUNBOOK_MIN_SIMILARITY", "0.55"))
HIGH_CONFIDENCE_SIMILARITY = float(os.getenv("RUNBOOK_HIGH_SIMILARITY", "0.72"))
GENERIC_QUERY_TOKENS = {
    "error", "errors", "failed", "failure", "http", "https", "test", "alert",
    "service", "timeout", "exception", "spike", "high", "low", "unknown",
}

# Aligns with platform/shared/scenarios.py and seed runbooks
SERVICE_TO_RUNBOOK: dict[str, str] = {
    "checkout-service": "checkout-redis-pool",
    "payment-api": "payment-high-cpu",
    "auth-service": "auth-error-spike",
    "order-service": "db-pool-exhausted",
    "api-gateway": "api-gateway-latency",
    "order-events-consumer": "kafka-consumer-lag",
    "search-service": "search-service-degraded",
    "inventory-service": "inventory-sync-failure",
    "notification-service": "notification-delivery-backlog",
    "catalog-service": "kubernetes-oom-restart",
    "edge-ingress": "tls-certificate-expiry",
    "recommendation-service": "deployment-canary-failure",
}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


def _distinctive_tokens(query: str, service: str | None = None) -> list[str]:
    skip = set(GENERIC_QUERY_TOKENS)
    if service:
        skip.update(t for t in service.lower().replace("_", "-").split("-") if t)
    tokens = []
    for raw in (query or "").lower().replace("/", " ").replace("_", " ").replace("-", " ").split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) < 4 or token in skip or token.isdigit():
            continue
        tokens.append(token)
    return tokens


def _token_overlap(tokens: list[str], doc: str) -> int:
    hay = (doc or "").lower()
    return sum(1 for t in tokens if t in hay)


def chunk_similarity(chunk: dict) -> float:
    if chunk.get("similarity") is not None:
        return float(chunk["similarity"])
    if chunk.get("distance") is not None:
        return max(0.0, 1.0 - float(chunk["distance"]))
    return 0.0


def assess_runbook_match(
    chunks: list[dict],
    *,
    query: str,
    service: str | None = None,
) -> dict:
    """Decide whether top-1 is grounded enough to use — not merely the closest doc."""
    if not chunks:
        return {
            "matched": False,
            "runbook_id": "none",
            "similarity": 0.0,
            "token_overlap": 0,
            "reason": "no_hits",
            "threshold": MIN_RUNBOOK_SIMILARITY,
            "nearest": None,
        }
    top = chunks[0]
    sim = chunk_similarity(top)
    content = top.get("content") or top.get("document") or top.get("preview") or ""
    tokens = _distinctive_tokens(query, service)
    overlap = _token_overlap(tokens, content)
    if len(tokens) <= 1:
        matched = sim >= HIGH_CONFIDENCE_SIMILARITY and overlap >= 1
        reason = "thin_query" if not matched else "grounded"
    else:
        matched = sim >= MIN_RUNBOOK_SIMILARITY and (overlap >= 1 or sim >= HIGH_CONFIDENCE_SIMILARITY)
        reason = "grounded" if matched else "low_similarity"
    nearest = {
        "runbook_id": top.get("runbook_id"),
        "similarity": round(sim, 4),
        "preview": (content[:180] + "…") if len(content) > 180 else content,
    }
    return {
        "matched": matched,
        "runbook_id": top.get("runbook_id") if matched else "none",
        "similarity": round(sim, 4),
        "token_overlap": overlap,
        "reason": reason,
        "threshold": MIN_RUNBOOK_SIMILARITY,
        "nearest": nearest,
    }


def unmatched_recommendation(*, alert: dict, match: dict) -> str:
    nearest = match.get("nearest") or {}
    pct = int(round(float(match.get("similarity") or 0) * 100))
    gate = int(round(MIN_RUNBOOK_SIMILARITY * 100))
    nearest_id = nearest.get("runbook_id") or "none"
    service = alert.get("service") or "the service"
    summary = alert.get("error_summary") or "this error"
    return (
        f"No grounded runbook in the vector index for {service} / “{summary}”. "
        f"Nearest neighbor was `{nearest_id}` at {pct}% similarity (gate is {gate}%) — that runbook was not applied. "
        "Recommended next steps: "
        "1) Pull a precise log signature (not a generic 500). "
        "2) Check error rate, latency, and the last deploy. "
        "3) Open a ticket with the evidence pack. "
        "4) Draft a new runbook from this incident and embed it so the next similar alert is grounded."
    )


def _keyword_score(query: str, doc: str, meta: dict) -> float:
    q = query.lower()
    score = 0.0
    for token in q.split():
        if len(token) < 3:
            continue
        if token in doc.lower():
            score += 1.0
        if token in meta.get("runbook_id", "").lower():
            score += 2.0
        if token in meta.get("service", "").lower():
            score += 1.5
    return score


def retrieve_runbooks(
    query: str,
    service: str | None = None,
    domain: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    """Retrieve top-k runbook chunks for query, optionally filtered by service/domain."""
    from observability.trace_context import trace_tool

    backend = os.getenv("VECTOR_BACKEND", "chroma")
    with trace_tool(
        "🔧 Tool · Weaviate RAG" if backend == "weaviate" else "🔧 Tool · Chroma RAG",
        input={"query": query[:300], "service": service, "domain": domain, "top_k": top_k},
        metadata={"backend": backend, "integration": "runbook_rag"},
    ) as span:
        result = _retrieve_runbooks_impl(query, service, domain, top_k)
        if span:
            span.end(
                output={
                    "count": len(result),
                    "runbooks": [r.get("runbook_id") for r in result],
                    "top_score": result[0].get("score") if result else None,
                }
            )
        return result


def _retrieve_runbooks_impl(
    query: str,
    service: str | None = None,
    domain: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    hint_runbook = SERVICE_TO_RUNBOOK.get(service or "")

    def _score_candidates(filter_service: bool, boost_runbook: str | None = None) -> list[tuple[float, float, str, dict]]:
        if os.getenv("VECTOR_BACKEND", "chroma").lower() != "weaviate":
            fallback = INDEX_DIR / "fallback_index.json"
            if fallback.exists():
                store = json.loads(fallback.read_text(encoding="utf-8"))
                q_vec = embed_text(query)
                scored: list[tuple[float, float, str, dict]] = []
                for doc, meta, emb in zip(store["documents"], store["metadatas"], store["embeddings"]):
                    if domain and meta.get("domain") != domain:
                        continue
                    if filter_service and service and meta.get("service") != service:
                        continue
                    kw = _keyword_score(query, doc, meta)
                    sim = _cosine(q_vec, emb)
                    combined = kw * 10 + sim
                    if boost_runbook and meta.get("runbook_id") == boost_runbook and kw >= 2:
                        combined += 8.0
                    scored.append((combined, sim, doc, meta))
                scored.sort(key=lambda x: x[0], reverse=True)
                return scored

        try:
            if os.getenv("VECTOR_BACKEND", "chroma").lower() == "weaviate":
                from rag.weaviate_store import query_near_vector

                rows = query_near_vector(
                    embed_text(query),
                    collection=read_active_collection(),
                    n_results=top_k * 6,
                    filters={"service": service} if filter_service and service else None,
                )
                scored = []
                for row in rows:
                    doc = row.get("document") or ""
                    meta = row.get("metadata") or {}
                    if domain and meta.get("domain") != domain:
                        continue
                    dist = float(row.get("distance") or 0.0)
                    sim = max(0.0, 1.0 - dist)
                    kw = _keyword_score(query, doc, meta)
                    combined = sim + kw * 0.1
                    if boost_runbook and meta.get("runbook_id") == boost_runbook and kw >= 2:
                        combined += 2.0
                    scored.append((combined, sim, doc, meta))
                scored.sort(key=lambda x: x[0], reverse=True)
                return scored

            import chromadb

            client = chromadb.PersistentClient(path=str(INDEX_DIR))
            collection = client.get_collection(read_active_collection())
            results = collection.query(query_embeddings=[embed_text(query)], n_results=top_k * 6)
            scored = []
            for doc, meta, dist in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0]
            ):
                if domain and meta.get("domain") != domain:
                    continue
                if filter_service and service and meta.get("service") != service:
                    continue
                sim = max(0.0, 1.0 - float(dist))
                kw = _keyword_score(query, doc, meta)
                combined = sim + kw * 0.1
                if boost_runbook and meta.get("runbook_id") == boost_runbook and kw >= 2:
                    combined += 2.0
                scored.append((combined, sim, doc, meta))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored
        except Exception:
            return []

    scored = _score_candidates(filter_service=True)
    if not scored and hint_runbook:
        scored = _score_candidates(filter_service=False, boost_runbook=hint_runbook)
    if not scored:
        scored = _score_candidates(filter_service=False)

    return [
        {
            "content": doc,
            "runbook_id": meta["runbook_id"],
            "source": meta.get("source", meta["runbook_id"]),
            "score": round(s, 4),
            "similarity": round(float(sim), 4),
        }
        for s, sim, doc, meta in scored[:top_k]
    ]


def retrieve_with_gate(
    query: str,
    service: str | None = None,
    domain: str | None = None,
    top_k: int = 3,
) -> dict:
    """Retrieve chunks, then refuse nearest-neighbor hits that fail the confidence gate."""
    chunks = retrieve_runbooks(query, service=service, domain=domain, top_k=top_k)
    match = assess_runbook_match(chunks, query=query, service=service)
    from observability.trace_context import emit_event

    emit_event(
        "📚 Event · RAG match" if match.get("matched") else "📚 Event · RAG gap",
        input={"query": (query or "")[:200], "service": service},
        output={
            "matched": bool(match.get("matched")),
            "runbook_id": match.get("runbook_id") or "none",
            "similarity": match.get("similarity"),
        },
        metadata={"phase": "2-context", "node": "retrieve_runbook"},
        level="DEFAULT" if match.get("matched") else "WARNING",
    )
    if match["matched"]:
        return {
            "chunks": chunks,
            "context": format_runbook_context(chunks),
            "runbook_id": match["runbook_id"],
            "match": match,
            "gap": False,
        }
    nearest = (match.get("nearest") or {}).get("runbook_id") or "none"
    pct = int(round(float(match.get("similarity") or 0) * 100))
    return {
        "chunks": chunks,
        "context": (
            "No grounded runbook. Do not follow a nearest-neighbor document. "
            f"Rejected candidate: {nearest} at {pct}% similarity."
        ),
        "runbook_id": "none",
        "match": match,
        "gap": True,
    }


def format_runbook_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No runbook matches found."
    parts = []
    for c in chunks:
        parts.append(f"[{c['runbook_id']}] ({c['source']}): {c['content']}")
    return "\n\n".join(parts)
