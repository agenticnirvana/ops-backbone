"""Weaviate HTTP client for Design 2 runbook vectors (own embeddings, vectorizer none)."""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

CLASS_NAME = "Runbook"
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def vector_backend() -> str:
    return (os.getenv("VECTOR_BACKEND") or "chroma").strip().lower()


def weaviate_url() -> str:
    return os.getenv("WEAVIATE_URL", "http://weaviate:8080").rstrip("/")


def _chunk_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, chunk_id))


def _client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


def ensure_schema() -> None:
    url = weaviate_url()
    schema = {
        "class": CLASS_NAME,
        "description": "SRE runbook chunks",
        "vectorizer": "none",
        "vectorIndexType": "hnsw",
        "vectorIndexConfig": {"distance": "cosine"},
        "properties": [
            {"name": "chunk_id", "dataType": ["text"]},
            {"name": "text", "dataType": ["text"]},
            {"name": "runbook_id", "dataType": ["text"]},
            {"name": "service", "dataType": ["text"]},
            {"name": "severity", "dataType": ["text"]},
            {"name": "domain", "dataType": ["text"]},
            {"name": "source", "dataType": ["text"]},
            {"name": "chunk_index", "dataType": ["int"]},
            {"name": "collection", "dataType": ["text"]},
        ],
    }
    with _client() as client:
        existing = client.get(f"{url}/v1/schema/{CLASS_NAME}")
        if existing.status_code == 200:
            return
        r = client.post(f"{url}/v1/schema", json=schema)
        r.raise_for_status()


def delete_collection_objects(collection: str | None = None) -> None:
    url = weaviate_url()
    where = {"operator": "NotEqual", "path": ["chunk_id"], "valueText": "__none__"}
    if collection:
        where = {"operator": "Equal", "path": ["collection"], "valueText": collection}
    with _client() as client:
        client.delete(
            f"{url}/v1/objects",
            params={"class": CLASS_NAME, "where": _where_param(where)},
        )


def delete_by_runbook(runbook_id: str, *, collection: str | None = None) -> None:
    url = weaviate_url()
    clause = {"operator": "Equal", "path": ["runbook_id"], "valueText": runbook_id}
    if collection:
        clause = {
            "operator": "And",
            "operands": [
                clause,
                {"operator": "Equal", "path": ["collection"], "valueText": collection},
            ],
        }
    with _client() as client:
        client.delete(
            f"{url}/v1/objects",
            params={"class": CLASS_NAME, "where": _where_param(clause)},
        )


def _where_param(where: dict) -> str:
    import json

    return json.dumps(where)


def upsert_chunks(
    *,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
    embeddings: list[list[float]],
    collection: str,
) -> int:
    if not ids:
        return 0
    ensure_schema()
    objects = []
    for chunk_id, doc, meta, emb in zip(ids, documents, metadatas, embeddings):
        objects.append(
            {
                "class": CLASS_NAME,
                "id": _chunk_uuid(chunk_id),
                "properties": {
                    "chunk_id": chunk_id,
                    "text": doc,
                    "runbook_id": str(meta.get("runbook_id") or ""),
                    "service": str(meta.get("service") or ""),
                    "severity": str(meta.get("severity") or ""),
                    "domain": str(meta.get("domain") or ""),
                    "source": str(meta.get("source") or ""),
                    "chunk_index": int(meta.get("chunk_index") or 0),
                    "collection": collection,
                },
                "vector": [float(x) for x in emb],
            }
        )
    with _client() as client:
        r = client.post(f"{weaviate_url()}/v1/batch/objects", json={"objects": objects})
        r.raise_for_status()
    return len(objects)


def count_objects(collection: str | None = None) -> int:
    args = _gql_args(collection=collection)
    gql = f"""
    {{
      Aggregate {{
        {CLASS_NAME}{args} {{
          meta {{ count }}
        }}
      }}
    }}
    """
    data = _graphql(gql)
    rows = (((data.get("data") or {}).get("Aggregate") or {}).get(CLASS_NAME)) or []
    if not rows:
        return 0
    return int(((rows[0] or {}).get("meta") or {}).get("count") or 0)


def _gql_where_obj(collection: str | None, extra: dict[str, str] | None = None) -> str:
    operands = []
    if collection:
        operands.append(f'{{ path: ["collection"], operator: Equal, valueText: "{_esc(collection)}" }}')
    for path, value in (extra or {}).items():
        if value:
            operands.append(f'{{ path: ["{path}"], operator: Equal, valueText: "{_esc(value)}" }}')
    if not operands:
        return ""
    if len(operands) == 1:
        return operands[0]
    joined = ", ".join(operands)
    return f'{{ operator: And, operands: [{joined}] }}'


def _gql_args(*, collection: str | None = None, extra: dict[str, str] | None = None, limit: int | None = None, near_vector: str | None = None) -> str:
    parts: list[str] = []
    where_obj = _gql_where_obj(collection, extra)
    if where_obj:
        parts.append(f"where: {where_obj}")
    if near_vector:
        parts.append(f"nearVector: {{ vector: [{near_vector}] }}")
    if limit is not None:
        parts.append(f"limit: {limit}")
    if not parts:
        return ""
    return "(" + ", ".join(parts) + ")"


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _graphql(query: str) -> dict[str, Any]:
    with _client() as client:
        r = client.post(f"{weaviate_url()}/v1/graphql", json={"query": query})
        r.raise_for_status()
        return r.json()


def list_objects(*, collection: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    args = _gql_args(collection=collection, limit=min(max(limit, 1), 2000))
    gql = f"""
    {{
      Get {{
        {CLASS_NAME}{args} {{
          chunk_id
          text
          runbook_id
          service
          severity
          domain
          source
          chunk_index
          collection
          _additional {{ id vector }}
        }}
      }}
    }}
    """
    data = _graphql(gql)
    rows = (((data.get("data") or {}).get("Get") or {}).get(CLASS_NAME)) or []
    out = []
    for row in rows:
        extra = row.get("_additional") or {}
        meta = {
            "runbook_id": row.get("runbook_id"),
            "service": row.get("service"),
            "severity": row.get("severity"),
            "domain": row.get("domain"),
            "source": row.get("source"),
            "chunk_index": row.get("chunk_index") or 0,
            "collection": row.get("collection"),
        }
        out.append(
            {
                "id": row.get("chunk_id") or extra.get("id"),
                "document": row.get("text") or "",
                "metadata": meta,
                "embedding": extra.get("vector"),
            }
        )
    return out


def get_object(chunk_id: str, *, collection: str | None = None) -> dict[str, Any] | None:
    oid = _chunk_uuid(chunk_id)
    with _client() as client:
        r = client.get(
            f"{weaviate_url()}/v1/objects/{oid}",
            params={"include": "vector"},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        obj = r.json()
    props = obj.get("properties") or {}
    if collection and props.get("collection") not in (None, collection):
        return None
    return {
        "id": props.get("chunk_id") or chunk_id,
        "document": props.get("text") or "",
        "metadata": {
            "runbook_id": props.get("runbook_id"),
            "service": props.get("service"),
            "severity": props.get("severity"),
            "domain": props.get("domain"),
            "source": props.get("source"),
            "chunk_index": props.get("chunk_index") or 0,
            "collection": props.get("collection"),
        },
        "embedding": obj.get("vector"),
    }


def query_near_vector(
    embedding: list[float],
    *,
    collection: str | None = None,
    n_results: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    vec = ",".join(str(float(x)) for x in embedding)
    args = _gql_args(
        collection=collection,
        extra=filters,
        limit=min(max(n_results, 1), 20),
        near_vector=vec,
    )
    gql = f"""
    {{
      Get {{
        {CLASS_NAME}{args} {{
          chunk_id
          text
          runbook_id
          service
          severity
          domain
          source
          chunk_index
          collection
          _additional {{ id distance certainty }}
        }}
      }}
    }}
    """
    data = _graphql(gql)
    rows = (((data.get("data") or {}).get("Get") or {}).get(CLASS_NAME)) or []
    out = []
    for row in rows:
        extra = row.get("_additional") or {}
        dist = extra.get("distance")
        meta = {
            "runbook_id": row.get("runbook_id"),
            "service": row.get("service"),
            "severity": row.get("severity"),
            "domain": row.get("domain"),
            "source": row.get("source"),
            "chunk_index": row.get("chunk_index") or 0,
            "collection": row.get("collection"),
        }
        out.append(
            {
                "id": row.get("chunk_id") or extra.get("id"),
                "document": row.get("text") or "",
                "metadata": meta,
                "distance": dist,
            }
        )
    return out
