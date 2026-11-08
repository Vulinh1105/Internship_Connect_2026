import pytest

from app.ai.rag.generate import extract_locally
from app.ai.rag.lists import complete_list, list_heading


QUESTIONS = [
    "bao nhiêu tuổi thì được đi làm",
    "độ tuổi đi làm là bao nhiêu",
    "độ tuổi lao động tối thiểu là bao nhiêu",
]
DISTRACTORS = [
    {"text": "Người lao động nuôi con dưới 12 tháng tuổi được ưu tiên giao kết hợp đồng mới."},
    {"text": "Người lao động có thể đi làm việc ở nơi khác trong thời gian đình công."},
]


@pytest.mark.parametrize("question", QUESTIONS)
def test_work_age_questions_require_a_direct_passage(question):
    assert extract_locally(question, DISTRACTORS) == {"evidence": []}

    direct = "Độtuôi lao động tối thiểu của người lao động là đủ15 tuổi, trừ trường hợp quy định riêng."
    chunks = [*DISTRACTORS, {"text": direct}]
    assert extract_locally(question, chunks) == {"evidence": [{"source": 3, "quote": direct}]}

def test_counted_list_spans_overlapping_chunks():
    question = "các năng lực cần xây dựng của Data Analyst"
    anchor = "Data Analyst 6 năng lực cần xây dựng 01 CLEANING Làm sạch dữ liệu. 02 JOIN Kết hợp bảng. 03"
    following = ("02 JOIN Kết hợp bảng. 03 KPI Đo hiệu quả. 04 THỐNG KÊ MÔ TẢ Mô tả dữ liệu. "
                 "05 STORYTELLING Trình bày kết quả. 06 CLEANING Luyện với ví dụ. Phần tiếp theo.")
    heading = list_heading(question, anchor)
    assert heading is not None
    assert list_heading(question, anchor.replace("Data Analyst", "Data Engineer")) is None
    assert complete_list(heading, anchor, []) is None

    quote, markers = complete_list(heading, anchor, [following])
    assert [quote[offset:offset + 2] for offset in markers] == ["01", "02", "03", "04", "05", "06"]
    assert quote.count("02 JOIN") == 1
    assert quote.count("CLEANING") == 2
    assert quote.endswith("06 CLEANING Luyện với ví dụ.")


@pytest.mark.parametrize("question", [
    "năng lực cần xây dựng của AI/ML Engineer là gì",
    "Liệt kê 6 năng lực cần xây dựng của AI/ML Engineer",
])
def test_chat_answers_the_complete_list_without_request_markers(monkeypatch, question):
    from contextlib import nullcontext
    from app.ai.rag import legacy_runtime

    anchor = {
        "document_id": 7, "position": 10, "title": "Cẩm nang", "source": "guide.pdf",
        "text": "AI/ML Engineer 6 năng lực cần xây dựng 01 TRAINING Huấn luyện. 02 INFERENCE Suy luận. 03",
    }
    neighbor = {
        "position": 11,
        "text": ("02 INFERENCE Suy luận. 03 EMBEDDINGS Biểu diễn. 04 EVALUATION Đánh giá. "
                 "05 MODEL SERVING Triển khai. 06 TRAINING Thực hành. Phần tiếp theo."),
    }
    monkeypatch.setattr(legacy_runtime, "call", lambda *args: nullcontext())
    monkeypatch.setattr(legacy_runtime, "retrieve", lambda *args, **kwargs: [anchor])
    monkeypatch.setattr(legacy_runtime.knowledge, "chunks_for", lambda *args, **kwargs: [neighbor])

    def fail_on_fallback(*args, **kwargs):
        pytest.fail("A complete matching list should not fall back to a single excerpt.")

    monkeypatch.setattr(legacy_runtime, "_run", fail_on_fallback)
    result = legacy_runtime.answer(None, None, question, "unused")
    assert [line[:2] for line in result["answer"].splitlines()[1:]] == ["01", "02", "03", "04", "05", "06"]
    assert result["sources"][0]["document_id"] == 7
