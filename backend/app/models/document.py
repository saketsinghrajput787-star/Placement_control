import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from app.db.session import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # csv, xlsx, xls, pdf, docx
    document_type = Column(String(100), nullable=False)  # Students, Companies, Shortlists, Rooms, Panels, etc.
    detected_type = Column(String(100), nullable=True)
    confidence_score = Column(Float, default=1.0)
    uploaded_by = Column(String(255), nullable=False, default="Coordinator")
    uploaded_by_user_id = Column(String(36), nullable=True)
    version = Column(Integer, default=1)
    status = Column(String(50), default="UPLOADED")  # UPLOADED, VALIDATED, IMPORTED, ERROR
    file_hash = Column(String(64), nullable=True)
    record_count = Column(Integer, default=0)
    valid_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    file_path = Column(String(500), nullable=True)
    raw_content_preview = Column(Text, default="[]")  # JSON string of preview rows
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), index=True, nullable=False)
    version_number = Column(Integer, nullable=False)
    record_count = Column(Integer, default=0)
    added_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    removed_count = Column(Integer, default=0)
    unchanged_count = Column(Integer, default=0)
    diff_summary = Column(Text, default="{}")  # JSON comparison with previous version
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DocumentImport(Base):
    __tablename__ = "document_imports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), index=True, nullable=False)
    status = Column(String(50), default="COMPLETED")
    imported_by = Column(String(255), nullable=False)
    imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    affected_entity_count = Column(Integer, default=0)
    triggered_replanning = Column(Boolean, default=False)
    schedule_version_id = Column(String(36), nullable=True)

class DocumentImportError(Base):
    __tablename__ = "document_import_errors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), index=True, nullable=False)
    row_number = Column(Integer, nullable=False)
    column_name = Column(String(100), nullable=True)
    error_type = Column(String(100), nullable=False)  # MISSING_VALUE, INVALID_FORMAT, DUPLICATE, INVALID_REF
    error_message = Column(Text, nullable=False)
    raw_value = Column(Text, nullable=True)
    raw_row_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
