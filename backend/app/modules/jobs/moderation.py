import re
import unicodedata

def screen(job):
    text = " ".join([job.title, job.description, job.requirements]).casefold()
    normalized = "".join(c for c in unicodedata.normalize("NFD", text.replace("đ","d")) if not unicodedata.combining(c))
    flags = []
    for pattern, label in [
        (r"\b(dat coc|dong phi|chuyen tien truoc)\b","Có đề cập đặt cọc hoặc chuyển tiền"),
        (r"\b(ca cuoc|danh bac|lua dao)\b","Nội dung cần xem xét"),
        (r"<\s*script\b|javascript:","Có nội dung giống mã lệnh"),
        (r"https?://|bit\.ly","Có liên kết cần xác minh"),
    ]:
        if re.search(pattern, normalized):
            flags.append(label)
    if job.salary_max is not None and job.salary_max > 30000000:
        flags.append("Mức phụ cấp cao bất thường cho tin thực tập")
    if not job.title.strip() or not job.description.strip() or not job.requirements.strip():
        flags.append("Thiếu nội dung bắt buộc")
    return flags

from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from app.ai.providers.llm import structured
from app.core.config import AI_BACKEND

class Assessment(BaseModel):
    concerns: list[Literal["fraud","discrimination","duplicated_content"]] = Field(max_length=3)

def assess(job,user_id):
    flags=screen(job)
    if not flags or len(flags)>2 or AI_BACKEND!="openai":
        return flags
    try:
        result=structured(Assessment,"Chỉ đánh dấu rủi ro có căn cứ trong nội dung. duplicated_content là nội dung tự lặp trong một tin.",
            {"title":job.title,"description":job.description,"requirements":job.requirements},
            {"concerns":[]},user_id=user_id,feature="job_moderation")
    except HTTPException as error:
        if error.status_code not in {429,503}:
            raise
        return flags
    labels={"fraud":"AI: nghi vấn lừa đảo","discrimination":"AI: nghi vấn phân biệt đối xử",
            "duplicated_content":"AI: nội dung lặp"}
    return flags+[labels[key] for key in dict.fromkeys(result.concerns)]
