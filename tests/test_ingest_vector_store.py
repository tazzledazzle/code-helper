"""Tests for ingest.vector_store: upsert chunks and query Chroma."""

import pytest
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from ingest.vector_store import upsert, query


class FakeEmbeddingFunction(EmbeddingFunction[Documents]):
    """In-memory embedder (384 dims) so tests do not touch disk or network."""

    def __init__(self) -> None:
        pass

    def name(self) -> str:
        return "fake"

    def __call__(self, input: Documents) -> Embeddings:
        # Match MiniLM dimension; deterministic per doc for reproducibility.
        return [[hash(d) % 1000 / 1000.0] * 384 for d in input]


@pytest.fixture
def chroma_client():
    """In-memory Chroma client for tests."""
    return chromadb.EphemeralClient()


@pytest.fixture
def fake_embedding():
    """Fake embedding function for tests (no ONNX download)."""
    return FakeEmbeddingFunction()


def test_upsert_and_query_returns_added_chunks(chroma_client, fake_embedding):
    """Given chunks and collection name, upsert adds them and query returns those chunks."""
    collection_id = "test_project"
    chunks = [
        "First chunk about Python functions.",
        "Second chunk about vector databases.",
        "Third chunk about ChromaDB.",
    ]
    metadatas = [
        {"source": "a.py", "line": 1},
        {"source": "b.py", "line": 2},
        {"source": "c.py", "line": 3},
    ]

    upsert(collection_id, chunks, metadatas=metadatas, client=chroma_client, embedding_function=fake_embedding)

    results = query(
        collection_id,
        "Python and vectors",
        n_results=3,
        client=chroma_client,
        embedding_function=fake_embedding,
    )

    assert results is not None
    assert "documents" in results
    doc_list = results["documents"]
    assert len(doc_list) >= 1
    # Each inner list is the list of documents for that query (we have one query)
    flat_docs = doc_list[0] if doc_list and isinstance(doc_list[0], list) else doc_list
    texts = [d for d in flat_docs if d]
    assert len(texts) == 3
    for chunk in chunks:
        assert any(chunk in t for t in texts)


def test_upsert_without_metadatas_and_query_by_content(chroma_client, fake_embedding):
    """Upsert without metadatas; query returns expected count and content."""
    collection_id = "minimal_collection"
    texts = ["Hello world", "Goodbye world"]

    upsert(collection_id, texts, client=chroma_client, embedding_function=fake_embedding)
    results = query(collection_id, "world", n_results=5, client=chroma_client, embedding_function=fake_embedding)

    assert results is not None
    assert "documents" in results
    doc_list = results["documents"]
    assert len(doc_list) >= 1
    flat = doc_list[0] if doc_list and isinstance(doc_list[0], list) else doc_list
    assert len(flat) >= 2
    all_text = " ".join(t for t in flat if t)
    assert "Hello world" in all_text
    assert "Goodbye world" in all_text
