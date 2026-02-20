"""Call Ollama-style embed API to turn texts into vectors."""

from __future__ import annotations

import urllib.parse

import httpx

# Default model and base URL for Ollama
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://localhost:11434"


def embed(
    texts: list[str],
    base_url: str = DEFAULT_BASE_URL,
    model: str = DEFAULT_EMBED_MODEL,
) -> list[list[float]]:
    """Call Ollama-style embed API. Returns list of embedding vectors (list[float] per text).

    POST to base_url/api/embed with {"model": model, "input": texts}.
    Raises on HTTP or response errors.
    """
    if not texts:
        return []
    base = base_url.rstrip("/")
    url = urllib.parse.urljoin(base + "/", "api/embed")
    payload: dict = {"model": model, "input": texts if len(texts) != 1 else texts[0]}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings")
    if embeddings is None:
        # Single-text response may be {"embedding": [...]}
        single = data.get("embedding")
        if single is not None:
            embeddings = [single]
        else:
            raise ValueError("Ollama response missing 'embeddings' and 'embedding'")
    if len(embeddings) != len(texts):
        raise ValueError(
            f"Ollama returned {len(embeddings)} embeddings for {len(texts)} texts"
        )
    return embeddings
