from typing import List, Optional
from pydantic import BaseModel, EmailStr

class StudentBase(BaseModel):
    student_code: str
    name: str
    email: EmailStr
    branch: str
    cgpa: float
    graduation_year: int = 2026
    skills: List[str] = []
    is_active: bool = True
    is_withdrawn: bool = False

class StudentCreate(StudentBase):
    password: Optional[str] = "student123"

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    skills: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_withdrawn: Optional[bool] = None

class StudentOut(StudentBase):
    id: str
    user_id: str

    class Config:
        from_attributes = True

class StudentWithShortlists(StudentOut):
    shortlisted_companies: List[str] = []
    interview_count: int = 0
