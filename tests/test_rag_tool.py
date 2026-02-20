"""Tests for RAG tool: query Chroma and return top-k chunks."""

import pytest
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from ingest.vector_store import upsert
from crew_api.crew.tools import RAGTool


class FakeEmbeddingFunction(EmbeddingFunction[Documents]):
    """In-memory embedder for tests (no disk/network)."""

    def __init__(self) -> None:
        pass

    def name(self) -> str:
        return "fake"

    def __call__(self, input: Documents) -> Embeddings:
        return [[hash(d) % 1000 / 1000.0] * 384 for d in input]


@pytest.fixture
def chroma_client():
    """In-memory Chroma client for tests."""
    return chromadb.EphemeralClient()


@pytest.fixture
def fake_embedding():
    return FakeEmbeddingFunction()


def test_rag_tool_returns_top_k_chunks_from_chroma(chroma_client, fake_embedding):
    """RAG tool: given query and collection_id, returns top-k chunks from Chroma with expected content."""
    collection_id = "test_rag_collection"
    chunks = [
        "RAG retrieves relevant document chunks.",
        "Chroma is a vector database.",
        "Use embedding to find similar text.",
    ]
    upsert(
        collection_id,
        chunks,
        client=chroma_client,
        embedding_function=fake_embedding,
    )

    tool = RAGTool(
        client=chroma_client,
        embedding_function=fake_embedding,
    )
    result = tool.run(query="vector database", collection_id=collection_id)

    assert result is not None
    assert isinstance(result, str)
    assert "Chroma" in result
    assert "vector database" in result or "RAG" in result or "embedding" in result
