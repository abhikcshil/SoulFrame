from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime


class UserSignup(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID4
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True