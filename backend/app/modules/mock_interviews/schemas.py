from typing import Literal
from pydantic import BaseModel, Field, StringConstraints, model_validator
from typing import Annotated

class Start(BaseModel):
    role: str | None = Field(default=None,min_length=1,max_length=100)
    question_set_id: int | None = Field(default=None,gt=0)
    job_id: int | None = None
    level: Literal["intern","fresher","junior"] | None = None

    @model_validator(mode="after")
    def source(self):
        if (self.role is None)==(self.question_set_id is None):
            raise ValueError("Chọn một vai trò hoặc một bộ câu hỏi doanh nghiệp")
        return self

class Submit(BaseModel):
    cursor: int = Field(ge=0)
    turn: int = Field(ge=0,le=1)
    transcript: str = Field(default="",max_length=5000)
    confirmed: bool = False
    skip: bool = False


class TurnCursor(BaseModel):
    cursor: int = Field(ge=0)
    turn: int = Field(ge=0,le=1)


class CompanyQuestion(BaseModel):
    question: Annotated[str,StringConstraints(strip_whitespace=True,min_length=5,max_length=350)]
    kind: Literal["knowledge","problem_solving","both"]
    difficulty: Literal["basic","intermediate","advanced"]
    criteria: str = Field(default="",max_length=600)
    guidance: str = Field(default="",max_length=1000)


class QuestionSetInput(BaseModel):
    job_id: int | None = Field(default=None,gt=0)
    company_id: int | None = Field(default=None,gt=0)
    position_title: Annotated[str,StringConstraints(strip_whitespace=True,min_length=2,max_length=200)] | None = None
    title: Annotated[str,StringConstraints(strip_whitespace=True,min_length=2,max_length=160)]
    description: str = Field(default="",max_length=2000)
    published: bool = False
    questions: list[CompanyQuestion] = Field(min_length=1,max_length=20)


    @model_validator(mode="after")
    def position(self):
        if self.job_id is None and (self.company_id is None or not self.position_title):
            raise ValueError("Nhập tên vị trí và chọn doanh nghiệp")
        return self
