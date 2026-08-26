import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text
from app.db.session import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=False)
    student_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., S0421
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    branch = Column(String(50), index=True, nullable=False)  # CSE, ISE, ECE, MECH, etc.
    cgpa = Column(Float, nullable=False)
    graduation_year = Column(Integer, default=2026)
    skills = Column(Text, default="[]")  # JSON encoded list of skills
    is_active = Column(Boolean, default=True)
    is_withdrawn = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
