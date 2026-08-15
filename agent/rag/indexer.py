"""Enterprise runbook indexer — full rebuild, incremental upsert, collection alias swap."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from rag.embeddings import embed_texts
from rag.weaviate_store import (
    delete_by_runbook,
    delete_collection_objects,
    upsert_chunks,
    vector_backend,
)

SRE_DOMAIN = "sre"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 64
DEFAULT_COLLECTION = "runbooks"


@dataclass
class IndexResult:
    index_version: str
    collection: str
    documents_indexed: int
    runbooks_indexed: int
    mode: str
    changed_files: list[str]


def chroma_path() -> Path:
    return Path(os.getenv("CHROMA_PATH", Path(__file__).parent.parent / ".chroma"))


def runbooks_dir() -> Path:
    return Path(os.getenv("RUNBOOKS_DIR", Path(__file__).parent / "runbooks"))


def active_manifest_path() -> Path:
    return Path(os.getenv("INDEX_MANIFEST_PATH", chroma_path() / "active.json"))


def _iter_runbook_paths(source_dir: Path) -> list[Path]:
    paths = sorted(source_dir.glob("*.md"))
    nested = sorted(source_dir.glob("*/*.md"))
    if nested:
        names = ", ".join(p.relative_to(source_dir).as_posix() for p in nested[:5])
        raise RuntimeError(f"Design 1 is SRE-only. Remove nested runbooks: {names}")
    return paths


def _parse_metadata(content: str, filename: str, path: Path, runbooks_root: Path) -> dict:
    service = "unknown"
    severity = "P3"
    domain = SRE_DOMAIN
    for line in content.splitlines():
        if line.startswith("**Service:**"):
            service = line.split(":", 1)[1].strip()
        if line.startswith("**Severity:**"):
            severity = line.split(":", 1)[1].strip()
        if line.startswith("**Domain:**"):
            domain = line.split(":", 1)[1].strip().lower()
    return {
        "runbook_id": filename.replace(".md", ""),
        "service": service,
        "severity": severity,
        "domain": domain,
        "source": str(path.relative_to(runbooks_root)),
    }


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def file_content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_file_manifest(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.is_file():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8")).get("files", {})


def save_file_manifest(manifest_path: Path, files: dict[str, str], *, collection: str, version: str) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collection": collection,
        "index_version": version,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    tmp = manifest_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(manifest_path)


def write_active_alias(collection: str, index_version: str) -> None:
    path = active_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collection": collection,
        "index_version": index_version,
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_active_collection(default: str = DEFAULT_COLLECTION) -> str:
    path = active_manifest_path()
    if not path.is_file():
        return os.getenv("CHROMA_COLLECTION", default)
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("collection", default)
    except json.JSONDecodeError:
        return default


def _build_documents(source_dir: Path, paths: list[Path]) -> tuple[list[str], list[dict], list[str]]:
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        meta_base = _parse_metadata(content, path.name, path, source_dir)
        for i, chunk in enumerate(_chunk_text(content)):
            doc_id = f"{meta_base['runbook_id']}-{i}"
            documents.append(chunk)
            metadatas.append({**meta_base, "chunk_index": i})
            ids.append(doc_id)
    return documents, metadatas, ids


def _write_fallback_index(
    persist: Path,
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
    *,
    merge_existing: bool = False,
) -> None:
    fallback = persist / "fallback_index.json"
    if merge_existing and fallback.is_file():
        store = json.loads(fallback.read_text(encoding="utf-8"))
        existing_ids = set(store.get("ids", []))
        for doc, meta, doc_id, emb in zip(
            store.get("documents", []),
            store.get("metadatas", []),
            store.get("ids", []),
            store.get("embeddings", []),
        ):
            runbook_id = meta.get("runbook_id")
            if any(m.get("runbook_id") == runbook_id for m in metadatas):
                continue
            if doc_id in existing_ids:
                documents.append(doc)
                metadatas.append(meta)
                ids.append(doc_id)

    embeddings = embed_texts(documents) if documents else []
    store = {"documents": documents, "metadatas": metadatas, "ids": ids, "embeddings": embeddings}
    fallback.write_text(json.dumps(store), encoding="utf-8")


def _chroma_client(persist: Path):
    import chromadb

    return chromadb.PersistentClient(path=str(persist))


def index_runbooks(
    *,
    source_dir: Path | None = None,
    persist_dir: Path | None = None,
    mode: Literal["full", "incremental"] = "full",
    collection_name: str | None = None,
) -> IndexResult:
    """Index SRE runbooks into Chroma with optional alias swap on full rebuild."""
    source = source_dir or runbooks_dir()
    persist = persist_dir or chroma_path()
    persist.mkdir(parents=True, exist_ok=True)

    all_paths = _iter_runbook_paths(source)
    manifest_path = persist / "file_manifest.json"
    prior_hashes = load_file_manifest(manifest_path)

    if mode == "incremental":
        changed_paths = [
            p
            for p in all_paths
            if prior_hashes.get(p.name) != file_content_hash(p)
        ]
        removed = set(prior_hashes) - {p.name for p in all_paths}
        target_paths = changed_paths
    else:
        changed_paths = all_paths
        removed = set()
        target_paths = all_paths

    version = datetime.now(timezone.utc).strftime("runbooks-%Y-%m-%d-%H%M")
    if mode == "full":
        target_collection = collection_name or f"runbooks-{version}"
    else:
        target_collection = collection_name or read_active_collection()

    documents, metadatas, ids = _build_documents(source, target_paths)
    backend = vector_backend()

    if backend == "weaviate":
        if mode == "full":
            try:
                delete_collection_objects()
            except Exception:
                pass
        else:
            for runbook_id in {p.stem for p in target_paths} | {Path(n).stem for n in removed}:
                try:
                    delete_by_runbook(runbook_id, collection=target_collection)
                except Exception:
                    pass
        if documents:
            embeddings = embed_texts(documents)
            upsert_chunks(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                collection=target_collection,
            )
        if mode == "full":
            docs, metas, doc_ids = _build_documents(source, all_paths)
            _write_fallback_index(persist, docs, metas, doc_ids)
            write_active_alias(target_collection, version)
        else:
            _rebuild_fallback_from_weaviate(persist, target_collection)
    else:
        client = _chroma_client(persist)
        if mode == "full":
            try:
                client.delete_collection(target_collection)
            except Exception:
                pass
            collection = client.get_or_create_collection(target_collection)
        else:
            collection = client.get_or_create_collection(target_collection)
            for runbook_id in {p.stem for p in target_paths} | {Path(n).stem for n in removed}:
                try:
                    existing = collection.get(include=["metadatas"])
                    delete_ids = [
                        doc_id
                        for doc_id, meta in zip(existing.get("ids", []), existing.get("metadatas", []))
                        if meta and meta.get("runbook_id") == runbook_id
                    ]
                    if delete_ids:
                        collection.delete(ids=delete_ids)
                except Exception:
                    pass

        if documents:
            embeddings = embed_texts(documents)
            collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

        if mode == "full":
            docs, metas, doc_ids = _build_documents(source, all_paths)
            _write_fallback_index(persist, docs, metas, doc_ids)
            write_active_alias(target_collection, version)
        else:
            _rebuild_fallback_from_chroma(client, target_collection, persist)

    new_hashes = {p.name: file_content_hash(p) for p in all_paths}
    save_file_manifest(manifest_path, new_hashes, collection=target_collection, version=version)

    (persist / "index_version.json").write_text(
        json.dumps(
            {
                "index_version": version,
                "collection": target_collection,
                "chunk_count": len(documents),
                "mode": mode,
            }
        ),
        encoding="utf-8",
    )

    return IndexResult(
        index_version=version,
        collection=target_collection,
        documents_indexed=len(documents),
        runbooks_indexed=len(target_paths),
        mode=mode,
        changed_files=[p.name for p in changed_paths],
    )


def _rebuild_fallback_from_weaviate(persist: Path, collection_name: str) -> None:
    try:
        from rag.weaviate_store import list_objects

        rows = list_objects(collection=collection_name, limit=2000)
        store = {
            "documents": [r["document"] for r in rows],
            "metadatas": [r["metadata"] for r in rows],
            "ids": [r["id"] for r in rows],
            "embeddings": [r.get("embedding") or [] for r in rows],
        }
        (persist / "fallback_index.json").write_text(json.dumps(store), encoding="utf-8")
    except Exception:
        pass


def _rebuild_fallback_from_chroma(client, collection_name: str, persist: Path) -> None:
    try:
        collection = client.get_collection(collection_name)
        data = collection.get(include=["documents", "metadatas", "embeddings"])
        store = {
            "documents": data.get("documents", []),
            "metadatas": data.get("metadatas", []),
            "ids": data.get("ids", []),
            "embeddings": data.get("embeddings", []),
        }
        (persist / "fallback_index.json").write_text(json.dumps(store), encoding="utf-8")
    except Exception:
        pass


def seed_runbooks_from_git(seed_dir: Path, target_dir: Path) -> list[str]:
    """Copy seed *.md runbooks into the live inbox (without overwriting newer Drive copies)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(seed_dir.glob("*.md")):
        dest = target_dir / path.name
        if not dest.exists():
            shutil.copy2(path, dest)
            copied.append(path.name)
    return copied
