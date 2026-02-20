"""Chroma vector store: create/get collection, upsert chunks, query by text."""

from __future__ import annotations

import chromadb


def _get_client(client: chromadb.Client | None) -> chromadb.Client:
    """Return the given client or a default in-memory client."""
    if client is not None:
        return client
    return chromadb.Client()


def upsert(
    collection_id: str,
    texts: list[str],
    metadatas: list[dict] | None = None,
    *,
    client: chromadb.Client | None = None,
    embedding_function: chromadb.api.types.EmbeddingFunction | None = None,
) -> None:
    """Add document chunks to a Chroma collection (creates collection if needed).

    Uses Chroma's default embedding when no embeddings are provided.
    Pass embedding_function to avoid default embedder (e.g. for tests without disk).
    """
    c = _get_client(client)
    kwargs = {"name": collection_id}
    if embedding_function is not None:
        kwargs["embedding_function"] = embedding_function
    coll = c.get_or_create_collection(**kwargs)
    ids = [f"chunk_{i}" for i in range(len(texts))]
    coll.add(ids=ids, documents=texts, metadatas=metadatas)


def query(
    collection_id: str,
    query_text: str,
    n_results: int = 5,
    *,
    client: chromadb.Client | None = None,
    embedding_function: chromadb.api.types.EmbeddingFunction | None = None,
) -> dict:
    """Query a collection by text; returns Chroma result dict with 'documents' (list of lists)."""
    c = _get_client(client)
    kwargs = {"name": collection_id}
    if embedding_function is not None:
        kwargs["embedding_function"] = embedding_function
    coll = c.get_or_create_collection(**kwargs)
    return coll.query(query_texts=[query_text], n_results=n_results)
