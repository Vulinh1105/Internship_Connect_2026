from typing import Annotated

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.ai.providers.llm import structured
from app.ai.providers.model_config import REPORT
from .planner import Domain

RUBRIC = {
    "knowledge": [
        "Hiểu biết kiến thức nền tảng", "Độ chính xác",
        "Giải thích và vận dụng kiến thức", "Mức độ đầy đủ và chuyên sâu",
    ],
    "problem_solving": [
        "Xác định và phân tích vấn đề", "Tư duy logic và lập luận",
        "Tính hợp lý của phương án", "Đánh giá kết quả và hạn chế",
    ],
}
BANDS = ("0–2: bỏ qua hoặc sai bản chất; 3–4: thiếu chính xác hoặc thiếu logic; "
         "5–6: nắm cơ bản; 7–8: đúng trọng tâm, có lập luận; 9–10: chính xác, đầy đủ, có chiều sâu.")
TURN_LIMIT = 10
TEXT_LIMIT = 30000
Mark = Annotated[int, Field(ge=0,le=10)]


class DomainResult(BaseModel):
    domain: Domain
    scores: tuple[Mark, Mark, Mark, Mark]
    quote: str = Field(default="",max_length=220)
    feedback: str = Field(max_length=260)


class TurnResult(BaseModel):
    turn_id: int
    results: list[DomainResult] = Field(max_length=2)


class Remark(BaseModel):
    text: str = Field(min_length=1,max_length=300)
    turn_ids: list[int] = Field(min_length=1,max_length=5)


class Summary(BaseModel):
    strengths: list[Remark] = Field(max_length=4)
    limitations: list[Remark] = Field(max_length=4)
    practice: list[str] = Field(max_length=4)


class Batch(BaseModel):
    turns: list[TurnResult] = Field(max_length=TURN_LIMIT)
    summary: Summary | None = None


def batches(turns):
    group, size = [], 0
    for turn in turns:
        length = len(turn["question"])+len(turn["transcript"])
        if group and (len(group)>=TURN_LIMIT or size+length>TEXT_LIMIT):
            yield group
            group,size = [],0
        group.append(turn)
        size += length
    if group:
        yield group


def evaluate(group,role,level,user_id,*,whole):
    response=structured(Batch,
        "Bạn là Evaluation AI. Đọc tất cả lượt trong nhóm. Chấm mỗi lượt có transcript và domains, đúng các domains "
        "được chỉ định. Bỏ qua lượt không có transcript hoặc domains rỗng trong kết quả turns. "
        "reference_topics là hướng dẫn nội bộ. Không trích nguyên văn chúng trong phản hồi; điểm luôn theo rubric chung. "
        "Với mỗi domain, trả đúng 4 điểm nguyên từ 0 đến 10 theo đúng thứ tự rubric. "
        "Mỗi domain có điểm dương phải trích một đoạn nguyên văn liên tục từ transcript của chính lượt đó. "
        "Feedback ngắn gọn, giải thích các điểm có căn cứ và những gì còn thiếu. Không suy đoán thành tích. "
        "Nếu whole=true, thêm summary bằng tiếng Việt với điểm mạnh, hạn chế, gợi ý luyện tập và turn_ids "
        "làm bằng chứng. Nếu whole=false, để summary=null.",
        {"role":role,"level":level,"rubric":RUBRIC,"bands":BANDS,"whole":whole,"turns":group},
        None,user_id=user_id,feature="interview_eval",model=REPORT,force_openai=True,max_completion_tokens=5000)
    expected={t["turn_id"]:t for t in group if t["transcript"] and t["domains"]}
    results={t.turn_id:t.results for t in response.turns}
    invalid=HTTPException(503,"AI chưa trả đủ điểm và dẫn chứng cho lịch sử phỏng vấn. Hãy thử chấm lại.")
    if len(results)!=len(response.turns) or results.keys()!=expected.keys():
        raise invalid
    for ident,rows in results.items():
        if len(rows)!=len(expected[ident]["domains"]) or {r.domain for r in rows}!=set(expected[ident]["domains"]):
            raise invalid
        text=" ".join(expected[ident]["transcript"].split())
        for row in rows:
            quote=" ".join(row.quote.split())
            if (any(row.scores) and not quote) or (quote and quote not in text):
                raise invalid
            row.quote=quote
    if whole and response.summary is None:
        raise invalid
    return {ident:[row.model_dump() for row in rows] for ident,rows in results.items()},response.summary


def synthesize(role,level,results,scores,user_id):
    return structured(Summary,
        "Tổng hợp các lượt đã chấm thành điểm mạnh, hạn chế và hướng luyện tập bằng tiếng Việt. "
        "Các điểm tổng hợp đã được tính theo rubric, giữ nguyên chúng. Dùng turn_ids thật và chỉ nêu "
        "nhận xét có căn cứ trong các điểm, phản hồi hoặc trích dẫn đã xác minh.",
        {"role":role,"level":level,"scores":scores,"rubric":RUBRIC,"evaluated_turns":results},
        None,user_id=user_id,feature="interview_synthesis",model=REPORT,force_openai=True,max_completion_tokens=2200)
