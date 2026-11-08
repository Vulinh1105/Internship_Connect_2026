from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


# THÊM:
# Schema kết quả của Evidence Judge.

class EvidenceJudgeResult(BaseModel):
    sufficient: bool = Field(
        description=(
            "Cho biết các evidence được chọn "
            "có đủ để trả lời câu hỏi hay không."
        )
    )

    supported_indices: list[int] = Field(
        default_factory=list,
        description=(
            "Danh sách index của các chunk thực sự "
            "hỗ trợ câu hỏi. Index bắt đầu từ 0."
        ),
    )

    reason: str = Field(
        default="",
        description=(
            "Giải thích ngắn gọn tại sao evidence "
            "được xem là đủ hoặc không đủ."
        ),
    )


# THÊM:
# Prompt dành riêng cho Evidence Judge.

EVIDENCE_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Bạn là Evidence Judge cho hệ thống RAG.

Nhiệm vụ của bạn là xác định những đoạn tài liệu nào thực sự
hỗ trợ việc trả lời câu hỏi.

Chỉ được đánh giá dựa trên câu hỏi và các chunk được cung cấp.

Quy tắc:
1. Chỉ chọn chunk nếu nội dung của chunk thực sự hỗ trợ câu hỏi.
2. Không chọn chunk chỉ vì có từ khóa giống câu hỏi.
3. Phải xét đúng đối tượng/chủ thể mà câu hỏi đề cập.
4. Phải xét đúng phạm vi, thời gian, đại lượng hoặc thuộc tính
   mà câu hỏi yêu cầu khi các thông tin này xuất hiện trong câu hỏi.
5. Không kết hợp các chunk thuộc những đối tượng hoặc phạm vi
   khác nhau để tạo thành evidence.
6. Nếu các chunk chỉ liên quan về chủ đề nhưng không đủ để
   trả lời câu hỏi, không chọn chúng.
7. Có thể chọn nhiều chunk nếu chúng bổ sung evidence cho cùng
   một câu hỏi và không mâu thuẫn về đối tượng/phạm vi.
8. Nếu không có chunk nào đủ để hỗ trợ câu hỏi,
   sufficient phải là false và supported_indices phải rỗng.
9. Không sử dụng kiến thức bên ngoài.
10. Không tự tạo thông tin không xuất hiện trong các chunk.
11. supported_indices phải chứa index của chunk, bắt đầu từ 0.

THÊM (rule 12-13, để sửa lỗi Judge từ chối oan các chunk thiếu
tên quốc gia/năm ngay trong nội dung dù đã có trong tên file):

12. Mỗi chunk có kèm "source" (tên tài liệu chứa chunk đó).
    Nếu "source" cho biết rõ chunk thuộc về đối tượng/năm nào
    (ví dụ tên file có ghi rõ "KINH TẾ VIỆT NAM NĂM 2025" hoặc
    "KINH TẾ TRUNG QUỐC NĂM 2025"), được phép dùng "source" để
    xác định đối tượng/phạm vi thời gian của chunk đó. Không bắt
    buộc bản thân nội dung chunk phải lặp lại tên quốc gia hoặc
    năm nếu "source" đã xác định rõ điều đó.
13. "reason" bạn trả về phải nhất quán với "sufficient":
    nếu trong "reason" bạn kết luận rằng bằng chứng không đủ,
    không rõ ràng, hoặc không chunk nào hỗ trợ câu hỏi, thì
    "sufficient" bắt buộc phải là false và "supported_indices"
    phải rỗng. Không được vừa nói "không đủ" trong reason vừa
    trả về sufficient=true.

Mục tiêu là chọn evidence, không phải trả lời câu hỏi."""
        ),
        (
            "human",
            """Câu hỏi:
{query}

Các chunk sau đây đã được retrieval và reranking chọn làm candidate:

{chunks}

Hãy xác định những chunk thực sự hỗ trợ câu hỏi."""
        ),
    ]
)



# Chuyển list[Document] thành context có index.
#
# Index được dùng làm "ID tạm thời" trong một lần judge.
# Evidence Judge chỉ trả index.
# Nội dung Document thật vẫn do Python giữ nguyên.
def _format_chunks(
    chunks: list[Document],
) -> str:

    formatted: list[str] = []

    for index, document in enumerate(chunks):

        metadata = document.metadata

        source = (
            metadata.get("source")
            or metadata.get("source_file")
            or metadata.get("file_name")
            or metadata.get("filename")
            or metadata.get("document_name")
        )

        page = (
            metadata.get("page")
            or metadata.get("page_number")
        )

        chunk_id = metadata.get(
            "chunk_id"
        )

        formatted.append(
            f"[CHUNK {index}]\n"
            f"source: {source}\n"
            f"page: {page}\n"
            f"chunk_id: {chunk_id}\n"
            f"content:\n"
            f"{document.page_content}"
        )

    return "\n\n---\n\n".join(
        formatted
    )


# THÊM:
# Safety net cho lỗi model output không tự nhất quán (sufficient=True
# nhưng reason lại kết luận "không đủ").
#
# SỬA (Bug 1 phát hiện qua log thực tế): bản patterns trước đó quá
# rộng -- ví dụ pattern "không đề cập" đã khớp nhầm với câu giải thích
# hoàn toàn bình thường "Chunk 0 nêu đúng X... Các chunk khác KHÔNG ĐỀ
# CẬP đến Y" (đây là câu xác nhận CÓ đủ evidence, không phải câu kết
# luận thiếu evidence), khiến case "Dự trữ ngoại hối của Trung Quốc"
# bị refuse oan dù trước đó luôn trả lời đúng.
#
# Từ log mới nhất cũng cho thấy rule 13 trong prompt ở trên đã tự sửa
# được phần lớn mâu thuẫn sufficient/reason ngay từ model (case "Hệ số
# Engel" giờ model tự trả sufficient=False đúng ngay từ đầu, không cần
# safety net can thiệp nữa). Vì vậy safety net này giờ CHỈ còn là lớp
# phòng hờ cho 2 tình huống rất đặc trưng, khó gây false positive:
#   (a) model nói thẳng "sufficient ... là false" trong lời giải thích
#       (tức tự mâu thuẫn với field sufficient=True nó trả về)
#   (b) reason MỞ ĐẦU ngay bằng kết luận "không đủ"/"chưa đủ" (không
#       phải xuất hiện giữa câu như các case false positive cũ)
_INSUFFICIENT_REASON_PATTERNS = (
    r"sufficient[^.]{0,60}(là|nên là|=)\s*false",
    r"^(không đủ|chưa đủ)\b",
)


def _reason_indicates_insufficient(reason: str) -> bool:
    """Trả True nếu reason (text tự do của LLM) tự mâu thuẫn với
    sufficient=True theo 1 trong 2 pattern rất đặc trưng ở trên."""

    if not reason:
        return False

    normalized = reason.strip().lower()

    return any(
        re.search(pattern, normalized)
        for pattern in _INSUFFICIENT_REASON_PATTERNS
    )



# Hàm Evidence Judge chính.
#
# Input:
#   query
#   reranked_chunks
#
# Output:
#   EvidenceJudgeResult
#
# component độc lập với graph.
def judge_evidence(
    query: str,
    chunks: list[Document],
) -> EvidenceJudgeResult:

    if not query or not query.strip():
        return EvidenceJudgeResult(
            sufficient=False,
            supported_indices=[],
            reason="empty_query",
        )

    if not chunks:
        return EvidenceJudgeResult(
            sufficient=False,
            supported_indices=[],
            reason="no_candidate_chunks",
        )

    context = _format_chunks(
        chunks
    )

    llm = ChatOpenAI(
        model="gpt-5.4-nano",
        temperature=0,
    )

    structured_llm = llm.with_structured_output(
        EvidenceJudgeResult
    )

    chain = (
        EVIDENCE_JUDGE_PROMPT
        | structured_llm
    )

    result: EvidenceJudgeResult = (
        chain.invoke(
            {
                "query": query,
                "chunks": context,
            }
        )
    )

    # Python kiểm tra lại range trước khi graph sử dụng chúng.
    valid_indices = [
        index
        for index in result.supported_indices
        if (
            isinstance(index, int)
            and 0 <= index < len(chunks)
        )
    ]


    # Loại duplicate index và giữ thứ tự.
    valid_indices = list(
        dict.fromkeys(
            valid_indices
        )
    )

    # Áp dụng safety net (đã thu hẹp, xem comment ở trên).
    reason_says_insufficient = _reason_indicates_insufficient(
        result.reason
    )

    sufficient = (
        bool(valid_indices)
        and result.sufficient
        and not reason_says_insufficient
    )

    return EvidenceJudgeResult(
        sufficient=sufficient,
        supported_indices=valid_indices if sufficient else [],
        reason=result.reason,
    )