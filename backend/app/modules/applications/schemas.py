from typing import Literal
from pydantic import BaseModel,Field
class ApplyInput(BaseModel):
    job_id: int
    cv_id: int|None=None
    cover_letter: str=Field(default="",max_length=5000)

class Decision(BaseModel):
    status: Literal["reviewing","accepted","rejected","withdrawn"]
    reason: str=Field(default="",max_length=2000)
