from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from .evidence import EvidenceJudgeResult, judge_evidence
from .query_expansion import split_comparison_query
from .state import RAGState
from .validation import (
    NO_EVIDENCE_MESSAGE,
    QueryCheckResult,
    check_query,
    validate_answer,
)

logger = logging.getLogger(__name__)

# Cấu hình mặc định

DEFAULT_RETRIEVE_K = 20

DEFAULT_RERANK_TOP_K = 8

DEFAULT_MIN_RERANK_SCORE = 0.05

# Refusal messages (theo lý do)
_TECHNICAL_ERROR_MESSAGE = (
    "Hệ thống đang gặp sự cố khi xử lý câu hỏi. Vui lòng thử lại sau."
)

REFUSAL_MESSAGES: dict[str, str] = {
    # --- check_query ---
    "empty_query": "Vui lòng nhập câu hỏi.",
    "query_too_long": "Câu hỏi quá dài. Vui lòng rút gọn và thử lại.",
    "meaningless_query": "Tôi chưa hiểu câu hỏi. Vui lòng diễn đạt lại.",
    "unsafe_or_out_of_scope": "Tôi không thể hỗ trợ yêu cầu này.",
    "out_of_scope": "Câu hỏi này nằm ngoài phạm vi tài liệu hiện có.",
    # --- lỗi hệ thống ---
    "evidence_judge_error": _TECHNICAL_ERROR_MESSAGE,
    "generation_error": _TECHNICAL_ERROR_MESSAGE,
    # Các lý do còn lại (no_retrieved_chunks, low_retrieval_quality,
    # insufficient_evidence, empty_answer, no_evidence, no_context,
    # missing_citations, ...) -> NO_EVIDENCE_MESSAGE.
}


def _short_id(chunk: Document) -> str:
    """Id ngắn gọn của chunk để in log (vd: doc56_p3_c002)."""
    meta = chunk.metadata
    raw = meta.get("chunk_id") or meta.get("qdrant_point_id") or "?"
    return str(raw).replace("_semantic", "")


# THÊM:
# Key dùng để dedupe chunk khi gộp evidence_chunks từ nhiều branch
def _doc_key(chunk: Document) -> str:
    meta = chunk.metadata
    return str(
        meta.get("chunk_id")
        or meta.get("qdrant_point_id")
        or f"{meta.get('document_id', '')}_{meta.get('chunk_index', '')}"
    )


# Kiểu dependency
class RetrieverLike(Protocol):
    def retrieve(self, query: str, k: int = 8) -> list[Document]: ...


class RerankerLike(Protocol):
    def rerank(
            self,
            query: str,
            documents: list[Document],
            top_k: int = 5,
    ) -> tuple[list[Document], float]: ...


GenerateFn = Callable[[str, list[Document]], str]


# Kiểu hàm sinh câu trả lời cho câu hỏi so sánh. Nhận query gốc +
# danh sách (sub_query, evidence_chunks) theo từng đối tượng.
ComparisonGenerateFn = Callable[[str, list[tuple[str, list[Document]]]], str]

QueryCheckFn = Callable[[str], QueryCheckResult]
EvidenceJudgeFn = Callable[[str, list[Document]], EvidenceJudgeResult]
AnswerValidatorFn = Callable[[str, list[Document]], dict[str, Any]]
SaveTurnFn = Callable[[str, str, str, list[dict[str, Any]]], None]


# Build graph
def build_rag_graph(
        *,
        retriever: RetrieverLike,
        reranker: RerankerLike,
        generate_fn: GenerateFn,
        comparison_generate_fn: ComparisonGenerateFn,
        query_checker: QueryCheckFn = check_query,
        comparison_splitter: Callable[[str], list[str] | None] = split_comparison_query,
        evidence_judge: EvidenceJudgeFn = judge_evidence,
        answer_validator: AnswerValidatorFn = validate_answer,
        save_turn_fn: SaveTurnFn | None = None,
        retrieve_k: int = DEFAULT_RETRIEVE_K,
        rerank_top_k: int = DEFAULT_RERANK_TOP_K,
        min_rerank_score: float = DEFAULT_MIN_RERANK_SCORE,
):
    """
    Tạo và compile LangGraph cho RAG pipeline.

    Args:
        retriever:        HybridRetriever (hoặc bất kỳ object có .retrieve(query, k)).
        reranker:         Reranker (có .rerank(query, documents, top_k)).
        generate_fn:      hàm (query, evidence_chunks) -> câu trả lời thô của LLM
                           cho câu hỏi ĐƠN (không so sánh).
        comparison_generate_fn: - hàm (query, list[(sub_query,
                           evidence_chunks)]) -> câu trả lời thô cho câu hỏi
                           SO SÁNH nhiều đối tượng.
        query_checker:    hàm kiểm tra query đầu vào (mặc định validation.check_query).
        evidence_judge:   hàm chọn evidence (mặc định evidence.judge_evidence).
        answer_validator: hàm validate câu trả lời + gắn citation.
        save_turn_fn:     hàm lưu lượt hội thoại (session_id, query, answer, citations).
        retrieve_k:       số chunk lấy từ hybrid retrieval (áp dụng cho cả
                           query đơn lẫn từng sub_query khi so sánh).
        rerank_top_k:     số chunk giữ lại sau rerank (áp dụng cho cả 2 trường hợp trên).
        min_rerank_score: ngưỡng rerank score để coi retrieval là "good".
    """

    # Helpers
    def effective_query(state: RAGState) -> str:
        # retrieval_query là query đã chuẩn hóa (sau này có thể là query đã rewrite).
        # Với câu hỏi so sánh, đây vẫn là câu hỏi GỐC (ghép), dùng làm "query"
        # truyền vào comparison_generate_fn - còn từng sub_query nằm riêng
        # trong mỗi phần tử của comparison_branches.
        return (state.get("retrieval_query") or state.get("query") or "").strip()

    # Nodes
    # 1. VALIDATION — check_query
    def validate_query_node(state: RAGState) -> dict[str, Any]:
        query = state.get("query", "")
        result = query_checker(query)

        if not result.allowed:
            logger.info("validate_query: refused (%s)", result.reason)
            return {
                "query_allowed": False,
                "refusal_reason": result.reason or "query_not_allowed",
            }

        return {
            "query_allowed": True,
            "retrieval_query": " ".join(query.split()),
        }

    # 2. RETRIEVAL — Hybrid Search (semantic + keyword + RRF)
    #
    # nếu phát hiện câu hỏi so sánh nhiều đối tượng,
    # KHÔNG gộp phẳng kết quả retrieve của các sub_query lại thành 1
    # list như bản trước nữa (đó là cách nửa vời, vẫn rerank chung 1
    # điểm bằng query gốc, làm loãng tín hiệu). Thay vào đó, mỗi
    # sub_query được lưu thành 1 "branch" riêng, và rerank_node/
    # check_quality_node/select_evidence_node bên dưới sẽ xử lý ĐỘC LẬP từng branch bằng đúng sub_query của nó.
    def retrieve_node(state: RAGState) -> dict[str, Any]:
        query = effective_query(state)

        sub_queries = comparison_splitter(query)

        if sub_queries:
            logger.info(
                "retrieve: phát hiện câu hỏi so sánh, sub_queries=%s",
                sub_queries,
            )

            branches: list[dict[str, Any]] = []

            for sub_query in sub_queries:
                sub_chunks = retriever.retrieve(sub_query, k=retrieve_k)

                logger.info(
                    "retrieve[%s]: %d chunks", sub_query, len(sub_chunks)
                )
                logger.info(
                    "retrieve[%s] ids: %s",
                    sub_query,
                    ", ".join(_short_id(c) for c in sub_chunks),
                )

                branches.append(
                    {
                        "sub_query": sub_query,
                        "retrieved_chunks": sub_chunks,
                    }
                )

            return {
                "is_comparison": True,
                "comparison_branches": branches,
                "sub_queries": sub_queries,
                "hybrid_attempted": True,
            }

        # Không phải câu hỏi so sánh -> hành vi y hệt code cũ.
        chunks = retriever.retrieve(query, k=retrieve_k)
        logger.info("retrieve: %d chunks", len(chunks))
        logger.info("retrieve ids: %s", ", ".join(_short_id(c) for c in chunks))
        return {
            "is_comparison": False,
            "retrieved_chunks": chunks,
            "hybrid_attempted": True,
            "sub_queries": [],
        }

    # 3. RERANKING — CrossEncoder
    #
    # nếu is_comparison=True, rerank TỪNG branch bằng
    # ĐÚNG sub_query của branch đó (không dùng chung query gốc như
    # trước) - đây chính là fix cho Bug 3 (rerank vẫn dùng câu hỏi
    # ghép làm loãng tín hiệu, khiến case "so sánh tỷ lệ thất nghiệp"
    # bị chặn ở check_quality dù retrieve đã đúng).
    def rerank_node(state: RAGState) -> dict[str, Any]:

        if state.get("is_comparison"):
            branches = state.get("comparison_branches", [])
            updated_branches: list[dict[str, Any]] = []

            for branch in branches:
                sub_query = branch["sub_query"]
                sub_chunks = branch.get("retrieved_chunks", [])

                reranked, latency_ms = reranker.rerank(
                    sub_query,
                    sub_chunks,
                    top_k=rerank_top_k,
                )

                logger.info(
                    "rerank[%s]: %d -> %d chunks (%.0f ms)",
                    sub_query,
                    len(sub_chunks),
                    len(reranked),
                    latency_ms,
                )
                logger.info(
                    "rerank[%s] scores: %s",
                    sub_query,
                    ", ".join(
                        f"{_short_id(c)}={c.metadata.get('rerank_score', 0.0):.3f}"
                        for c in reranked
                    ),
                )

                branch = dict(branch)
                branch["reranked_chunks"] = reranked
                branch["rerank_latency_ms"] = latency_ms
                updated_branches.append(branch)

            return {"comparison_branches": updated_branches}

        # Không phải câu hỏi so sánh -> hành vi y hệt code cũ.
        chunks = state.get("retrieved_chunks", [])
        reranked, latency_ms = reranker.rerank(
            effective_query(state),
            chunks,
            top_k=rerank_top_k,
        )
        logger.info(
            "rerank: %d -> %d chunks (%.0f ms)",
            len(chunks),
            len(reranked),
            latency_ms,
        )
        logger.info(
            "rerank scores: %s",
            ", ".join(
                f"{_short_id(c)}={c.metadata.get('rerank_score', 0.0):.3f}"
                for c in reranked
            ),
        )
        return {
            "reranked_chunks": reranked,
            "rerank_latency_ms": latency_ms,
        }

    # 4. RETRIEVAL QUALITY — kiểm tra rerank score
    #
    # với câu hỏi so sánh, tính quality RIÊNG cho từng
    # branch. Chỉ refuse toàn bộ khi TẤT CẢ các branch đều "poor" -
    # nếu có ít nhất 1 branch "good", vẫn cho đi tiếp để branch đó có
    # cơ hội trả lời (branch "poor" sẽ được đánh dấu thiếu dữ liệu ở
    # select_evidence_node, không tốn thêm lời gọi Evidence Judge).
    def check_quality_node(state: RAGState) -> dict[str, Any]:

        if state.get("is_comparison"):
            branches = state.get("comparison_branches", [])
            updated_branches: list[dict[str, Any]] = []
            any_good = False
            any_chunks = False

            for branch in branches:
                sub_query = branch["sub_query"]
                chunks = branch.get("reranked_chunks", [])

                if chunks:
                    any_chunks = True
                    top_score = max(
                        float(c.metadata.get("rerank_score", float("-inf")))
                        for c in chunks
                    )
                else:
                    top_score = 0.0

                quality = "good" if top_score >= min_rerank_score else "poor"
                if quality == "good":
                    any_good = True

                logger.info(
                    "check_quality[%s]: %s (top=%.4f)",
                    sub_query,
                    quality,
                    top_score,
                )

                branch = dict(branch)
                branch["top_rerank_score"] = top_score
                branch["retrieval_quality"] = quality
                updated_branches.append(branch)

            overall_top_score = max(
                (b["top_rerank_score"] for b in updated_branches),
                default=0.0,
            )

            if not any_good:
                return {
                    "comparison_branches": updated_branches,
                    "retrieval_quality": "poor",
                    "top_rerank_score": overall_top_score,
                    "refusal_reason": (
                        "low_retrieval_quality"
                        if any_chunks
                        else "no_retrieved_chunks"
                    ),
                }

            return {
                "comparison_branches": updated_branches,
                "retrieval_quality": "good",
                "top_rerank_score": overall_top_score,
            }

        # Không phải câu hỏi so sánh -> hành vi y hệt code cũ.
        chunks = state.get("reranked_chunks", [])

        if not chunks:
            return {
                "retrieval_quality": "poor",
                "top_rerank_score": 0.0,
                "refusal_reason": "no_retrieved_chunks",
            }

        top_score = max(
            float(chunk.metadata.get("rerank_score", float("-inf")))
            for chunk in chunks
        )

        if top_score >= min_rerank_score:
            logger.info("check_quality: good (top=%.4f)", top_score)
            return {
                "retrieval_quality": "good",
                "top_rerank_score": top_score,
            }

        logger.info(
            "check_quality: poor (top=%.4f < %.4f)", top_score, min_rerank_score
        )
        return {
            "retrieval_quality": "poor",
            "top_rerank_score": top_score,
            "refusal_reason": "low_retrieval_quality",
        }

    # 5. EVIDENCE SELECT — Evidence Judge
    # với câu hỏi so sánh, chạy Evidence Judge RIÊNG
    # cho từng branch có quality="good" (branch "poor" bị bỏ qua,
    # không tốn lời gọi Judge, tự đánh dấu evidence_sufficient=False
    # với lý do "low_retrieval_quality"). Chỉ refuse toàn bộ khi
    # KHÔNG branch nào có evidence_sufficient=True - đây chính là cơ
    # chế cho phép trả lời "1 bên có data, 1 bên không" ở generate_node.
    def select_evidence_node(state: RAGState) -> dict[str, Any]:

        if state.get("is_comparison"):
            branches = state.get("comparison_branches", [])
            updated_branches: list[dict[str, Any]] = []
            any_sufficient = False

            for branch in branches:
                sub_query = branch["sub_query"]

                if branch.get("retrieval_quality") != "good":
                    branch = dict(branch)
                    branch["evidence_chunks"] = []
                    branch["evidence_sufficient"] = False
                    branch["evidence_reason"] = "low_retrieval_quality"
                    updated_branches.append(branch)
                    logger.info(
                        "select_evidence[%s]: skip (retrieval_quality=poor)",
                        sub_query,
                    )
                    continue

                chunks = branch.get("reranked_chunks", [])

                try:
                    result = evidence_judge(sub_query, chunks)
                except Exception:
                    logger.exception(
                        "Evidence Judge failed for branch '%s'", sub_query
                    )
                    branch = dict(branch)
                    branch["evidence_chunks"] = []
                    branch["evidence_sufficient"] = False
                    branch["evidence_reason"] = "evidence_judge_error"
                    updated_branches.append(branch)
                    continue

                evidence_chunks = [
                    chunks[index]
                    for index in result.supported_indices
                    if 0 <= index < len(chunks)
                ]
                sufficient = bool(result.sufficient and evidence_chunks)

                if sufficient:
                    any_sufficient = True

                logger.info(
                    "select_evidence[%s]: sufficient=%s indices=%s reason=%s",
                    sub_query,
                    sufficient,
                    result.supported_indices,
                    result.reason,
                )

                branch = dict(branch)
                branch["evidence_chunks"] = evidence_chunks
                branch["evidence_sufficient"] = sufficient
                branch["evidence_reason"] = result.reason
                updated_branches.append(branch)

            if not any_sufficient:
                all_errored = all(
                    b.get("evidence_reason") == "evidence_judge_error"
                    for b in updated_branches
                )
                return {
                    "comparison_branches": updated_branches,
                    "evidence_sufficient": False,
                    "refusal_reason": (
                        "evidence_judge_error"
                        if all_errored
                        else "insufficient_evidence"
                    ),
                }

            return {
                "comparison_branches": updated_branches,
                "evidence_sufficient": True,
            }

        # Không phải câu hỏi so sánh -> hành vi y hệt code cũ.
        chunks = state.get("reranked_chunks", [])

        try:
            result = evidence_judge(effective_query(state), chunks)
        except Exception:
            # Fail-closed: không chắc có evidence -> không cho generation.
            logger.exception("Evidence Judge failed")
            return {
                "evidence_chunks": [],
                "evidence_sufficient": False,
                "refusal_reason": "evidence_judge_error",
            }

        # Judge chỉ trả về index; Document thật vẫn do Python giữ nguyên.
        evidence_chunks = [
            chunks[index]
            for index in result.supported_indices
            if 0 <= index < len(chunks)
        ]
        sufficient = bool(result.sufficient and evidence_chunks)

        logger.info(
            "select_evidence: sufficient=%s indices=%s reason=%s",
            sufficient,
            result.supported_indices,
            result.reason,
        )

        update: dict[str, Any] = {
            "evidence_chunks": evidence_chunks,
            "evidence_sufficient": sufficient,
            "evidence_reason": result.reason,
        }
        if not sufficient:
            update["refusal_reason"] = "insufficient_evidence"
        return update

    # 6. GENERATE — LLM chỉ nhìn evidence_chunks
    #
    # với câu hỏi so sánh, gọi comparison_generate_fn
    # với danh sách (sub_query, evidence_chunks) của TẤT CẢ branch
    # (kể cả branch evidence_chunks rỗng - để LLM biết đối tượng đó
    # thiếu dữ liệu và nêu rõ trong câu trả lời theo rule 3 của COMPARISON_SYSTEM_PROMPT_TEMPLATE).
    def generate_node(state: RAGState) -> dict[str, Any]:

        if state.get("is_comparison"):
            branches = state.get("comparison_branches", [])
            branch_inputs = [
                (branch["sub_query"], branch.get("evidence_chunks", []))
                for branch in branches
            ]

            try:
                answer = comparison_generate_fn(
                    effective_query(state),
                    branch_inputs,
                )
            except Exception:
                logger.exception("Comparison generation failed")
                return {
                    "raw_answer": "",
                    "answer": "",
                    "refusal_reason": "generation_error",
                }

            return {
                "raw_answer": answer,
                "answer": answer,
            }

        # Không phải câu hỏi so sánh -> hành vi y hệt code cũ.
        try:
            answer = generate_fn(
                effective_query(state),
                state.get("evidence_chunks", []),
            )
        except Exception:
            logger.exception("Generation failed")
            return {
                "raw_answer": "",
                "answer": "",
                "refusal_reason": "generation_error",
            }

        return {
            "raw_answer": answer,
            "answer": answer,
        }

    # 7. VALIDATE ANSWER — kiểm tra output + tạo citation từ metadata thật
    #
    # với câu hỏi so sánh, citation phải gộp evidence_chunks
    # từ TẤT CẢ branch có sufficient=True (dedupe theo _doc_key để tránh
    # trùng nếu 2 branch vô tình cùng chọn 1 chunk).
    def validate_answer_node(state: RAGState) -> dict[str, Any]:

        if state.get("is_comparison"):
            branches = state.get("comparison_branches", [])
            merged_evidence: list[Document] = []
            seen_keys: set[str] = set()

            for branch in branches:
                for doc in branch.get("evidence_chunks", []):
                    key = _doc_key(doc)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        merged_evidence.append(doc)

            result = answer_validator(
                state.get("answer", ""),
                merged_evidence,
            )

            if result.get("valid"):
                return {
                    "valid": True,
                    "answer": result["answer"],
                    "citations": result.get("citations", []),
                    "guardrail_reason": None,
                }

            reason = result.get("reason") or "invalid_answer"
            logger.info("validate_answer: invalid (%s)", reason)
            return {
                "valid": False,
                "guardrail_reason": reason,
                "refusal_reason": reason,
            }

        # Không phải câu hỏi so sánh -> hành vi y hệt code cũ.
        result = answer_validator(
            state.get("answer", ""),
            state.get("evidence_chunks", []),
        )

        if result.get("valid"):
            return {
                "valid": True,
                "answer": result["answer"],
                "citations": result.get("citations", []),
                "guardrail_reason": None,
            }

        reason = result.get("reason") or "invalid_answer"
        logger.info("validate_answer: invalid (%s)", reason)
        return {
            "valid": False,
            "guardrail_reason": reason,
            "refusal_reason": reason,
        }

    # 8. SAVE TURN — chỉ chạy khi câu trả lời hợp lệ
    def save_turn_node(state: RAGState) -> dict[str, Any]:
        query = state.get("query", "")
        answer = state.get("answer", "")
        citations = state.get("citations", [])

        if save_turn_fn is not None:
            try:
                save_turn_fn(
                    state.get("session_id", "default"),
                    query,
                    answer,
                    citations,
                )
            except Exception:
                # Lỗi lưu lịch sử không được làm hỏng câu trả lời đã hợp lệ.
                logger.exception("Failed to save turn")

        history = list(state.get("history", []))
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})

        return {
            "history": history,
            "route": "answer",
        }

    # REFUSE — điểm dừng chung cho mọi nhánh từ chối
    def refuse_node(state: RAGState) -> dict[str, Any]:
        reason = state.get("refusal_reason") or "unknown"
        return {
            "answer": REFUSAL_MESSAGES.get(reason, NO_EVIDENCE_MESSAGE),
            "citations": [],
            "valid": False,
            "refusal_reason": reason,
            "route": "refuse",
        }

    # Routers (conditional edges)
    #
    # GHI CHÚ (Hướng B): các router bên dưới KHÔNG cần sửa gì, vì cả
    # nhánh so sánh lẫn nhánh câu hỏi đơn đều ghi field top-level
    # "retrieval_quality" và "evidence_sufficient" giống nhau về mặt
    # tên field (chỉ khác cách tính bên trong check_quality_node/
    # select_evidence_node ở trên) - router chỉ đọc field top-level
    # nên dùng chung được cho cả 2 nhánh.
    def route_after_query_check(state: RAGState) -> str:
        return "retrieve" if state.get("query_allowed") else "refuse"

    def route_after_quality(state: RAGState) -> str:
        return (
            "select_evidence"
            if state.get("retrieval_quality") == "good"
            else "refuse"
        )

    def route_after_evidence(state: RAGState) -> str:
        return "generate" if state.get("evidence_sufficient") else "refuse"

    def route_after_generate(state: RAGState) -> str:
        # generate_node chỉ set refusal_reason khi LLM bị lỗi.
        return "refuse" if state.get("refusal_reason") else "validate_answer"

    def route_after_validation(state: RAGState) -> str:
        return "save_turn" if state.get("valid") else "refuse"

    # Wiring
    builder = StateGraph(RAGState)

    builder.add_node("validate_query", validate_query_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("rerank", rerank_node)
    builder.add_node("check_quality", check_quality_node)
    builder.add_node("select_evidence", select_evidence_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate_answer", validate_answer_node)
    builder.add_node("save_turn", save_turn_node)
    builder.add_node("refuse", refuse_node)

    builder.add_edge(START, "validate_query")

    builder.add_conditional_edges(
        "validate_query",
        route_after_query_check,
        {"retrieve": "retrieve", "refuse": "refuse"},
    )

    builder.add_edge("retrieve", "rerank")
    builder.add_edge("rerank", "check_quality")

    builder.add_conditional_edges(
        "check_quality",
        route_after_quality,
        {"select_evidence": "select_evidence", "refuse": "refuse"},
    )

    builder.add_conditional_edges(
        "select_evidence",
        route_after_evidence,
        {"generate": "generate", "refuse": "refuse"},
    )

    builder.add_conditional_edges(
        "generate",
        route_after_generate,
        {"validate_answer": "validate_answer", "refuse": "refuse"},
    )

    builder.add_conditional_edges(
        "validate_answer",
        route_after_validation,
        {"save_turn": "save_turn", "refuse": "refuse"},
    )

    builder.add_edge("save_turn", END)
    builder.add_edge("refuse", END)

    return builder.compile()