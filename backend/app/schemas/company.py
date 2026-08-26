from typing import List, Optional
from pydantic import BaseModel

class CompanyRequirementSchema(BaseModel):
    min_cgpa: float = 7.0
    eligible_branches: List[str] = ["CSE", "ISE", "ECE"]
    rounds_count: int = 1

class CompanyAvailabilitySchema(BaseModel):
    day_number: int = 1
    start_time_slot: int = 0
    end_time_slot: int = 12
    is_available: bool = True

class CompanyBase(BaseModel):
    company_code: str
    name: str
    industry: str = "Technology"
    priority_tier: int = 1
    interview_duration_mins: int = 45
    max_panels: int = 4
    is_active: bool = True

class CompanyCreate(CompanyBase):
    email: str
    password: Optional[str] = "company123"
    requirements: Optional[CompanyRequirementSchema] = None
    availability: Optional[List[CompanyAvailabilitySchema]] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    priority_tier: Optional[int] = None
    interview_duration_mins: Optional[int] = None
    max_panels: Optional[int] = None
    is_active: Optional[bool] = None

class CompanyOut(CompanyBase):
    id: str
    user_id: str
    requirements: Optional[CompanyRequirementSchema] = None
    availability: Optional[List[CompanyAvailabilitySchema]] = None
    panels_count: int = 0
    shortlisted_count: int = 0

    class Config:
        from_attributes = True

class ShortlistCreate(BaseModel):
    company_id: str
    student_id: str
    preference_rank: int = 1

class ShortlistBatchCreate(BaseModel):
    company_id: str
    student_ids: List[str]

class ShortlistOut(BaseModel):
    id: str
    company_id: str
    student_id: str
    student_code: str
    student_name: str
    student_branch: str
    student_cgpa: float
    preference_rank: int
    status: str

    class Config:
        from_attributes = True
