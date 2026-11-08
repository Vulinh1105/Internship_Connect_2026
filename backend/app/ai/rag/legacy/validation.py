from dataclasses import dataclass
import re
from typing import List, Dict, Any

from langchain_core.documents import Document


NO_EVIDENCE_MESSAGE = "Tài liệu hiện tại không đề cập vấn đề này."

NO_EVIDENCE_PREFIXES = (
    "tài liệu hiện tại không đề cập",
    "tài liệu không đề cập",
    "không tìm thấy thông tin",
    "không có thông tin",
)

# 1. check input của user
# định nghĩa ctruc và kqua trả về -> check_query()
@dataclass(frozen=True)
class QueryCheckResult:
    allowed: bool
    reason: str | None = None


_UNSAFE_PATTERNS = (
    r"\b(ignore|bypass|reveal|leak|dump)\b.{0,60}\b(system prompt|instruction|api key|password|secret)\b",
    r"\b(delete|drop|truncate|format)\b.{0,40}\b(database|table|filesystem|file)\b",
    r"\b(hack|exploit|malware|ransomware|ddos|phishing)\b",
    r"\b(tự sát|tu sat|giết người|giet nguoi|chế tạo bom|che tao bom)\b",
)

_OUT_OF_SCOPE_PATTERNS = (
    r"\b(thời tiết|weather forecast|giá cổ phiếu|stock price|crypto price|tỷ số bóng đá|sports score)\b",
    r"\b(kể chuyện cười|write (a )?poem|viết thơ)\b",
)


# 1. kiểm tra

# khai báo hàm
def check_query(
    query: str,
    *,
    max_length: int = 2_000
) -> QueryCheckResult:

    # check 1: query rỗng?
    if not isinstance(query, str) or not query.strip():
        return QueryCheckResult(False, "empty_query")

    normalized = " ".join(query.split())

    # check 2: too longg?
    if len(normalized) > max_length:
        return QueryCheckResult(False, "query_too_long")
    # check 3
    if any(
        re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        )
        for pattern in _UNSAFE_PATTERNS
    ):
        return QueryCheckResult(False, "unsafe_or_out_of_scope")

    # check 4: ngoài phạm vi?
    if any(
        re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        )
        for pattern in _OUT_OF_SCOPE_PATTERNS
    ):
        return QueryCheckResult(False, "out_of_scope")

    # check 5: vô nghĩa?
    if not re.search(
        r"[A-Za-zÀ-ỹà-ỹ0-9]",
        normalized
    ):
        return QueryCheckResult(False, "meaningless_query")

    return QueryCheckResult(True)


# 2. check context/evidence + tạo citation
# check evidence/ context đầu vào có ton tại?
def has_evidence(
    chunks: List[Document]
) -> bool:

    if not chunks:
        return False

    for chunk in chunks:
        if isinstance(chunk, Document):
            if (
                chunk.page_content
                and chunk.page_content.strip()
            ):
                return True

    return False


# get source metadata  ==> tạo citation sau này
def get_source_metadata(
    chunk: Document
) -> Dict[str, Any]:
    """
    Lấy metadata citation từ Document
    """

    if not isinstance(
        chunk,
        Document
    ):
        return {
            "source": None,
            "page": None,
            "chunk_index": None,
            "chunk_id": None,
        }

    metadata = chunk.metadata

    if not isinstance(metadata, dict):
        metadata = {}

    # sourse
    source = (
        metadata.get("source")
        or metadata.get("source_file")
        or metadata.get("file_name")
        or metadata.get("filename")
        or metadata.get("document_name")
        or (
            f"document_{metadata['document_id']}"
            if metadata.get("document_id") is not None
            else None
        )
    )

    # page
    page = metadata.get("page")

    if page is None:
        page = metadata.get("page_number")

    # chunk_index
    chunk_index = metadata.get("chunk_index")

    return {
        "source": source,
        "page": page,
        "chunk_index": chunk_index,
        "chunk_id": metadata.get("chunk_id"),
    }


def build_citations(
    chunks: List[Document]
) -> List[Dict[str, Any]]:
    """
    Tạo citation từ metadata thật của chunks.
    KHÔNG lấy citation do LLM tự sinh.
    """

    grouped = {}

    for chunk in chunks:

        metadata = get_source_metadata(chunk)
        source = metadata["source"]
        page = metadata["page"]

        # Không có source -> không tạo citation
        if not source:
            continue

        if source not in grouped:
            grouped[source] = {
                "source": source,
                "pages": [],
                "chunk_ids": []
            }

        if (
            page is not None
            and page not in grouped[source]["pages"]
        ):
            grouped[source]["pages"].append(page)

        if (
            metadata["chunk_id"] is not None
            and metadata["chunk_id"]
            not in grouped[source]["chunk_ids"]
        ):
            grouped[source]["chunk_ids"].append(
                metadata["chunk_id"]
            )

    citations = []

    for source, data in grouped.items():

        data["pages"].sort()

        citations.append({
            "source": source,
            "pages": data["pages"],
            "chunk_ids": data["chunk_ids"],
        })

    return citations


def format_citations(
    citations: List[Dict[str, Any]]
) -> str:
    """
    Format citation để hiển thị cho người dùng.
    """

    if not citations:
        return ""

    lines = [
        "",
        "Nguồn tham khảo:"
    ]

    for citation in citations:

        source = citation["source"]
        pages = citation.get("pages", [])
        chunk_ids = citation.get("chunk_ids", [])

        chunk_text = (
            f" (chunk: {', '.join(str(item) for item in chunk_ids)})"
            if chunk_ids
            else ""
        )

        # Có source + page
        if pages:

            pages = sorted(set(pages))

            if len(pages) == 1:
                page_text = f"trang {pages[0]}"
            else:
                page_text = (
                    "trang "
                    + ", ".join(
                        str(page)
                        for page in pages
                    )
                )

            lines.append(
                f"- {source}, {page_text}{chunk_text}"
            )

        # Chỉ có source
        else:
            lines.append(
                f"- {source}{chunk_text}"
            )

    return "\n".join(lines)


# 3. check output của LLM
# hàm nhan diện no-evidence
def is_no_evidence_answer(
    answer: str
) -> bool:

    if not isinstance(answer, str):
        return False

    normalized = " ".join(
        answer.strip().lower().split()
    )

    return any(
        normalized.startswith(prefix)
        for prefix in NO_EVIDENCE_PREFIXES
    )


# final
def validate_answer(
    answer: str,
    chunks: List[Document]
) -> Dict[str, Any]:
    """
    Validation cuối cùng của T17.

    Trả về:

    {
        "valid": True/False,
        "answer": "...",
        "citations": [...]
    }
    """

    # 1. LLM không trả lời
    if not isinstance(answer, str) or not answer.strip():
        return {
            "valid": False,
            "reason": "empty_answer",
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }

    answer = answer.strip()

    # 2. LLM trả câu no-evidence
    if is_no_evidence_answer(answer):
        return {
            "valid": False,
            "reason": "no_evidence",
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }

    # 3. Không có evidence
    if not has_evidence(chunks):
        return {
            "valid": False,
            "reason": "no_context",
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }

    # 4. Tạo citation từ metadata thật
    citations = build_citations(chunks)

    # Có context nhưng không có nguồn
    if not citations:
        return {
            "valid": False,
            "reason": "missing_citations",
            "answer": NO_EVIDENCE_MESSAGE,
            "citations": []
        }

    # 5. Ghép Answer + Citation
    final_answer = (
        answer
        + format_citations(citations)
    )

    return {
        "valid": True,
        "reason": None,
        "answer": final_answer,
        "citations": citations
    }


# print('validation done')
