"""Embedding provider — real vectors (sentence-transformers or OpenAI-compatible API)."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache


def _hash_embed(text: str) -> list[float]:
    """Test-only fallback when EMBEDDING_BACKEND=hash (pytest CI)."""
    h = hashlib.sha256(text.encode()).digest()
    return [b / 255.0 for b in h[:32]] + [0.0] * 32


@lru_cache(maxsize=1)
def _sentence_model():
    from sentence_transformers import SentenceTransformer

    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    return SentenceTransformer(model_name)


def _api_embed(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY") or "local"
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def embed_texts(texts: list[str]) -> list[list[float]]:
    backend = os.getenv("EMBEDDING_BACKEND", "local").lower()
    if backend == "hash":
        return [_hash_embed(t) for t in texts]
    if backend in ("openai", "azure", "bedrock"):
        return _api_embed(texts)
    # default: local sentence-transformers (real neural embeddings)
    model = _sentence_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
