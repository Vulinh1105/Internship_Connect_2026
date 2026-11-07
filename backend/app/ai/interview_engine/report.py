from collections import defaultdict
from pydantic import BaseModel, Field
from app.ai.providers.llm import structured
from app.ai.providers.model_config import REPORT
from app.core.config import AI_BACKEND

class Advice(BaseModel):
    practice: list[str] = Field(min_length=1,max_length=4)
    example: str = Field(default="",max_length=1000)

def summarize(answers,previous,user_id=None):
    rows=defaultdict(list)
    for answer in answers:
        rows[answer.position].append(answer)
    best=[max(group,key=lambda answer:answer.evaluation["score"]) for group in rows.values()]
    score=round(sum(a.evaluation["score"] for a in best)/max(len(best),1),1)
    practiced=[a for a in best if not a.evaluation["skipped"]]
    weak=min(practiced,key=lambda a:a.evaluation["score"],default=None)
    criteria=[c for a in practiced for c in a.evaluation["criteria"]]
    strengths=sorted((c for c in criteria if c["quote"]),key=lambda c:c["score"],reverse=True)[:3]
    gaps=sorted((c for c in criteria if c["score"]<2),key=lambda c:c["score"])[:3]
    practice=["Dùng tình huống, hành động và kết quả khi trả lời.",
              "Luyện lại tiêu chí thiếu dẫn chứng, rồi so sánh với buổi trước."]
    example=""
    if weak and AI_BACKEND=="openai" and user_id is not None:
        from fastapi import HTTPException
        try:
            advice=structured(Advice,"Dựa vào các tiêu chí còn thiếu, đưa lời khuyên. Viết câu trả lời mẫu giả định, không gán thành tích cho sinh viên.",
                {"weak_question":weak.question,"gaps":[c["criterion"] for c in gaps]},
                {"practice":practice,"example":""},user_id=user_id,feature="interview_report",model=REPORT)
            practice,example=advice.practice,advice.example
        except HTTPException as error:
            if error.status_code not in {429,503}:
                raise
    return {"score":score,"previous_score":previous,"delta":round(score-previous,1) if previous is not None else None,
            "answers":[{"question":a.question,"transcript":a.transcript,**a.evaluation} for a in answers],
            "strengths":strengths,"gaps":gaps,"practice":practice,"example":example}
