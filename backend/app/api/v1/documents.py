import json
import csv
import io
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_session_id
from app.models.document import Document, DocumentVersion, DocumentImport, DocumentImportError
from app.services.document_service import DocumentService, CATEGORIES
from app.services.event_service import EventService

router = APIRouter(prefix="/documents", tags=["documents"])

def format_dt(dt):
    if not dt:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    uploaded_by: str = Form("Coordinator"),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 1. Parse file content
    columns, rows = DocumentService.parse_file_content(file.filename, content)
    
    # 2. Auto-detect category & confidence if not provided
    detected_cat, confidence = DocumentService.detect_category(columns, file.filename)
    final_doc_type = document_type if document_type and document_type in CATEGORIES else detected_cat

    # Check if prior version exists for this filename in this placement session
    existing_doc = db.query(Document).filter(
        Document.placement_session_id == session_id,
        Document.filename == file.filename
    ).order_by(Document.version.desc()).first()
    version_num = (existing_doc.version + 1) if existing_doc else 1

    # 3. Create document record
    doc = Document(
        placement_session_id=session_id,
        filename=file.filename,
        file_type=file.filename.split(".")[-1].lower(),
        document_type=final_doc_type,
        detected_type=detected_cat,
        confidence_score=confidence,
        uploaded_by=uploaded_by,
        version=version_num,
        status="UPLOADED",
        file_hash=file_hash,
        record_count=len(rows),
        raw_content_preview=json.dumps(rows)
    )
    db.add(doc)
    db.flush()

    # 4. Perform validation check
    val_res = DocumentService.validate_document_data(db, final_doc_type, columns, rows, placement_session_id=session_id)
    doc.valid_count = val_res["valid_count"]
    doc.warning_count = val_res["warning_count"]
    doc.error_count = val_res["error_count"]
    if doc.error_count > 0:
        doc.status = "VALIDATION_FAILED"
    else:
        doc.status = "VALIDATED"

    # Save import error records
    for err in val_res["errors"]:
        imp_err = DocumentImportError(
            placement_session_id=session_id,
            document_id=doc.id,
            row_number=err["row_number"],
            column_name=err["column_name"],
            error_type=err["error_type"],
            error_message=err["error_message"],
            raw_value=err.get("raw_value", ""),
            raw_row_data=err["raw_row_data"]
        )
        db.add(imp_err)

    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "placement_session_id": session_id,
        "filename": doc.filename,
        "document_type": doc.document_type,
        "detected_type": doc.detected_type,
        "confidence_score": doc.confidence_score,
        "version": doc.version,
        "record_count": doc.record_count,
        "valid_count": doc.valid_count,
        "warning_count": doc.warning_count,
        "error_count": doc.error_count,
        "status": doc.status,
        "columns": columns,
        "preview": rows[:5],
        "errors": val_res["errors"]
    }

@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    docs = db.query(Document).filter(Document.placement_session_id == session_id).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "document_type": d.document_type,
            "detected_type": d.detected_type,
            "confidence_score": d.confidence_score,
            "uploaded_by": d.uploaded_by,
            "version": d.version,
            "status": d.status,
            "record_count": d.record_count,
            "valid_count": d.valid_count,
            "error_count": d.error_count,
            "created_at": format_dt(d.created_at)
        }
        for d in docs
    ]

@router.get("/{id}")
def get_document(
    id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    doc = db.query(Document).filter(Document.id == id, Document.placement_session_id == session_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    errors = db.query(DocumentImportError).filter(DocumentImportError.document_id == doc.id).all()
    raw_preview = json.loads(doc.raw_content_preview) if doc.raw_content_preview else []
    columns = list(raw_preview[0].keys()) if raw_preview else []

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "document_type": doc.document_type,
        "detected_type": doc.detected_type,
        "confidence_score": doc.confidence_score,
        "uploaded_by": doc.uploaded_by,
        "version": doc.version,
        "status": doc.status,
        "record_count": doc.record_count,
        "valid_count": doc.valid_count,
        "warning_count": doc.warning_count,
        "error_count": doc.error_count,
        "columns": columns,
        "preview": raw_preview,
        "errors": [
            {
                "row_number": err.row_number,
                "column_name": err.column_name,
                "error_type": err.error_type,
                "error_message": err.error_message,
                "raw_value": err.raw_value
            }
            for err in errors
        ],
        "created_at": format_dt(doc.created_at)
    }

@router.post("/{id}/import")
async def import_document(
    id: str,
    import_mode: str = Query("REPLACE"),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    doc = db.query(Document).filter(Document.id == id, Document.placement_session_id == session_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.error_count > 0:
        raise HTTPException(status_code=400, detail="Cannot import document with validation errors. Please fix errors and re-upload.")

    raw_preview = json.loads(doc.raw_content_preview) if doc.raw_content_preview else []
    
    # 1. Compare and diff if prior versions exist
    diff_res = DocumentService.compare_and_diff(db, doc.id, raw_preview, placement_session_id=session_id)
    
    # 2. Persist data into ORM entities according to import mode
    import_summary = DocumentService.persist_imported_data(
        db,
        doc.document_type,
        raw_preview,
        placement_session_id=session_id,
        import_mode=import_mode
    )

    persisted_cnt = import_summary if isinstance(import_summary, int) else 0

    # 3. Create DocumentVersion record
    doc_ver = DocumentVersion(
        placement_session_id=session_id,
        document_id=doc.id,
        version_number=doc.version,
        record_count=doc.record_count,
        added_count=diff_res.get("added", 0),
        updated_count=diff_res.get("updated", 0),
        removed_count=diff_res.get("removed", 0),
        unchanged_count=diff_res.get("unchanged", 0),
        diff_summary=json.dumps(diff_res)
    )
    db.add(doc_ver)

    # 4. Create DocumentImport record
    doc_imp = DocumentImport(
        placement_session_id=session_id,
        document_id=doc.id,
        status="COMPLETED",
        imported_by=doc.uploaded_by,
        affected_entity_count=persisted_cnt
    )
    db.add(doc_imp)

    doc.status = "IMPORTED"
    db.commit()

    # Try auto-generating / updating schedule if pool conditions met
    try:
        from app.services.schedule_service import ScheduleService
        ScheduleService.generate_initial_schedule(db, placement_session_id=session_id, max_time_seconds=15)
    except Exception as e:
        print(f"Auto-schedule update note: {e}")

    # Broadcast live WebSocket event
    await EventService.broadcast_live_event({
        "type": "DOCUMENT_IMPORTED",
        "placement_session_id": session_id,
        "document_id": doc.id,
        "document_type": doc.document_type,
        "filename": doc.filename,
        "import_mode": import_mode,
        "version": doc.version,
        "persisted_count": persisted_cnt,
        "message": f"Dataset {doc.filename} ({doc.document_type}) imported & synchronized across portals."
    })

    return {
        "status": "SUCCESS",
        "document_id": doc.id,
        "version": doc.version,
        "import_mode": import_mode,
        "persisted_count": persisted_cnt,
        "diff_summary": diff_res
    }

@router.get("/{id}/error-report")
def download_error_report(
    id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    doc = db.query(Document).filter(Document.id == id, Document.placement_session_id == session_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    errors = db.query(DocumentImportError).filter(DocumentImportError.document_id == doc.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "Column Name", "Error Type", "Error Message", "Raw Value"])

    for err in errors:
        writer.writerow([
            err.row_number,
            err.column_name or "",
            err.error_type,
            err.error_message,
            err.raw_value or ""
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=error_report_{doc.filename}.csv"}
    )

@router.post("/sync-all")
async def sync_all_documents(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    try:
        from app.services.schedule_service import ScheduleService
        ScheduleService.generate_initial_schedule(db, placement_session_id=session_id, max_time_seconds=15)
    except Exception as e:
        print(f"Auto-schedule update note on sync: {e}")

    await EventService.broadcast_live_event({
        "type": "DATA_SYNCED",
        "placement_session_id": session_id,
        "message": "System data synchronized across all 3 portals (Coordinator, Company, Student)."
    })
    return {"status": "SUCCESS", "message": "System data synchronized across all 3 portals (Coordinator, Company, Student)." }

@router.post("/clear-all")
async def clear_all_documents(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    from app.models.student import Student
    from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
    from app.models.resource import Room, Panel
    from app.models.schedule import Schedule, ScheduleVersion, Interview
    from app.models.operations import Disruption, ReplanningRun

    try:
        scheds = db.query(Schedule).filter(Schedule.placement_session_id == session_id).all()
        for s in scheds:
            versions = db.query(ScheduleVersion).filter(ScheduleVersion.schedule_id == s.id).all()
            for v in versions:
                db.query(Interview).filter(Interview.schedule_version_id == v.id).delete(synchronize_session=False)
            db.query(ScheduleVersion).filter(ScheduleVersion.schedule_id == s.id).delete(synchronize_session=False)
        db.query(Schedule).filter(Schedule.placement_session_id == session_id).delete(synchronize_session=False)

        db.query(ReplanningRun).filter(ReplanningRun.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Disruption).filter(Disruption.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Shortlist).filter(Shortlist.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Panel).filter(Panel.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Room).filter(Room.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(CompanyAvailability).filter(CompanyAvailability.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(CompanyRequirements).filter(CompanyRequirements.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Company).filter(Company.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Student).filter(Student.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(DocumentImportError).filter(DocumentImportError.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(DocumentImport).filter(DocumentImport.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(DocumentVersion).filter(DocumentVersion.placement_session_id == session_id).delete(synchronize_session=False)
        db.query(Document).filter(Document.placement_session_id == session_id).delete(synchronize_session=False)

        db.commit()

        await EventService.broadcast_live_event({
            "type": "DATA_CLEARED",
            "placement_session_id": session_id,
            "message": "All session data and dataset registries have been cleared."
        })

        return {"status": "SUCCESS", "message": "All session data successfully cleared."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear session data: {str(e)}")
