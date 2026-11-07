from datetime import datetime
from typing import Literal
from pydantic import BaseModel,Field
class Invitation(BaseModel):
    application_id: int
    scheduled_at: datetime
    location: str=Field(min_length=2,max_length=255)
    note: str=Field(default="",max_length=2000)

class Reply(BaseModel):
    action: Literal["confirmed","declined","reschedule_requested"]
    message: str=Field(default="",max_length=2000)
