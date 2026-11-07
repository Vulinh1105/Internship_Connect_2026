from pydantic import BaseModel, Field

class CompanyInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    industry: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5, max_length=12000)
    benefits: str = Field(default="", max_length=3000)
