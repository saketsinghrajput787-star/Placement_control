import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.db.session import Base

class PlacementSession(Base):
    __tablename__ = "placement_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, default="Default Placement Session")
    college_name = Column(String(255), nullable=False, default="University Placement Office")
    academic_year = Column(String(50), nullable=False, default="2025-2026")
    status = Column(String(50), nullable=False, default="ACTIVE") # ACTIVE, ARCHIVED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "college_name": self.college_name,
            "academic_year": self.academic_year,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
