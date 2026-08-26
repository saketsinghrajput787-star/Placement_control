import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company
from app.models.resource import Room, Panel
from app.models.operations import Notification, AuditLog, ScheduleChange, ReplanningRun
from app.schemas.schedule import (
    GenerateScheduleRequest, InterviewOut, ScheduleMetrics, ScheduleVersionOut, InterviewAuditMetadata
)
from app.services.schedule_service import ScheduleService
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/schedule", tags=["schedule"])

@router.post("/generate")
def generate_schedule(
    req: Optional[GenerateScheduleRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        max_time = req.max_solve_time_seconds if req else 30
        res = ScheduleService.generate_initial_schedule(db, max_time_seconds=max_time)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
def get_latest_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    latest_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
    if not latest_version:
        return {
            "version_number": 0,
            "metrics": ScheduleMetrics().dict(),
            "interviews": []
        }

    interviews = db.query(Interview).filter(Interview.schedule_version_id == latest_version.id).all()
    students = {s.id: s for s in db.query(Student).all()}
    companies = {c.id: c for c in db.query(Company).all()}
    rooms = {r.id: r for r in db.query(Room).all()}
    panels = {p.id: p for p in db.query(Panel).all()}

    iv_outs = []
    for iv in interviews:
        s = students.get(iv.student_id)
        c = companies.get(iv.company_id)
        r = rooms.get(iv.room_id)
        p = panels.get(iv.panel_id)

        audit_meta = json.loads(iv.audit_metadata) if iv.audit_metadata else {}

        iv_outs.append(InterviewOut(
            id=iv.id,
            schedule_version_id=iv.schedule_version_id,
            student_id=iv.student_id,
            student_code=s.student_code if s else "S0000",
            student_name=s.name if s else "Student",
            student_branch=s.branch if s else "CSE",
            student_cgpa=s.cgpa if s else 0.0,
            company_id=iv.company_id,
            company_name=c.name if c else "Company",
            company_tier=c.priority_tier if c else 1,
            room_id=iv.room_id,
            room_code=r.room_code if r else "R01",
            panel_id=iv.panel_id,
            panel_code=p.panel_code if p else "P1",
            day_number=iv.day_number,
            slot_index=iv.slot_index,
            start_time_str=iv.start_time_str,
            end_time_str=iv.end_time_str,
            status=iv.status,
            audit_metadata=InterviewAuditMetadata(**audit_meta) if audit_meta else None
        ))

    metrics_data = json.loads(latest_version.metrics_snapshot) if latest_version.metrics_snapshot else {}
    metrics = ScheduleMetrics(**metrics_data) if metrics_data else ScheduleMetrics()

    return {
        "schedule_version_id": latest_version.id,
        "version_number": latest_version.version_number,
        "stability_score": latest_version.stability_score,
        "created_at": latest_version.created_at.isoformat(),
        "metrics": metrics,
        "interviews": iv_outs
    }

@router.get("/versions")
def get_schedule_versions(db: Session = Depends(get_db)):
    versions = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).all()
    res = []
    for v in versions:
        m = json.loads(v.metrics_snapshot) if v.metrics_snapshot else {}
        res.append({
            "id": v.id,
            "version_number": v.version_number,
            "stability_score": v.stability_score,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "metrics": m
        })
    return res

@router.get("/versions/{id}")
def get_schedule_version(id: str, db: Session = Depends(get_db)):
    v = db.query(ScheduleVersion).get(id)
    if not v:
        raise HTTPException(status_code=404, detail="Schedule version not found")

    interviews = db.query(Interview).filter(Interview.schedule_version_id == v.id).all()
    students = {s.id: s for s in db.query(Student).all()}
    companies = {c.id: c for c in db.query(Company).all()}
    rooms = {r.id: r for r in db.query(Room).all()}
    panels = {p.id: p for p in db.query(Panel).all()}

    iv_outs = []
    for iv in interviews:
        s = students.get(iv.student_id)
        c = companies.get(iv.company_id)
        r = rooms.get(iv.room_id)
        p = panels.get(iv.panel_id)

        audit_meta = json.loads(iv.audit_metadata) if iv.audit_metadata else {}

        iv_outs.append(InterviewOut(
            id=iv.id,
            schedule_version_id=iv.schedule_version_id,
            student_id=iv.student_id,
            student_code=s.student_code if s else "S0000",
            student_name=s.name if s else "Student",
            student_branch=s.branch if s else "CSE",
            student_cgpa=s.cgpa if s else 0.0,
            company_id=iv.company_id,
            company_name=c.name if c else "Company",
            company_tier=c.priority_tier if c else 1,
            room_id=iv.room_id,
            room_code=r.room_code if r else "R01",
            panel_id=iv.panel_id,
            panel_code=p.panel_code if p else "P1",
            day_number=iv.day_number,
            slot_index=iv.slot_index,
            start_time_str=iv.start_time_str,
            end_time_str=iv.end_time_str,
            status=iv.status,
            audit_metadata=InterviewAuditMetadata(**audit_meta) if audit_meta else None
        ))

    metrics_data = json.loads(v.metrics_snapshot) if v.metrics_snapshot else {}
    return {
        "schedule_version_id": v.id,
        "version_number": v.version_number,
        "stability_score": v.stability_score,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "metrics": metrics_data,
        "interviews": iv_outs
    }

@router.get("/versions/{id}/diff")
def get_schedule_version_diff(id: str, db: Session = Depends(get_db)):
    v = db.query(ScheduleVersion).get(id)
    if not v:
        raise HTTPException(status_code=404, detail="Schedule version not found")

    # Find previous version
    prev_v = db.query(ScheduleVersion).filter(ScheduleVersion.version_number < v.version_number).order_by(ScheduleVersion.version_number.desc()).first()
    
    # Check if there is a replanning run resulting in this version
    replan_run = db.query(ReplanningRun).filter(ReplanningRun.resulting_version_id == v.id).first()
    changes = []
    if replan_run:
        sc_list = db.query(ScheduleChange).filter(ScheduleChange.replanning_run_id == replan_run.id).all()
        students = {s.id: s for s in db.query(Student).all()}
        companies = {c.id: c for c in db.query(Company).all()}
        rooms = {r.id: r for r in db.query(Room).all()}
        panels = {p.id: p for p in db.query(Panel).all()}

        for sc in sc_list:
            st = students.get(sc.student_id)
            comp = companies.get(sc.company_id)
            old_r = rooms.get(sc.old_room_id) if sc.old_room_id else None
            new_r = rooms.get(sc.new_room_id) if sc.new_room_id else None
            old_p = panels.get(sc.old_panel_id) if sc.old_panel_id else None
            new_p = panels.get(sc.new_panel_id) if sc.new_panel_id else None

            changes.append({
                "id": sc.id,
                "student_id": sc.student_id,
                "student_code": st.student_code if st else "Candidate",
                "student_name": st.name if st else "Student",
                "company_name": comp.name if comp else "Company",
                "change_type": sc.change_type,
                "old_time": sc.old_time_str or "N/A",
                "new_time": sc.new_time_str or "N/A",
                "old_room": old_r.room_code if old_r else "N/A",
                "new_room": new_r.room_code if new_r else "N/A",
                "old_panel": old_p.panel_code if old_p else "N/A",
                "new_panel": new_p.panel_code if new_p else "N/A",
                "reason": sc.reason
            })

    if not changes and prev_v:
        students = {s.id: s for s in db.query(Student).all()}
        companies = {c.id: c for c in db.query(Company).all()}
        rooms = {r.id: r for r in db.query(Room).all()}
        panels = {p.id: p for p in db.query(Panel).all()}

        curr_ivs = db.query(Interview).filter(Interview.schedule_version_id == v.id).all()
        prev_ivs = db.query(Interview).filter(Interview.schedule_version_id == prev_v.id).all()

        curr_map = {(iv.student_id, iv.company_id): iv for iv in curr_ivs if iv.status == "SCHEDULED"}
        prev_map = {(iv.student_id, iv.company_id): iv for iv in prev_ivs if iv.status == "SCHEDULED"}

        for (s_id, c_id), prev_iv in prev_map.items():
            st = students.get(s_id)
            comp = companies.get(c_id)
            old_r = rooms.get(prev_iv.room_id)
            old_p = panels.get(prev_iv.panel_id)

            if (s_id, c_id) in curr_map:
                curr_iv = curr_map[(s_id, c_id)]
                new_r = rooms.get(curr_iv.room_id)
                new_p = panels.get(curr_iv.panel_id)

                if (curr_iv.slot_index == prev_iv.slot_index and 
                    curr_iv.room_id == prev_iv.room_id and 
                    curr_iv.panel_id == prev_iv.panel_id):
                    changes.append({
                        "id": curr_iv.id,
                        "student_id": s_id,
                        "student_code": st.student_code if st else "Candidate",
                        "student_name": st.name if st else "Student",
                        "company_name": comp.name if comp else "Company",
                        "change_type": "UNCHANGED",
                        "old_time": prev_iv.start_time_str,
                        "new_time": curr_iv.start_time_str,
                        "old_room": old_r.room_code if old_r else "N/A",
                        "new_room": new_r.room_code if new_r else "N/A",
                        "old_panel": old_p.panel_code if old_p else "N/A",
                        "new_panel": new_p.panel_code if new_p else "N/A",
                        "reason": "Retained existing schedule slot"
                    })
                else:
                    changes.append({
                        "id": curr_iv.id,
                        "student_id": s_id,
                        "student_code": st.student_code if st else "Candidate",
                        "student_name": st.name if st else "Student",
                        "company_name": comp.name if comp else "Company",
                        "change_type": "MOVED",
                        "old_time": prev_iv.start_time_str,
                        "new_time": curr_iv.start_time_str,
                        "old_room": old_r.room_code if old_r else "N/A",
                        "new_room": new_r.room_code if new_r else "N/A",
                        "old_panel": old_p.panel_code if old_p else "N/A",
                        "new_panel": new_p.panel_code if new_p else "N/A",
                        "reason": f"Rescheduled: time {prev_iv.start_time_str} -> {curr_iv.start_time_str}"
                    })
            else:
                changes.append({
                    "id": prev_iv.id,
                    "student_id": s_id,
                    "student_code": st.student_code if st else "Candidate",
                    "student_name": st.name if st else "Student",
                    "company_name": comp.name if comp else "Company",
                    "change_type": "CANCELLED",
                    "old_time": prev_iv.start_time_str,
                    "new_time": "N/A",
                    "old_room": old_r.room_code if old_r else "N/A",
                    "new_room": "N/A",
                    "old_panel": old_p.panel_code if old_p else "N/A",
                    "new_panel": "N/A",
                    "reason": "Interview cancelled"
                })

        for (s_id, c_id), curr_iv in curr_map.items():
            if (s_id, c_id) not in prev_map:
                st = students.get(s_id)
                comp = companies.get(c_id)
                new_r = rooms.get(curr_iv.room_id)
                new_p = panels.get(curr_iv.panel_id)

                changes.append({
                    "id": curr_iv.id,
                    "student_id": s_id,
                    "student_code": st.student_code if st else "Candidate",
                    "student_name": st.name if st else "Student",
                    "company_name": comp.name if comp else "Company",
                    "change_type": "NEW",
                    "old_time": "N/A",
                    "new_time": curr_iv.start_time_str,
                    "old_room": "N/A",
                    "new_room": new_r.room_code if new_r else "N/A",
                    "old_panel": "N/A",
                    "new_panel": new_p.panel_code if new_p else "N/A",
                    "reason": "Newly assigned replacement slot"
                })

    moved_count = sum(1 for c in changes if c["change_type"] == "MOVED")
    cancelled_count = sum(1 for c in changes if c["change_type"] == "CANCELLED")
    unchanged_count = sum(1 for c in changes if c["change_type"] == "UNCHANGED")
    new_count = sum(1 for c in changes if c["change_type"] in ["NEW", "NEWLY_SCHEDULED"])

    return {
        "current_version": v.version_number,
        "previous_version": prev_v.version_number if prev_v else None,
        "stability_score": v.stability_score,
        "summary": {
            "moved": moved_count,
            "cancelled": cancelled_count,
            "unchanged": unchanged_count,
            "new": new_count
        },
        "changes": changes
    }

@router.get("/interviews", response_model=List[InterviewOut])
def list_interviews(
    student_id: Optional[str] = None,
    company_id: Optional[str] = None,
    room_id: Optional[str] = None,
    panel_id: Optional[str] = None,
    slot_index: Optional[int] = None,
    version_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not version_id:
        latest = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
        if not latest:
            return []
        version_id = latest.id

    query = db.query(Interview).filter(Interview.schedule_version_id == version_id)
    if student_id:
        query = query.filter(Interview.student_id == student_id)
    if company_id:
        query = query.filter(Interview.company_id == company_id)
    if room_id:
        query = query.filter(Interview.room_id == room_id)
    if panel_id:
        query = query.filter(Interview.panel_id == panel_id)
    if slot_index is not None:
        query = query.filter(Interview.slot_index == slot_index)

    interviews = query.order_by(Interview.slot_index).all()
    students = {s.id: s for s in db.query(Student).all()}
    companies = {c.id: c for c in db.query(Company).all()}
    rooms = {r.id: r for r in db.query(Room).all()}
    panels = {p.id: p for p in db.query(Panel).all()}

    results = []
    for iv in interviews:
        s = students.get(iv.student_id)
        c = companies.get(iv.company_id)
        r = rooms.get(iv.room_id)
        p = panels.get(iv.panel_id)
        audit_meta = json.loads(iv.audit_metadata) if iv.audit_metadata else {}

        results.append(InterviewOut(
            id=iv.id,
            schedule_version_id=iv.schedule_version_id,
            student_id=iv.student_id,
            student_code=s.student_code if s else "",
            student_name=s.name if s else "",
            student_branch=s.branch if s else "",
            student_cgpa=s.cgpa if s else 0.0,
            company_id=iv.company_id,
            company_name=c.name if c else "",
            company_tier=c.priority_tier if c else 1,
            room_id=iv.room_id,
            room_code=r.room_code if r else "",
            panel_id=iv.panel_id,
            panel_code=p.panel_code if p else "",
            day_number=iv.day_number,
            slot_index=iv.slot_index,
            start_time_str=iv.start_time_str,
            end_time_str=iv.end_time_str,
            status=iv.status,
            audit_metadata=InterviewAuditMetadata(**audit_meta) if audit_meta else None
        ))
    return results
