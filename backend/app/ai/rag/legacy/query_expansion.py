from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


# Schema kết quả tách câu hỏi so sánh.

class QueryExpansionResult(BaseModel):
    is_comparison: bool = Field(
        description=(
            "True nếu câu hỏi yêu cầu so sánh từ 2 đối tượng "
            "(quốc gia, công ty, ngành...) trở lên."
        )
    )

    sub_queries: list[str] = Field(
        default_factory=list,
        description=(
            "Danh sách câu hỏi con, mỗi câu chỉ hỏi về 1 đối tượng, "
            "giữ nguyên đại lượng/thuộc tính của câu hỏi gốc."
        ),
    )


# Prompt tách câu hỏi so sánh.

QUERY_EXPANSION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Bạn là bộ phân tích câu hỏi cho hệ thống RAG.

Nhiệm vụ: xác định câu hỏi của người dùng có phải là câu hỏi
so sánh giữa từ 2 đối tượng trở lên hay không (VD: so sánh giữa
2 quốc gia, 2 công ty, 2 ngành, 2 giai đoạn thời gian...).

Nếu ĐÚNG là câu hỏi so sánh:
- Tách thành các câu hỏi con, mỗi câu hỏi con chỉ hỏi về DUY NHẤT
  một đối tượng.
- Mỗi câu hỏi con phải giữ nguyên đại lượng/thuộc tính mà câu hỏi
  gốc yêu cầu (VD: nếu hỏi "tỷ lệ thất nghiệp", mỗi câu hỏi con
  cũng phải hỏi về "tỷ lệ thất nghiệp", không đổi thành khái niệm
  khác).
- Mỗi câu hỏi con phải là câu hỏi độc lập, đầy đủ ngữ nghĩa,
  không phụ thuộc ngữ cảnh của câu hỏi gốc.
- KHÔNG tự thêm thông tin, số liệu hoặc giả định nào không có
  trong câu hỏi gốc.

Nếu câu hỏi KHÔNG phải câu hỏi so sánh (chỉ hỏi về 1 đối tượng,
hoặc là câu hỏi chung chung không nêu đối tượng cụ thể):
- is_comparison = false
- sub_queries = []

Chỉ trả về kết quả theo đúng schema, không giải thích thêm."""
        ),
        (
            "human",
            "Câu hỏi: {query}",
        ),
    ]
)


def split_comparison_query(
    query: str,
) -> list[str] | None:

    if not query or not query.strip():
        return None

    try:
        llm = ChatOpenAI(
            model="gpt-5.4-nano",
            temperature=0,
        )

        structured_llm = llm.with_structured_output(
            QueryExpansionResult
        )

        chain = (
            QUERY_EXPANSION_PROMPT
            | structured_llm
        )

        result: QueryExpansionResult = chain.invoke(
            {"query": query}
        )

    except Exception:
        return None

    # Lọc sub_query rỗng / trùng nhau, giữ thứ tự.
    sub_queries = [
        sub.strip()
        for sub in result.sub_queries
        if sub and sub.strip()
    ]
    sub_queries = list(dict.fromkeys(sub_queries))

    if not result.is_comparison or len(sub_queries) < 2:
        return None

    return sub_queries