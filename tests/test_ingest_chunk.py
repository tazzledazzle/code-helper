"""Tests for ingest.chunk: chunk_file and chunk_directory return chunks with path metadata."""

import pytest

from ingest.chunk import chunk_file, chunk_directory


def test_chunk_file_returns_chunks_with_path_metadata(tmp_path):
    """chunk_file(path) returns list of (text, metadata); metadata includes file path."""
    py_file = tmp_path / "sample.py"
    py_file.write_text(
        "def hello():\n"
        "    return 'world'\n"
        "\n"
        "def bye():\n"
        "    return 'bye'\n"
    )
    chunks = chunk_file(py_file)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    for item in chunks:
        assert isinstance(item, (tuple, dict)), "each chunk should be (text, metadata) or dict"
        if isinstance(item, tuple):
            text, meta = item
            assert isinstance(text, str)
            assert isinstance(meta, dict)
            assert "path" in meta or "file_path" in meta
            path_val = meta.get("path") or meta.get("file_path")
            assert path_val is not None
            assert "sample.py" in str(path_val)
        else:
            assert "text" in item and "metadata" in item
            assert "path" in item["metadata"] or "file_path" in item["metadata"]
            assert "sample.py" in str(item["metadata"].get("path") or item["metadata"].get("file_path"))
    all_text = " ".join(
        c[0] if isinstance(c, tuple) else c["text"] for c in chunks
    )
    assert "hello" in all_text and "world" in all_text


def test_chunk_directory_returns_chunks_with_path_metadata(tmp_path):
    """chunk_directory(path) walks directory, filters by extension, returns chunks with path in metadata."""
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    (tmp_path / "b.py").write_text("def foo(): pass\n")
    (tmp_path / "ignore.txt").write_text("not included")
    chunks = chunk_directory(tmp_path)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    paths_seen = set()
    for item in chunks:
        if isinstance(item, tuple):
            text, meta = item
            path_val = meta.get("path") or meta.get("file_path")
        else:
            text = item["text"]
            path_val = item["metadata"].get("path") or item["metadata"].get("file_path")
        assert path_val is not None
        paths_seen.add(str(path_val))
    assert any("a.py" in p for p in paths_seen)
    assert any("b.py" in p for p in paths_seen)
    all_text = " ".join(
        c[0] if isinstance(c, tuple) else c["text"] for c in chunks
    )
    assert "x = 1" in all_text or "foo" in all_text
