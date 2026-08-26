import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from app.db.session import Base

class Disruption(Base):
    __tablename__ = "disruptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False)  # COMPANY_DELAY, COMPANY_CANCELLATION, PANEL_UNAVAILABLE, ROOM_UNAVAILABLE, STUDENT_WITHDRAWAL, STUDENT_CANCELLED_INTERVIEW
    target_entity_type = Column(String(50), nullable=False)  # company, panel, room, student
    target_entity_id = Column(String(36), nullable=False)
    severity = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    parameters = Column(Text, default="{}")  # JSON: { delay_slots: 3, affected_panel_ids: [...], withdrawn_student_ids: [...] }
    status = Column(String(50), default="SIMULATED")  # SIMULATED, APPLIED, DISCARDED
    reported_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ReplanningRun(Base):
    __tablename__ = "replanning_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    disruption_id = Column(String(36), ForeignKey("disruptions.id"), index=True, nullable=False)
    source_version_id = Column(String(36), ForeignKey("schedule_versions.id"), index=True, nullable=False)
    resulting_version_id = Column(String(36), ForeignKey("schedule_versions.id"), index=True, nullable=True)
    strategy_type = Column(String(50), nullable=False)  # STUDENT_FIRST, BALANCED, STABILITY_FIRST
    strategy_score = Column(Float, default=0.0)
    stability_score = Column(Float, default=100.0)
    metrics = Column(Text, default="{}")  # JSON: { moved: 38, unchanged: 1757, cancelled: 0, new: 0, waiting_time_level: "Medium" }
    is_selected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ScheduleChange(Base):
    __tablename__ = "schedule_changes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    replanning_run_id = Column(String(36), ForeignKey("replanning_runs.id"), index=True, nullable=False)
    student_id = Column(String(36), ForeignKey("students.id"), index=True, nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), index=True, nullable=False)
    change_type = Column(String(50), nullable=False)  # UNCHANGED, MOVED, CANCELLED, NEW
    old_slot_index = Column(Integer, nullable=True)
    new_slot_index = Column(Integer, nullable=True)
    old_time_str = Column(String(10), nullable=True)
    new_time_str = Column(String(10), nullable=True)
    old_room_id = Column(String(36), nullable=True)
    new_room_id = Column(String(36), nullable=True)
    old_panel_id = Column(String(36), nullable=True)
    new_panel_id = Column(String(36), nullable=True)
    reason = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="SCHEDULE_CHANGE")  # SCHEDULE_CHANGE, DISRUPTION, BOTTLENECK, ALERT, DOCUMENT
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(String(36), nullable=True)
    schedule_version_id = Column(String(36), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)  # STUDENT_CANCELLED_INTERVIEW, COMPANY_DELAY_REPORTED, DOCUMENT_IMPORTED, etc.
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    before_state = Column(Text, default="{}")
    after_state = Column(Text, default="{}")
    reason = Column(String(500), nullable=True)
    trigger_event = Column(String(100), nullable=True)
    schedule_version_id = Column(String(36), nullable=True)
    details = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    payload = Column(Text, default="{}")  # JSON string
    created_by_user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
