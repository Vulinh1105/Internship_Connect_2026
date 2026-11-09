from pydantic import BaseModel, Field
from typing import Literal

class Preferences(BaseModel):
    target_category: str = Field(default="",max_length=100)
    preferred_location: str = Field(default="",max_length=100)
    preferred_work_mode: Literal["","onsite","remote","hybrid"] = ""
    salary_min: int|None=Field(default=None,ge=0,le=1000000000)
    level: Literal["intern","fresher","junior"] = "intern"

class ProfileInput(BaseModel):
    name: str=Field(min_length=2,max_length=150)
    major: str=Field(default="",max_length=150)
    summary: str=Field(default="",max_length=4000)
    skills: list[str]=Field(default_factory=list,max_length=40)
    preferences: Preferences=Field(default_factory=Preferences)
    school: str|None=Field(default=None,max_length=200)
    specialization: str|None=Field(default=None,max_length=150)
    study_year: int|None=Field(default=None,ge=1,le=10)
    skill_levels: dict[str,Literal["basic","intermediate","advanced"]]|None=Field(default=None,max_length=40)

class CVFacts(BaseModel):
    skills: list[str]=Field(default_factory=list,max_length=40)
    education: list[str]=Field(default_factory=list,max_length=15)
    experience: list[str]=Field(default_factory=list,max_length=15)
    projects: list[str]=Field(default_factory=list,max_length=15)
    certificates: list[str]=Field(default_factory=list,max_length=15)
    languages: list[str]=Field(default_factory=list,max_length=15)
