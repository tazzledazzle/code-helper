"""Chunk files and directories for ingest; return (text, metadata) with path."""

from __future__ import annotations

import os
from pathlib import Path

# Extensions to include when walking a directory
ALLOWED_EXTENSIONS = (".py", ".md", ".ts", ".js")

# Default max lines per chunk (simple line-based chunking)
DEFAULT_CHUNK_LINES = 50


def chunk_file(
    path: str | Path,
    *,
    chunk_lines: int = DEFAULT_CHUNK_LINES,
) -> list[tuple[str, dict]]:
    """Read a single file and split into chunks. Returns list of (text, metadata).

    metadata includes "path" (str) with the file path.
    """
    path = Path(path)
    if not path.is_file():
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    path_str = str(path)
    metadata_base = {"path": path_str}
    lines = content.splitlines()
    chunks: list[tuple[str, dict]] = []
    for i in range(0, len(lines), chunk_lines):
        block = lines[i : i + chunk_lines]
        text = "\n".join(block)
        if not text.strip():
            continue
        meta = {**metadata_base, "start_line": i + 1, "end_line": i + len(block)}
        chunks.append((text, meta))
    if not chunks and content.strip():
        chunks.append((content.strip(), metadata_base))
    return chunks


def chunk_directory(
    path: str | Path,
    *,
    extensions: tuple[str, ...] = ALLOWED_EXTENSIONS,
    chunk_lines: int = DEFAULT_CHUNK_LINES,
) -> list[tuple[str, dict]]:
    """Walk directory, filter by extension, chunk each file. Returns list of (text, metadata).

    metadata includes "path" with the file path. Only files with extension in
    extensions (e.g. .py, .md, .ts, .js) are included.
    """
    path = Path(path)
    if not path.is_dir():
        return []
    result: list[tuple[str, dict]] = []
    for root, _dirs, files in os.walk(path):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in extensions:
                continue
            file_path = Path(root) / name
            result.extend(chunk_file(file_path, chunk_lines=chunk_lines))
    return result
