import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from app.db.session import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    user_id = Column(String(36), index=True, nullable=True)
    student_code = Column(String(50), index=True, nullable=False)  # e.g., S0421
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    branch = Column(String(50), index=True, nullable=False)  # CSE, ISE, ECE, MECH, etc.
    cgpa = Column(Float, nullable=False)
    graduation_year = Column(Integer, default=2026)
    skills = Column(Text, default="[]")  # JSON encoded list of skills
    is_active = Column(Boolean, default=True)
    is_withdrawn = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "placement_session_id": self.placement_session_id,
            "student_code": self.student_code,
            "name": self.name,
            "email": self.email,
            "branch": self.branch,
            "cgpa": self.cgpa,
            "graduation_year": self.graduation_year,
            "is_active": self.is_active,
            "is_withdrawn": self.is_withdrawn
        }
