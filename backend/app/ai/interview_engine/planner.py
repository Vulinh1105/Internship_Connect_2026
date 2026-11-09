from typing import Literal

from pydantic import BaseModel, Field

from app.ai.providers.llm import structured

Domain = Literal["knowledge","problem_solving"]


class Wording(BaseModel):
    code: str
    question: str = Field(min_length=12,max_length=350)
    domains: list[Domain] = Field(max_length=2)


class PlanWording(BaseModel):
    questions: list[Wording] = Field(max_length=7)


class NextTurn(BaseModel):
    followup: str = Field(default="",max_length=350)
    next_question: str = Field(default="",max_length=350)


def default_domains(kind):
    if kind=="technical":
        return ["knowledge"]
    if kind in ("behavioral","situational"):
        return ["problem_solving"]
    return []


def general(code,prompt,kind):
    return {"code":code,"question":prompt,"kind":kind,"seconds":120}


def plan(role,questions,job,profile,user_id,*,level="intern"):
    technical=[q for q in questions if q["kind"]=="technical"][:3]
    behavioral=[q for q in questions if q["kind"]=="behavioral"][:1]
    result=[
        general("INTRO","Hãy giới thiệu bản thân và một trải nghiệm liên quan đến vị trí này.","introduction"),
        *technical,*behavioral,
        general("SITUATION","Khi sắp đến hạn mà yêu cầu công việc còn mơ hồ, bạn sẽ làm gì?","situational"),
        general("MOTIVATION","Vì sao bạn muốn thực tập ở vị trí này, và bạn sẽ học gì trong tháng đầu?","motivation"),
    ]
    phrasing=structured(PlanWording,
        "Bạn là Interview AI. Viết lại câu hỏi theo vị trí, cấp độ và kỹ năng. Giữ mã và chủ đề từng câu, "
        "không đưa thông tin nhận dạng, không chấm điểm. Gán domains: knowledge cho câu kiểm tra chuyên môn, "
        "problem_solving cho câu xử lý tình huống, cả hai nếu câu đòi hỏi cả kiến thức và phương án. "
        "Câu khởi động hoặc động lực có thể có domains rỗng. Luôn có câu kiểm tra kiến thức và câu xử lý vấn đề.",
        {"role":role,"level":level,"job":job,"skills":profile["skills"],"questions":result},None,
        user_id=user_id,feature="interview_plan",force_openai=True,max_completion_tokens=1800)
    by_code={q.code:q for q in phrasing.questions}
    planned=[]
    for q in result:
        wording=by_code.get(q["code"])
        domains=list(dict.fromkeys(wording.domains)) if wording else []
        planned.append({**q,"level":level,"question":wording.question if wording else q["question"],
                        "domains":domains or default_domains(q["kind"])})
    if technical and not any("knowledge" in q["domains"] for q in planned):
        planned[1]["domains"].append("knowledge")
    if not any("problem_solving" in q["domains"] for q in planned):
        planned[-2]["domains"].append("problem_solving")
    return planned


def next_turn(role,question,prompt,answer,recent,upcoming,can_followup,user_id):
    return structured(NextTurn,
        "Bạn là Interview AI. Dựa trên câu trả lời mới nhất, nếu can_followup và cần làm rõ một chi tiết, "
        "hãy hỏi một câu bổ sung cùng phạm vi đánh giá. Nếu không, có thể điều chỉnh cách hỏi của câu tiếp theo "
        "để nối mạch với câu trả lời, giữ nguyên chủ đề và phạm vi đánh giá. Không chấm điểm, không gợi ý đáp án, "
        "không nhắc thông tin nhận dạng. Trả chuỗi rỗng nếu không cần điều chỉnh.",
        {"role":role,"level":question.get("level","intern"),"question":prompt,"answer":answer,
         "recent":recent,"upcoming":upcoming,"can_followup":can_followup},None,
        user_id=user_id,feature="interview_next",force_openai=True)
