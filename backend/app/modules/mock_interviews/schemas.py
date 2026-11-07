from pydantic import BaseModel, Field

class Start(BaseModel):
    role: str = Field(min_length=1,max_length=100)
    job_id: int | None = None

class Submit(BaseModel):
    cursor: int = Field(ge=0)
    turn: int = Field(ge=0,le=1)
    transcript: str = Field(default="",max_length=5000)
    confirmed: bool = False
    skip: bool = False
