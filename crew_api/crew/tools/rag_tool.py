"""RAG tool: query vector store and return top-k chunks for the Coder agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from crewai.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

from ingest.vector_store import query as vector_store_query

if TYPE_CHECKING:
    import chromadb


class RAGToolInput(BaseModel):
    """Input schema for RAGTool."""

    query: str = Field(..., description="Search query to find relevant document chunks.")
    collection_id: str = Field(..., description="Chroma collection id (e.g. project identifier).")


class RAGTool(BaseTool):
    """Query a Chroma collection and return top-k document chunks as formatted text."""

    name: str = "rag_search"
    description: str = (
        "Search project documentation/code chunks in the vector store. "
        "Provide a query and collection_id (project). Returns top relevant chunks."
    )
    args_schema: type[BaseModel] = RAGToolInput

    client: Optional[Any] = None
    embedding_function: Optional[Any] = None
    n_results: int = 5

    def _run(self, query: str, collection_id: str) -> str:
        results = vector_store_query(
            collection_id,
            query,
            n_results=self.n_results,
            client=self.client,
            embedding_function=self.embedding_function,
        )
        if not results or "documents" not in results:
            return "No results found."
        doc_list = results["documents"]
        # Chroma returns list of lists (one per query)
        flat = doc_list[0] if doc_list and isinstance(doc_list[0], list) else doc_list
        chunks = [c for c in flat if c]
        if not chunks:
            return "No results found."
        return "\n\n---\n\n".join(chunks)
