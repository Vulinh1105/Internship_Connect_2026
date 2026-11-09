from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class JobInput(BaseModel):
    company_id: int
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=15, max_length=16000)
    requirements: str = Field(min_length=4, max_length=12000)
    category: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    work_mode: Literal["onsite", "hybrid", "remote"]
    level: Literal["intern", "fresher", "junior", "senior"] = "intern"
    salary_min: int | None = Field(default=None, ge=0, le=1000000000)
    salary_max: int | None = Field(default=None, ge=0, le=1000000000)
    deadline: date | None = None
    skills: list[str] = Field(default_factory=list, max_length=40)
    benefits: str = Field(default="", max_length=3000)
    experience: str = Field(default="", max_length=100)
    education: Literal["Không yêu cầu", "Sinh viên đại học/cao đẳng", "Sinh viên năm cuối", "Mới tốt nghiệp",
                       "Trung cấp trở lên", "Cao đẳng trở lên", "Đại học trở lên", "Thạc sĩ trở lên"] | None = None
    quantity: int | None = Field(default=None, ge=1, le=1000)
    working_hours: str = Field(default="", max_length=500)
    employment_schedule: Literal["part_time", "full_time"] | None = None
    address: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def bounds(self):
        if (self.salary_min is None) != (self.salary_max is None):
            raise ValueError("Nhập cả hai mức lương hoặc để cả hai trống")
        if self.salary_min is not None and self.salary_min > self.salary_max:
            raise ValueError("Mức lương tối thiểu lớn hơn tối đa")
        if any(not s.strip() or len(s)>100 for s in self.skills):
            raise ValueError("Tên kỹ năng không hợp lệ")
        return self

class ReviewInput(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(default="", max_length=2000)
