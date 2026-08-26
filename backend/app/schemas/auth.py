from typing import Optional
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    email: str
    entity_id: Optional[str] = None  # student_id or company_id if applicable
    name: Optional[str] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str
    role: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "STUDENT"

class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    name: Optional[str] = None
    entity_id: Optional[str] = None

    class Config:
        from_attributes = True
