from pydantic import BaseModel,Field
class DocumentInput(BaseModel):
    title: str=Field(min_length=3,max_length=220)
    content: str=Field(min_length=15,max_length=120000)
    topic: str=Field(default="FAQ",max_length=100)
