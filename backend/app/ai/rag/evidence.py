# Evidence Judge reused from chatbot_AI/backend/app/ai_agent/evidence.py.
# Adapted to the current provider and SQL chunk records.
import re
from pydantic import BaseModel, Field
from app.ai.providers.llm import structured


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


EVIDENCE_JUDGE_INSTRUCTION = """Bạn là Evidence Judge cho hệ thống RAG.

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


def judge_evidence(user_id,question,chunks):
    fallback=EvidenceJudgeResult(sufficient=False,reason="no_candidate_chunks")
    if not chunks:
        return []
    candidates=[{"index":index,"source":chunk["title"],"content":chunk["text"]}
                for index,chunk in enumerate(chunks)]
    result=structured(EvidenceJudgeResult,EVIDENCE_JUDGE_INSTRUCTION,
                      {"query":question,"chunks":candidates},fallback.model_dump(),
                      user_id=user_id,feature="rag_evidence")
    indices=list(dict.fromkeys(index for index in result.supported_indices if 0<=index<len(chunks)))
    if not result.sufficient or _reason_indicates_insufficient(result.reason):
        return []
    return [chunks[index] for index in indices]
