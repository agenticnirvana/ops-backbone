"""Runbook RAG retrieval tool."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from rag.embeddings import embed_text
from rag.indexer import chroma_path, read_active_collection

INDEX_DIR = chroma_path()

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

    def _score_candidates(filter_service: bool, boost_runbook: str | None = None) -> list[tuple[float, str, dict]]:
        if os.getenv("VECTOR_BACKEND", "chroma").lower() != "weaviate":
            fallback = INDEX_DIR / "fallback_index.json"
            if fallback.exists():
                store = json.loads(fallback.read_text(encoding="utf-8"))
                q_vec = embed_text(query)
                scored: list[tuple[float, str, dict]] = []
                for doc, meta, emb in zip(store["documents"], store["metadatas"], store["embeddings"]):
                    if domain and meta.get("domain") != domain:
                        continue
                    if filter_service and service and meta.get("service") != service:
                        continue
                    kw = _keyword_score(query, doc, meta)
                    sim = _cosine(q_vec, emb)
                    combined = kw * 10 + sim
                    if boost_runbook and meta.get("runbook_id") == boost_runbook:
                        combined += 100.0
                    scored.append((combined, doc, meta))
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
                    combined = (1 - dist) + _keyword_score(query, doc, meta) * 0.1
                    if boost_runbook and meta.get("runbook_id") == boost_runbook:
                        combined += 10.0
                    scored.append((combined, doc, meta))
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
                combined = (1 - dist) + _keyword_score(query, doc, meta) * 0.1
                if boost_runbook and meta.get("runbook_id") == boost_runbook:
                    combined += 10.0
                scored.append((combined, doc, meta))
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
        }
        for s, doc, meta in scored[:top_k]
    ]


def format_runbook_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No runbook matches found."
    parts = []
    for c in chunks:
        parts.append(f"[{c['runbook_id']}] ({c['source']}): {c['content']}")
    return "\n\n".join(parts)
