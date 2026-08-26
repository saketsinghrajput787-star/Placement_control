import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.db.session import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., R01, R02
    building = Column(String(100), default="Placement Block")
    floor = Column(Integer, default=1)
    capacity = Column(Integer, default=5)
    has_video_conf = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Panel(Base):
    __tablename__ = "panels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), index=True, nullable=False)
    panel_code = Column(String(50), index=True, nullable=False)  # e.g., P1, P2, P3
    interviewer_names = Column(String(255), default="Interviewer Panel")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "panel_code", name="uq_company_panel_code"),
    )

class InterviewSlot(Base):
    __tablename__ = "interview_slots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    day_number = Column(Integer, default=1)
    slot_index = Column(Integer, nullable=False)  # 0 to 11 (e.g. 09:00, 09:45, ...)
    start_time_str = Column(String(10), nullable=False)  # "09:00"
    end_time_str = Column(String(10), nullable=False)    # "09:45"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
