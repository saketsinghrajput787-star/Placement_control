import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from app.db.session import Base

class InterviewCancellation(Base):
    __tablename__ = "interview_cancellations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id = Column(String(36), ForeignKey("interviews.id"), index=True, nullable=False)
    schedule_version_id = Column(String(36), ForeignKey("schedule_versions.id"), index=True, nullable=False)
    student_id = Column(String(36), ForeignKey("students.id"), index=True, nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), index=True, nullable=False)
    freed_room_id = Column(String(36), nullable=True)
    freed_panel_id = Column(String(36), nullable=True)
    slot_index = Column(Integer, nullable=False)
    day_number = Column(Integer, default=1)
    reason = Column(String(255), nullable=False)  # Personal reason, Accepted another opportunity, etc.
    comment = Column(Text, nullable=True)
    cancelled_by_role = Column(String(50), default="STUDENT")  # STUDENT, COMPANY, COORDINATOR
    cancelled_by_user_id = Column(String(36), nullable=False)
    resulting_schedule_version_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
