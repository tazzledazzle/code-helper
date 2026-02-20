"""Tests for ingest.run: run_ingest indexes a directory into the vector store."""

import pytest
import chromadb

from ingest.chunk import chunk_directory
from ingest.run import run_ingest


def _mock_embed(texts: list[str]) -> list[list[float]]:
    """Mock embed: returns fixed-dimension vectors (384) for each text. No Ollama."""
    return [[0.1] * 384 for _ in texts]


@pytest.fixture
def chroma_client():
    """In-memory Chroma client for tests."""
    return chromadb.EphemeralClient()


@pytest.fixture
def sample_project(tmp_path):
    """A small fixture dir with a few .py files to chunk."""
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n")
    (tmp_path / "b.py").write_text("x = 2\ny = 3\n")
    return tmp_path


def test_run_ingest_indexes_chunks_into_vector_store(sample_project, chroma_client):
    """run_ingest(project_path, collection_id, client=..., embed_func=...) indexes chunks; store has expected count."""
    collection_id = "test_run_ingest_coll"
    chunks = chunk_directory(sample_project)
    expected_count = len(chunks)
    assert expected_count >= 1, "fixture should yield at least one chunk"

    run_ingest(
        sample_project,
        collection_id,
        vector_db_url=None,
        client=chroma_client,
        embed_func=_mock_embed,
    )

    coll = chroma_client.get_collection(name=collection_id)
    assert coll.count() == expected_count
