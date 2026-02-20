"""Ingest pipeline: walk + chunk, embed, upsert. Entrypoint for CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from ingest.chunk import chunk_directory
from ingest.embed import embed as ollama_embed
from ingest.embed import DEFAULT_BASE_URL
from ingest.vector_store import upsert


def _embedding_function_for(
    embed_func: Callable[[list[str]], list[list[float]]] | None,
    embed_base_url: str = DEFAULT_BASE_URL,
) -> EmbeddingFunction[Documents]:
    """Wrap embed_func or Ollama embed into a Chroma EmbeddingFunction."""

    def _call(input: Documents) -> Embeddings:
        texts = list(input)
        if not texts:
            return []
        if embed_func is not None:
            return embed_func(texts)
        return ollama_embed(texts, base_url=embed_base_url)

    class _Wrapper(EmbeddingFunction[Documents]):
        def __init__(self) -> None:
            pass

        def name(self) -> str:
            return "ingest_embed"

        def __call__(self, input: Documents) -> Embeddings:
            return _call(input)

    return _Wrapper()


def run_ingest(
    project_path: str | Path,
    collection_id: str,
    vector_db_url: str | None = None,
    *,
    client: chromadb.Client | None = None,
    embed_func: Callable[[list[str]], list[list[float]]] | None = None,
    embed_base_url: str = DEFAULT_BASE_URL,
) -> None:
    """Chunk project dir, embed texts, upsert to vector store.

    If client is provided it is used (e.g. for tests). Else if vector_db_url
    is set, a Chroma HttpClient is created; otherwise an in-memory client is used.
    If embed_func is provided it is used; otherwise Ollama is called via embed.embed.
    """
    project_path = Path(project_path)
    if not project_path.is_dir():
        raise NotADirectoryError(f"project_path is not a directory: {project_path}")

    if client is None and vector_db_url:
        parsed = urlparse(vector_db_url)
        client = chromadb.HttpClient(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8000,
        )
    elif client is None:
        client = chromadb.Client()

    chunks = chunk_directory(project_path)
    if not chunks:
        return
    texts = [t for t, _ in chunks]
    metadatas = [m for _, m in chunks]
    ef = _embedding_function_for(embed_func, embed_base_url=embed_base_url)
    upsert(
        collection_id,
        texts,
        metadatas=metadatas,
        client=client,
        embedding_function=ef,
    )


def _main() -> None:
    """Entrypoint: python -m ingest.run <project_path>. Vector URL from env."""
    if len(sys.argv) < 2:
        print("Usage: python -m ingest.run <project_path>", file=sys.stderr)
        sys.exit(1)
    project_path = Path(sys.argv[1]).resolve()
    if not project_path.is_dir():
        print(f"Not a directory: {project_path}", file=sys.stderr)
        sys.exit(1)
    vector_db_url = os.environ.get("VECTOR_DB_URL") or os.environ.get("CHROMA_URL")
    # Derive collection_id from project path (stable hash-like id)
    collection_id = f"code_{project_path.name}"
    run_ingest(project_path, collection_id, vector_db_url=vector_db_url)


if __name__ == "__main__":
    _main()
