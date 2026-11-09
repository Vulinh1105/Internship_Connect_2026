from pydantic import BaseModel, Field

class Login(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

class Register(Login):
    name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)

class Activate(BaseModel):
    password: str = Field(min_length=10, max_length=128)

class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

class ForgotPassword(BaseModel):
    email: str = Field(min_length=3, max_length=255)

class ResetPassword(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)
