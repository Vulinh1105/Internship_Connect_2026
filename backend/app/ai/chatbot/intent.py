import re
from typing import Literal
from pydantic import BaseModel,Field
from app.ai.providers.embedding import normalize
from app.ai.providers.llm import structured

class Entities(BaseModel):
    location: str=Field(default="",max_length=100)
    category: str=Field(default="",max_length=100)
    level: Literal["","intern","fresher","junior","senior"]=""
    work_mode: Literal["","onsite","hybrid","remote"]=""
    salary_min: int|None=Field(default=None,ge=0,le=1_000_000_000)
    skills: list[str]=Field(default_factory=list,max_length=12)

class Intent(BaseModel):
    intent: Literal["job_search","job_detail","compare","application_status","knowledge","cv_advice","mock","other"]
    confidence: float=Field(ge=0,le=1)
    query: str=Field(max_length=500)
    entities: Entities=Field(default_factory=Entities)

def classify(user_id,question,history,summary,has_job,profile):
    t=normalize(question)
    if re.search(r"\b(bo qua (chi dan|huong dan)|ignore (all|previous)|system prompt|lay api key)\b",t):
        return Intent(intent="other",confidence=1,query=question)
    if re.search(r"\bdemo-a\d+\b",t) or any(x in t for x in ("don cua toi","don ung tuyen cua toi","trang thai ung tuyen")):
        kind="application_status"
    elif "phong van thu" in t or "phong van ao" in t:
        kind="mock"
    elif "tu van cv" in t or "cv cua toi" in t:
        kind="cv_advice"
    elif "so sanh" in t and (has_job or any(x in t for x in ("tin ","vi tri","cong viec"))):
        kind="compare"
    elif ("chi tiet" in t and (has_job or "tin " in t or "vi tri" in t)) or (has_job and "tin nay" in t):
        kind="job_detail"
    elif any(x in t for x in ("tu nop","dat han","cho duyet","cong khai","tien ve")):
        kind="knowledge"
    elif any(x in t for x in ("tim viec","tim tin","goi y","co viec","vi tri nao")):
        kind="job_search"
    elif any(x in t for x in ("ung tuyen","phong van","cv","ho so","han nop","phu cap","ky nang","kiem duyet","cong khai","cho duyet","dat han","con han","het han")):
        kind="knowledge"
    elif t.strip(" .!?") in {"chao", "xin chao", "chao ban", "hello", "hi", "cam on"}:
        kind="other"
    else:
        kind="knowledge"
    loc=next((x for x in ["Hà Nội","Đà Nẵng","Hồ Chí Minh","Cần Thơ"] if normalize(x) in t),"")
    fallback=Intent(intent=kind,confidence=.9,query=question,entities=Entities(location=loc))
    return structured(Intent,"Viết lại câu hỏi tự đủ ngữ cảnh và phân loại ý định. Dùng knowledge cho câu hỏi thông tin có thể tra trong tài liệu, kể cả chủ đề mới. Chỉ trích bộ lọc có căn cứ.",
                      {"question":question,"recent":history,"summary":summary,"profile":profile},fallback.model_dump(),
                      user_id=user_id,feature="chat_route")
