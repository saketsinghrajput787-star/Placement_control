import json
import csv
import io
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.document import Document, DocumentVersion, DocumentImport, DocumentImportError
from app.services.document_service import DocumentService, CATEGORIES
from app.services.event_service import EventService

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    uploaded_by: str = Form("Coordinator"),
    db: Session = Depends(get_db)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 1. Parse file content
    columns, rows = DocumentService.parse_file_content(file.filename, content)
    
    # 2. Auto-detect category & confidence if not provided
    detected_cat, confidence = DocumentService.detect_category(columns, file.filename)
    final_doc_type = document_type if document_type and document_type in CATEGORIES else detected_cat

    # Check if prior version exists for this filename
    existing_doc = db.query(Document).filter(Document.filename == file.filename).order_by(Document.version.desc()).first()
    version_num = (existing_doc.version + 1) if existing_doc else 1

    # 3. Create document record
    doc = Document(
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

    # 4. Perform instant validation check
    val_res = DocumentService.validate_document_data(db, final_doc_type, columns, rows)
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
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
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
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]

@router.get("/{id}")
def get_document(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    errors = db.query(DocumentImportError).filter(DocumentImportError.document_id == doc.id).all()
    return {
        "id": doc.id,
        "filename": doc.filename,
        "document_type": doc.document_type,
        "detected_type": doc.detected_type,
        "confidence_score": doc.confidence_score,
        "version": doc.version,
        "status": doc.status,
        "record_count": doc.record_count,
        "valid_count": doc.valid_count,
        "warning_count": doc.warning_count,
        "error_count": doc.error_count,
        "raw_content_preview": json.loads(doc.raw_content_preview) if doc.raw_content_preview else [],
        "errors": [
            {
                "row_number": e.row_number,
                "column_name": e.column_name,
                "error_type": e.error_type,
                "error_message": e.error_message,
                "raw_value": e.raw_value or "",
                "raw_row_data": e.raw_row_data or "{}"
            }
            for e in errors
        ]
    }

@router.post("/{id}/import")
async def import_document(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    rows = json.loads(doc.raw_content_preview or "[]")
    
    # Persist records into live database entities (Panels, Rooms, Companies, Students, Shortlists)
    persisted_count = DocumentService.persist_imported_data(db, doc.document_type, rows)

    # Trigger OR-Tools CP-SAT solver to recalculate live schedule version for new data
    try:
        from app.services.schedule_service import ScheduleService
        ScheduleService.generate_initial_schedule(db, max_time_seconds=10)
    except Exception as e:
        pass

    diff_res = DocumentService.compare_and_diff(db, doc.id, rows)
    
    doc_ver = DocumentVersion(
        document_id=doc.id,
        version_number=doc.version,
        record_count=doc.record_count,
        added_count=diff_res["added"],
        updated_count=diff_res["updated"],
        removed_count=diff_res["removed"],
        unchanged_count=diff_res["unchanged"],
        diff_summary=json.dumps(diff_res)
    )
    db.add(doc_ver)
    
    doc.status = "IMPORTED"
    
    imp_log = DocumentImport(
        document_id=doc.id,
        status="COMPLETED",
        imported_by=doc.uploaded_by,
        affected_entity_count=diff_res["added"] + diff_res["updated"]
    )
    db.add(imp_log)

    EventService.record_change_event(
        db,
        event_type="DATA_IMPORTED",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        payload={
            "filename": doc.filename,
            "document_type": doc.document_type,
            "version": doc.version,
            "diff": diff_res
        }
    )

    EventService.create_audit_log(
        db,
        action="DOCUMENT_IMPORTED",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        reason=f"Coordinator imported {doc.filename} ({doc.document_type})",
        trigger_event="DATA_IMPORTED",
        details=diff_res
    )

    db.commit()

    await EventService.broadcast_live_event({
        "type": "DATA_IMPORTED",
        "document_id": doc.id,
        "filename": doc.filename,
        "document_type": doc.document_type,
        "version": doc.version,
        "diff": diff_res,
        "message": f"New dataset imported: {doc.filename} ({doc.record_count} records)"
    })

    return {
        "status": "SUCCESS",
        "message": f"Successfully imported document {doc.filename}",
        "version": doc.version,
        "diff": diff_res
    }

@router.get("/{id}/error-report")
def download_error_report(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    errors = db.query(DocumentImportError).filter(DocumentImportError.document_id == doc.id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "Column Name", "Error Type", "Error Message", "Raw Value", "Raw Data"])
    
    for err in errors:
        writer.writerow([err.row_number, err.column_name or "", err.error_type, err.error_message, err.raw_value or "", err.raw_row_data or ""])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=error_report_{doc.filename}.csv"}
    )

@router.post("/clear-all")
async def clear_all_documents(db: Session = Depends(get_db)):
    """Purges all system data, entity tables, and uploaded document registries."""
    from app.models.student import Student
    from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
    from app.models.resource import Room, Panel
    from app.models.schedule import ScheduleVersion, Interview
    from app.models.user import User
    from app.models.operations import Disruption, ReplanningRun

    try:
        db.query(Interview).delete()
        db.query(ScheduleVersion).delete()
        db.query(ReplanningRun).delete()
        db.query(Disruption).delete()
        db.query(Shortlist).delete()
        db.query(Panel).delete()
        db.query(Room).delete()
        db.query(CompanyAvailability).delete()
        db.query(CompanyRequirements).delete()
        db.query(Company).delete()
        db.query(Student).delete()
        db.query(DocumentImportError).delete()
        db.query(DocumentImport).delete()
        db.query(DocumentVersion).delete()
        db.query(Document).delete()
        db.query(User).filter(User.role.in_(["STUDENT", "COMPANY"])).delete()

        db.commit()

        await EventService.broadcast_live_event({
            "type": "DATA_CLEARED",
            "message": "All system data and dataset registries have been cleared."
        })

        return {"status": "SUCCESS", "message": "All system data successfully cleared."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear system data: {str(e)}")

@router.post("/sync-all")
async def sync_all_documents(db: Session = Depends(get_db)):
    """Synchronizes and applies all currently imported datasets to active database entities and recalculates schedule."""
    try:
        docs = db.query(Document).filter(Document.status.in_(["IMPORTED", "VALIDATED"])).order_by(Document.created_at.desc()).all()
        latest_by_cat = {}
        for d in docs:
            if d.document_type not in latest_by_cat:
                latest_by_cat[d.document_type] = d

        persisted_summary = {}
        for cat in ["Students", "Companies", "Rooms", "Panels", "Shortlists", "Company Availability", "Student Availability"]:
            if cat in latest_by_cat:
                d = latest_by_cat[cat]
                rows = json.loads(d.raw_content_preview or "[]")
                cnt = DocumentService.persist_imported_data(db, cat, rows)
                d.status = "IMPORTED"
                persisted_summary[cat] = cnt

        # Auto-link shortlists if students & companies exist but no explicit shortlists uploaded
        from app.models.student import Student
        from app.models.company import Company
        from app.models.company import Shortlist
        studs = db.query(Student).all()
        comps = db.query(Company).all()
        if len(studs) > 0 and len(comps) > 0:
            if db.query(Shortlist).count() == 0:
                import uuid
                for comp in comps:
                    for stud in studs:
                        sh = Shortlist(
                            id=str(uuid.uuid4()),
                            company_id=comp.id,
                            student_id=stud.id,
                            preference_rank=1,
                            status="SHORTLISTED"
                        )
                        db.add(sh)
                db.commit()

        # Recalculate OR-Tools CP-SAT schedule
        sched_ver = None
        try:
            from app.services.schedule_service import ScheduleService
            res = ScheduleService.generate_initial_schedule(db, max_time_seconds=10)
            sched_ver = res.get("version_number")
        except Exception:
            pass

        db.commit()

        await EventService.broadcast_live_event({
            "type": "DATA_IMPORTED",
            "message": "System data synchronized across all portals."
        })

        return {
            "status": "SUCCESS",
            "message": "System data successfully synchronized and applied.",
            "summary": persisted_summary,
            "schedule_version": sched_ver
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync system data: {str(e)}")

