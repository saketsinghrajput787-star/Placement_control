import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from app.db.session import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    user_id = Column(String(36), index=True, nullable=True)
    company_code = Column(String(50), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), default="Technology")
    priority_tier = Column(Integer, default=1)  # 1 = Day 1, 2 = Day 2, etc.
    interview_duration_mins = Column(Integer, default=45)
    max_panels = Column(Integer, default=4)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CompanyRequirements(Base):
    __tablename__ = "company_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    min_cgpa = Column(Float, default=7.0)
    eligible_branches = Column(Text, default='["CSE","ISE","ECE"]')  # JSON list
    rounds_count = Column(Integer, default=1)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class CompanyAvailability(Base):
    __tablename__ = "company_availability"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    day_number = Column(Integer, default=1)
    start_time_slot = Column(Integer, default=0)  # Slot index 0 = 09:00, 1 = 09:45, etc.
    end_time_slot = Column(Integer, default=12)   # 12 slots for 09:00 - 18:00
    is_available = Column(Boolean, default=True)

class Shortlist(Base):
    __tablename__ = "shortlists"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False)
    preference_rank = Column(Integer, default=1)
    status = Column(String(50), default="SHORTLISTED")  # SHORTLISTED, SCHEDULED, COMPLETED, WITHDRAWN
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
