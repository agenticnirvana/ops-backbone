"""Read-only views and Chroma query features for the runbook vector index."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config import CHROMA_PATH, GOOGLE_DRIVE_ENABLED, GOOGLE_DRIVE_FOLDER_ID, GOOGLE_SERVICE_ACCOUNT_FILE
from rag.embeddings import embed_text
from rag.indexer import active_manifest_path, chroma_path, read_active_collection
from rag.weaviate_store import vector_backend, weaviate_url


def drive_status() -> dict:
    sa_path = Path(GOOGLE_SERVICE_ACCOUNT_FILE)
    return {
        "enabled": GOOGLE_DRIVE_ENABLED,
        "folder_id": GOOGLE_DRIVE_FOLDER_ID or None,
        "service_account_present": sa_path.is_file(),
        "ready": bool(
            GOOGLE_DRIVE_ENABLED
            and GOOGLE_DRIVE_FOLDER_ID
            and sa_path.is_file()
        ),
    }


def _store_path() -> str:
    if vector_backend() == "weaviate":
        return weaviate_url()
    return str(CHROMA_PATH)


def _chroma_collection(collection_name: str | None = None):
    from rag.indexer import _chroma_client

    name = collection_name or read_active_collection()
    client = _chroma_client(chroma_path())
    return client, client.get_collection(name), name


def _read_manifest() -> dict[str, Any]:
    path = active_manifest_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _clean_meta_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if cleaned.startswith("**"):
        cleaned = cleaned[2:].strip()
    return cleaned


def _clean_metadata(meta: dict | None) -> dict:
    if not meta:
        return {}
    return {key: _clean_meta_value(val) for key, val in meta.items()}


def _embedding_preview(emb, *, dims: int = 32) -> list[float] | None:
    if emb is None:
        return None
    vec = list(emb)
    if not vec:
        return None
    return [round(float(v), 4) for v in vec[:dims]]


def _chunk_record(doc_id: str, doc: str, meta: dict, emb, embedding_dims: int | None) -> dict:
    meta = _clean_metadata(meta)
    full_doc = doc or ""
    return {
        "id": doc_id,
        "chunk_index": meta.get("chunk_index", 0),
        "preview": full_doc[:280],
        "document": full_doc,
        "char_count": len(full_doc),
        "token_estimate": max(1, len(full_doc.split())),
        "service": meta.get("service"),
        "severity": meta.get("severity"),
        "domain": meta.get("domain"),
        "source": meta.get("source"),
        "runbook_id": meta.get("runbook_id"),
        "metadata": meta,
        "embedding_dims": len(emb) if emb is not None else embedding_dims,
        "embedding_preview": _embedding_preview(emb),
    }


def list_collections() -> dict:
    try:
        if vector_backend() == "weaviate":
            from rag.weaviate_store import count_objects

            active = read_active_collection()
            manifest = _read_manifest()
            return {
                "active_collection": active,
                "index_version": manifest.get("index_version"),
                "activated_at": manifest.get("activated_at"),
                "backend": "weaviate",
                "collections": [
                    {"name": active, "count": count_objects(active), "is_active": True}
                ],
            }

        from rag.indexer import _chroma_client

        client = _chroma_client(chroma_path())
        active = read_active_collection()
        manifest = _read_manifest()
        items = []
        for col in client.list_collections():
            name = col.name if hasattr(col, "name") else col.get("name", str(col))
            try:
                count = client.get_collection(name).count()
            except Exception:
                count = 0
            items.append(
                {
                    "name": name,
                    "count": count,
                    "is_active": name == active,
                }
            )
        items.sort(key=lambda c: (not c["is_active"], c["name"]))
        return {
            "active_collection": active,
            "index_version": manifest.get("index_version"),
            "activated_at": manifest.get("activated_at"),
            "collections": items,
        }
    except Exception as exc:
        return {"active_collection": read_active_collection(), "collections": [], "error": str(exc)}


def list_index_chunks(*, limit: int = 500, collection: str | None = None) -> dict:
    manifest = _read_manifest()
    collection_name = collection or read_active_collection()
    try:
        if vector_backend() == "weaviate":
            from rag.weaviate_store import count_objects, list_objects

            rows = list_objects(collection=collection_name, limit=limit)
            ids = [r["id"] for r in rows]
            documents = [r["document"] for r in rows]
            metadatas = [r["metadata"] for r in rows]
            emb_list = [r.get("embedding") for r in rows]
            total_count = count_objects(collection_name)
            embedding_dims = next((len(e) for e in emb_list if e), None)
        else:
            _, collection_obj, collection_name = _chroma_collection(collection)
            total_count = collection_obj.count()
            data = collection_obj.get(
                include=["documents", "metadatas", "embeddings"],
                limit=min(max(limit, 1), 2000),
            )
            ids = data.get("ids") or []
            documents = data.get("documents") or []
            metadatas = data.get("metadatas") or []
            embeddings = data.get("embeddings")
            if embeddings is None or len(embeddings) == 0:
                emb_list = [None] * len(ids)
                embedding_dims = None
            else:
                emb_list = list(embeddings)
                embedding_dims = len(emb_list[0])
    except Exception as exc:
        return {
            "collection": collection or read_active_collection(),
            "chroma_path": _store_path(),
            "total_chunks": 0,
            "total_in_collection": 0,
            "runbook_count": 0,
            "embedding_dims": None,
            "index_version": manifest.get("index_version"),
            "runbooks": [],
            "services": [],
            "severities": [],
            "error": str(exc),
        }

    grouped: dict[str, list[dict]] = defaultdict(list)
    services: set[str] = set()
    severities: set[str] = set()

    for doc_id, doc, meta, emb in zip(ids, documents, metadatas, emb_list):
        meta = _clean_metadata(meta)
        runbook_id = meta.get("runbook_id") or "unknown"
        if meta.get("service"):
            services.add(meta["service"])
        if meta.get("severity"):
            severities.add(meta["severity"])
        grouped[runbook_id].append(_chunk_record(doc_id, doc, meta, emb, embedding_dims))

    runbooks = []
    for runbook_id, chunks in sorted(grouped.items()):
        chunks.sort(key=lambda c: c["chunk_index"])
        first = chunks[0]
        runbooks.append(
            {
                "runbook_id": runbook_id,
                "service": first.get("service"),
                "severity": first.get("severity"),
                "domain": first.get("domain"),
                "source": first.get("source"),
                "chunk_count": len(chunks),
                "total_chars": sum(c["char_count"] for c in chunks),
                "chunks": chunks,
            }
        )

    return {
        "collection": collection_name,
        "chroma_path": _store_path(),
        "total_chunks": len(ids),
        "total_in_collection": total_count,
        "runbook_count": len(runbooks),
        "embedding_dims": embedding_dims,
        "index_version": manifest.get("index_version"),
        "activated_at": manifest.get("activated_at"),
        "distance_metric": "cosine",
        "embedding_model": "all-MiniLM-L6-v2",
        "services": sorted(services),
        "severities": sorted(severities),
        "runbooks": runbooks,
    }


def get_chunk_by_id(chunk_id: str, *, collection: str | None = None) -> dict | None:
    try:
        if vector_backend() == "weaviate":
            from rag.weaviate_store import get_object

            collection_name = collection or read_active_collection()
            row = get_object(chunk_id, collection=collection_name)
            if not row:
                return None
            emb = row.get("embedding")
            return {
                "collection": collection_name,
                "chunk": _chunk_record(
                    row["id"],
                    row.get("document") or "",
                    row.get("metadata") or {},
                    emb,
                    len(emb) if emb is not None else None,
                ),
            }
        _, collection_obj, collection_name = _chroma_collection(collection)
        data = collection_obj.get(
            ids=[chunk_id],
            include=["documents", "metadatas", "embeddings"],
        )
        ids = data.get("ids") or []
        if not ids:
            return None
        emb = (data.get("embeddings") or [None])[0]
        return {
            "collection": collection_name,
            "chunk": _chunk_record(
                ids[0],
                (data.get("documents") or [""])[0],
                (data.get("metadatas") or [{}])[0],
                emb,
                len(emb) if emb is not None else None,
            ),
        }
    except Exception as exc:
        return {"error": str(exc)}


def query_index(
    *,
    query_text: str,
    n_results: int = 5,
    collection: str | None = None,
    service: str | None = None,
    severity: str | None = None,
    runbook_id: str | None = None,
) -> dict:
    query_text = (query_text or "").strip()
    if not query_text:
        return {"error": "query_text is required", "results": []}

    where: dict[str, Any] = {}
    if service:
        where["service"] = service
    if severity:
        where["severity"] = severity
    if runbook_id:
        where["runbook_id"] = runbook_id

    try:
        query_embedding = embed_text(query_text)
        if vector_backend() == "weaviate":
            from rag.weaviate_store import query_near_vector

            collection_name = collection or read_active_collection()
            rows = query_near_vector(
                query_embedding,
                collection=collection_name,
                n_results=min(max(n_results, 1), 20),
                filters=where if where else None,
            )
            results = []
            for rank, row in enumerate(rows, start=1):
                meta = _clean_metadata(row.get("metadata") or {})
                dist = row.get("distance")
                similarity = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else None
                doc = row.get("document") or ""
                results.append(
                    {
                        "rank": rank,
                        "id": row.get("id"),
                        "distance": round(float(dist), 6) if dist is not None else None,
                        "similarity": similarity,
                        "document": doc,
                        "preview": doc[:240],
                        "runbook_id": meta.get("runbook_id"),
                        "service": meta.get("service"),
                        "severity": meta.get("severity"),
                        "chunk_index": meta.get("chunk_index"),
                        "metadata": meta,
                    }
                )
            return {
                "collection": collection_name,
                "query": query_text,
                "n_results": len(results),
                "where": where or None,
                "distance_metric": "cosine",
                "embedding_dims": len(query_embedding),
                "query_embedding_preview": _embedding_preview(query_embedding),
                "results": results,
            }

        _, collection_obj, collection_name = _chroma_collection(collection)
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(max(n_results, 1), 20),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        raw = collection_obj.query(**kwargs)
        results = []
        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]

        for rank, (doc_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists), start=1):
            meta = _clean_metadata(meta)
            similarity = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else None
            results.append(
                {
                    "rank": rank,
                    "id": doc_id,
                    "distance": round(float(dist), 6) if dist is not None else None,
                    "similarity": similarity,
                    "document": doc or "",
                    "preview": (doc or "")[:240],
                    "runbook_id": meta.get("runbook_id"),
                    "service": meta.get("service"),
                    "severity": meta.get("severity"),
                    "chunk_index": meta.get("chunk_index"),
                    "metadata": meta,
                }
            )

        return {
            "collection": collection_name,
            "query": query_text,
            "n_results": len(results),
            "where": where or None,
            "distance_metric": "cosine",
            "embedding_dims": len(query_embedding),
            "query_embedding_preview": _embedding_preview(query_embedding),
            "results": results,
        }
    except Exception as exc:
        return {"query": query_text, "results": [], "error": str(exc)}
