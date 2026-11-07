from pydantic import BaseModel, Field
from app.ai.providers.llm import structured

class Wording(BaseModel):
    code: str
    question: str = Field(min_length=12,max_length=350)

class PlanWording(BaseModel):
    questions: list[Wording] = Field(max_length=7)

def general(code,prompt,criterion,kind):
    return {"code":code,"question":prompt,"kind":kind,"seconds":120,
            "rubric":[{"criterion_id":"C1","criterion":criterion,"weight":100}],"version":"1"}

def plan(role,questions,job,profile,user_id):
    technical=[q for q in questions if q["kind"]=="technical"][:3]
    behavioral=[q for q in questions if q["kind"]=="behavioral"][:1]
    result=[
        general("INTRO","Hãy giới thiệu bản thân và một trải nghiệm liên quan đến vị trí này.",
                "Giới thiệu rõ mục tiêu, kỹ năng và ví dụ cụ thể","introduction"),
        *technical,*behavioral,
        general("SITUATION","Khi sắp đến hạn mà yêu cầu công việc còn mơ hồ, bạn sẽ làm gì?",
                "Làm rõ yêu cầu, thống nhất ưu tiên và thông báo tiến độ","situational"),
        general("MOTIVATION","Vì sao bạn muốn thực tập ở vị trí này, và bạn sẽ học gì trong tháng đầu?",
                "Nêu lý do cụ thể và kế hoạch học có thể thực hiện","motivation"),
    ]
    fallback={"questions":[{"code":q["code"],"question":q["question"]} for q in result]}
    phrasing=structured(PlanWording,
        "Cá nhân hóa cách hỏi theo vị trí và kỹ năng đã khai báo. Giữ nguyên mã và ý đánh giá của từng câu. Không đưa thông tin cá nhân hoặc điều kiện mới.",
        {"role":role,"job":job,"skills":profile["skills"],"questions":result},fallback,
        user_id=user_id,feature="interview_plan")
    by_code={q.code:q.question for q in phrasing.questions}
    return [{**q,"question":by_code.get(q["code"],q["question"])} for q in result]
