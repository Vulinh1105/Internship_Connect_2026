from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.documents import Document


# data structure: định nghĩa dữ liệu được truyền giữa các node trong LangGraph
class RAGState(TypedDict, total=False):
    query: str
    session_id: str
    history: list[Any]
    cached_context: list[Document]
    query_allowed: bool
    refusal_reason: str
    needs_rewrite: bool
    rewritten_query: str
    retrieval_query: str
    retrieved_chunks: list[Document]
    reranked_chunks: list[Document]
    sub_queries: list[str]

    is_comparison: bool

    comparison_branches: list[dict[str, Any]]


    evidence_chunks: list[Document]

    evidence_sufficient: bool

    # THÊM: lý do ngắn gọn do Evidence Judge trả về (debug / evaluation).
    evidence_reason: str

    retrieval_quality: str  # "good" | "poor"

    # THÊM: rerank score cao nhất, dùng cho bước Retrieval Quality + debug.
    top_rerank_score: float

    # THÊM: latency của bước rerank (ms).
    rerank_latency_ms: float

    hybrid_attempted: bool

    # THÊM: câu trả lời thô của LLM (trước khi validate / gắn citation).
    # Giữ lại để debug vì khi bị refuse, `answer` sẽ bị thay bằng refusal message.
    raw_answer: str

    answer: str
    citations: list[dict[str, Any]]
    guardrail_reason: str | None
    valid: bool
    route: str