import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index, text
from app.db.session import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    name = Column(String(255), default="Placement Week 2026")
    academic_year = Column(String(50), default="2025-2026")
    status = Column(String(50), default="ACTIVE")  # DRAFT, ACTIVE, ARCHIVED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number = Column(Integer, default=1)
    stability_score = Column(Float, default=100.0)
    metrics_snapshot = Column(Text, default="{}")  # JSON string of metrics
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    placement_session_id = Column(String(36), ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    schedule_version_id = Column(String(36), ForeignKey("schedule_versions.id", ondelete="CASCADE"), index=True, nullable=False)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    panel_id = Column(String(36), ForeignKey("panels.id", ondelete="CASCADE"), index=True, nullable=False)
    day_number = Column(Integer, default=1)
    slot_index = Column(Integer, nullable=False)  # 0 to 11
    start_time_str = Column(String(10), nullable=False)  # "09:00"
    end_time_str = Column(String(10), nullable=False)    # "09:45"
    status = Column(String(50), default="SCHEDULED")    # SCHEDULED, COMPLETED, CANCELLED, RESCHEDULED
    audit_metadata = Column(Text, default="{}")        # JSON explainability data: reasons, constraints checked, alternatives
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("uq_sched_student_slot", "schedule_version_id", "student_id", "slot_index", "day_number", unique=True, sqlite_where=text("status != 'CANCELLED'"), postgresql_where=text("status != 'CANCELLED'")),
        Index("uq_sched_room_slot", "schedule_version_id", "room_id", "slot_index", "day_number", unique=True, sqlite_where=text("status != 'CANCELLED'"), postgresql_where=text("status != 'CANCELLED'")),
        Index("uq_sched_panel_slot", "schedule_version_id", "panel_id", "slot_index", "day_number", unique=True, sqlite_where=text("status != 'CANCELLED'"), postgresql_where=text("status != 'CANCELLED'")),
    )
