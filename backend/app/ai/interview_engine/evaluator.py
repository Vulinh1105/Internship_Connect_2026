import re
from pydantic import BaseModel, Field
from app.ai.providers.llm import structured

class Criterion(BaseModel):
    criterion_id: str
    score: int = Field(ge=0,le=2)
    quote: str = Field(max_length=300)
    feedback: str = Field(max_length=450)

class Evaluation(BaseModel):
    criteria: list[Criterion] = Field(max_length=12)
    followup: str = Field(default="",max_length=350)

def evaluate(question,text,user_id,skipped=False):
    fallback={"criteria":[],"followup":""}
    for rubric in question["rubric"]:
        words=set(re.findall(r"\w+",rubric["criterion"].lower()))
        sentence=next((p.strip() for p in re.split(r"[.!?\n]+",text) if len(p.strip())>=20
                       and len(words & set(re.findall(r"\w+",p.lower())))>=2),"")
        fallback["criteria"].append({"criterion_id":rubric["criterion_id"],"score":int(bool(sentence)),
            "quote":sentence[:240],"feedback":"Bổ sung cách làm cụ thể và giải thích kết quả."})
    result=Evaluation.model_validate(fallback) if skipped else structured(
        Evaluation,"Chấm từng tiêu chí 0–2. Mỗi điểm dương cần quote nguyên văn. Chỉ hỏi tiếp nếu thiếu ví dụ cụ thể.",
        {"question":question["question"],"rubric":question["rubric"],"answer":text},fallback,
        user_id=user_id,feature="interview_eval")
    by_id={r.criterion_id:r for r in result.criteria}
    criteria=[]
    for rubric in question["rubric"]:
        row=by_id.get(rubric["criterion_id"])
        valid=bool(row and row.quote.strip() and row.quote in text)
        criteria.append({"criterion":rubric["criterion"],"score":row.score if valid else 0,
                         "quote":row.quote if valid else "","weight":rubric["weight"],
                         "feedback":row.feedback if row else "Thiếu bằng chứng trong câu trả lời."})
    weight=sum(row["weight"] for row in criteria) or 1
    score=round(50*sum(row["weight"]*row["score"] for row in criteria)/weight,1)
    return {"score":score,"criteria":criteria,"skipped":skipped},result.followup
