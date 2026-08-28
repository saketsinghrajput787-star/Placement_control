import json
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, require_role, get_current_session_id
from app.models.user import User
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, Shortlist
from app.models.resource import Room, Panel
from app.models.cancellation import InterviewCancellation
from app.scheduler.solver import TIME_SLOT_MAP
from app.schemas.schedule import (
    GenerateScheduleRequest, InterviewOut, ScheduleMetrics, ScheduleVersionOut, InterviewAuditMetadata
)
from app.services.schedule_service import ScheduleService
from app.services.event_service import EventService

router = APIRouter(prefix="/schedule", tags=["schedule"])

@router.post("/generate")
def generate_schedule(
    req: Optional[GenerateScheduleRequest] = None,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        max_time = req.max_solve_time_seconds if req else 30
        res = ScheduleService.generate_initial_schedule(
            db=db,
            placement_session_id=session_id,
            max_time_seconds=max_time
        )
        if res.get("status") == "BLOCKED":
            raise HTTPException(status_code=400, detail=res.get("message", "Schedule generation blocked due to missing input dataset pools."))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_schedule_to_baseline(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    """
    Restores all cancelled interviews back to SCHEDULED,
    clears all cancellation records, and restores all candidate shortlists.
    Never wipes or drops existing interviews.
    """
    try:
        # 1. Clear all cancellation records
        db.query(InterviewCancellation).filter(InterviewCancellation.placement_session_id == session_id).delete()
        
        # 2. Reset all shortlists to active
        db.query(Shortlist).filter(Shortlist.placement_session_id == session_id).update({"status": "SHORTLISTED"})
        
        # 3. Reset withdrawn students
        db.query(Student).filter(Student.placement_session_id == session_id).update({"is_withdrawn": False})

        # 4. Find Version 1 (Immutable Baseline) and Latest Version
        v1 = db.query(ScheduleVersion).filter(
            ScheduleVersion.placement_session_id == session_id
        ).order_by(ScheduleVersion.version_number.asc()).first()

        latest_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.placement_session_id == session_id
        ).order_by(ScheduleVersion.version_number.desc()).first()

        if not v1:
            # If no version exists, generate baseline version 1
            ScheduleService.generate_initial_schedule(db=db, placement_session_id=session_id, max_time_seconds=10)
            v1 = db.query(ScheduleVersion).filter(
                ScheduleVersion.placement_session_id == session_id
            ).order_by(ScheduleVersion.version_number.asc()).first()
            latest_version = v1

        # 5. Get original baseline interviews from Version 1
        v1_interviews = db.query(Interview).filter(
            Interview.placement_session_id == session_id,
            Interview.schedule_version_id == v1.id
        ).all()

        if not v1_interviews and latest_version:
            v1_interviews = db.query(Interview).filter(
                Interview.placement_session_id == session_id,
                Interview.schedule_version_id == latest_version.id
            ).all()

        # Create a new version restoring baseline
        new_version_num = (latest_version.version_number + 1) if latest_version else 1
        new_version = ScheduleVersion(
            id=str(uuid.uuid4()),
            placement_session_id=session_id,
            schedule_id=latest_version.schedule_id if latest_version else str(uuid.uuid4()),
            version_number=new_version_num,
            stability_score=100.0,
            metrics_snapshot=v1.metrics_snapshot if v1 else "{}"
        )
        db.add(new_version)
        db.flush()

        for iv in v1_interviews:
            db_iv = Interview(
                id=str(uuid.uuid4()),
                placement_session_id=session_id,
                schedule_version_id=new_version.id,
                student_id=iv.student_id,
                company_id=iv.company_id,
                room_id=iv.room_id,
                panel_id=iv.panel_id,
                day_number=iv.day_number,
                slot_index=iv.slot_index,
                start_time_str=iv.start_time_str,
                end_time_str=iv.end_time_str,
                status="SCHEDULED",
                audit_metadata=json.dumps({"replan_reason": None})
            )
            db.add(db_iv)

        db.commit()

        # 7. Broadcast live update
        await EventService.broadcast_live_event({
            "type": "SCHEDULE_UPDATED",
            "placement_session_id": session_id,
            "message": "All cancellations restored to scheduled status."
        })

        return {
            "status": "SUCCESS",
            "message": "All cancelled interviews successfully restored to scheduled status.",
            "version_number": latest_version.version_number
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset cancellations: {str(e)}")

@router.post("/reinstate-interview")
async def reinstate_interview(
    student_id: str = Body(..., embed=True),
    company_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    """
    Reinstates or schedules a cancelled / unscheduled interview for the student and company.
    """
    try:
        # Resolve target student
        st = db.query(Student).filter(
            Student.placement_session_id == session_id,
            (Student.id == student_id) | (Student.user_id == student_id) | (Student.student_code == student_id)
        ).first()
        if not st:
            raise HTTPException(status_code=404, detail="Student not found")

        comp = db.query(Company).filter(
            Company.placement_session_id == session_id,
            (Company.id == company_id) | (Company.company_code == company_id)
        ).first()
        if not comp:
            raise HTTPException(status_code=404, detail="Company not found")

        # 1. Clear cancellations for this pair
        db.query(InterviewCancellation).filter(
            InterviewCancellation.placement_session_id == session_id,
            InterviewCancellation.student_id == st.id,
            InterviewCancellation.company_id == comp.id
        ).delete()

        # 2. Set Shortlist to SHORTLISTED
        sh = db.query(Shortlist).filter(
            Shortlist.placement_session_id == session_id,
            Shortlist.student_id == st.id,
            Shortlist.company_id == comp.id
        ).first()
        if sh:
            sh.status = "SHORTLISTED"
        else:
            sh = Shortlist(
                id=str(uuid.uuid4()),
                placement_session_id=session_id,
                student_id=st.id,
                company_id=comp.id,
                preference_rank=1,
                status="SHORTLISTED"
            )
            db.add(sh)

        # 3. Get latest schedule version
        latest_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.placement_session_id == session_id
        ).order_by(ScheduleVersion.version_number.desc()).first()
        if not latest_version:
            raise HTTPException(status_code=400, detail="No active schedule version found. Please generate schedule first.")

        # Check existing interviews in latest version
        current_ivs = db.query(Interview).filter(
            Interview.placement_session_id == session_id,
            Interview.schedule_version_id == latest_version.id
        ).all()

        existing_st_iv = next((iv for iv in current_ivs if iv.student_id == st.id and iv.company_id == comp.id), None)
        
        # Find busy slots for student, company panels, and rooms
        busy_student_slots = {iv.slot_index for iv in current_ivs if iv.student_id == st.id and iv.status != "CANCELLED"}
        panels = db.query(Panel).filter(Panel.placement_session_id == session_id, Panel.company_id == comp.id, Panel.is_active == True).all()
        rooms = db.query(Room).filter(Room.placement_session_id == session_id, Room.is_active == True).all()
        
        assigned_slot = None
        assigned_room = None
        assigned_panel = None

        for slot_idx in range(12):
            if slot_idx in busy_student_slots:
                continue
            # Check panel availability in this slot
            for p in panels:
                p_busy = any(iv.slot_index == slot_idx and iv.panel_id == p.id and iv.status != "CANCELLED" for iv in current_ivs)
                if not p_busy:
                    # Check room availability
                    for r in rooms:
                        r_busy = any(iv.slot_index == slot_idx and iv.room_id == r.id and iv.status != "CANCELLED" for iv in current_ivs)
                        if not r_busy:
                            assigned_slot = slot_idx
                            assigned_panel = p
                            assigned_room = r
                            break
                if assigned_slot is not None:
                    break
            if assigned_slot is not None:
                break

        if assigned_slot is None:
            # Fallback to default panel/room if fully booked
            assigned_slot = 0
            assigned_panel = panels[0] if panels else None
            assigned_room = rooms[0] if rooms else None

        times = TIME_SLOT_MAP.get(assigned_slot, ("09:00", "09:45"))

        # Create new schedule version
        new_version = ScheduleVersion(
            id=str(uuid.uuid4()),
            placement_session_id=session_id,
            schedule_id=latest_version.schedule_id,
            version_number=latest_version.version_number + 1,
            stability_score=latest_version.stability_score,
            metrics_snapshot=latest_version.metrics_snapshot
        )
        db.add(new_version)
        db.flush()

        # Copy all other interviews to new version
        for iv in current_ivs:
            if iv.student_id == st.id and iv.company_id == comp.id:
                continue
            db.add(Interview(
                id=str(uuid.uuid4()),
                placement_session_id=session_id,
                schedule_version_id=new_version.id,
                student_id=iv.student_id,
                company_id=iv.company_id,
                room_id=iv.room_id,
                panel_id=iv.panel_id,
                day_number=iv.day_number,
                slot_index=iv.slot_index,
                start_time_str=iv.start_time_str,
                end_time_str=iv.end_time_str,
                status=iv.status,
                audit_metadata=iv.audit_metadata
            ))

        # Add newly scheduled / restored interview
        new_iv = Interview(
            id=str(uuid.uuid4()),
            placement_session_id=session_id,
            schedule_version_id=new_version.id,
            student_id=st.id,
            company_id=comp.id,
            room_id=assigned_room.id if assigned_room else "",
            panel_id=assigned_panel.id if assigned_panel else "",
            day_number=1,
            slot_index=assigned_slot,
            start_time_str=times[0],
            end_time_str=times[1],
            status="SCHEDULED",
            audit_metadata=json.dumps({
                "assignment_reason": f"Manually scheduled/reinstated interview for candidate {st.student_code} with {comp.name}",
                "replan_reason": "Interview restored to active status"
            })
        )
        db.add(new_iv)
        db.commit()

        await EventService.broadcast_live_event({
            "type": "SCHEDULE_UPDATED",
            "placement_session_id": session_id,
            "message": f"Interview for {st.name} ({st.student_code}) with {comp.name} scheduled at {times[0]} in Room {assigned_room.room_code if assigned_room else 'R01'}."
        })

        return {
            "status": "SUCCESS",
            "message": f"Interview scheduled at {times[0]} in Room {assigned_room.room_code if assigned_room else 'R01'}.",
            "new_version_number": new_version.version_number,
            "interview_id": new_iv.id,
            "start_time_str": times[0],
            "room_code": assigned_room.room_code if assigned_room else "R01",
            "panel_code": assigned_panel.panel_code if assigned_panel else "P1"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
def get_latest_schedule(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    latest_version = db.query(ScheduleVersion).filter(
        ScheduleVersion.placement_session_id == session_id
    ).order_by(ScheduleVersion.version_number.desc()).first()

    if not latest_version:
        return {
            "version_number": 0,
            "metrics": ScheduleMetrics().dict(),
            "interviews": []
        }

    interviews = db.query(Interview).filter(Interview.schedule_version_id == latest_version.id).all()
    students = {s.id: s for s in db.query(Student).filter(Student.placement_session_id == session_id).all()}
    companies = {c.id: c for c in db.query(Company).filter(Company.placement_session_id == session_id).all()}
    rooms = {r.id: r for r in db.query(Room).filter(Room.placement_session_id == session_id).all()}
    panels = {p.id: p for p in db.query(Panel).filter(Panel.placement_session_id == session_id).all()}

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
def get_schedule_versions(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    versions = db.query(ScheduleVersion).filter(
        ScheduleVersion.placement_session_id == session_id
    ).order_by(ScheduleVersion.version_number.desc()).all()
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
def get_schedule_version(
    id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    v = db.query(ScheduleVersion).filter(
        ScheduleVersion.id == id,
        ScheduleVersion.placement_session_id == session_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Schedule version not found")

    iv_outs = list_interviews(version_id=v.id, db=db, session_id=session_id)
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
def get_schedule_version_diff(
    id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id)
):
    v = db.query(ScheduleVersion).filter(
        ScheduleVersion.id == id,
        ScheduleVersion.placement_session_id == session_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Schedule version not found")

    prev_v = db.query(ScheduleVersion).filter(
        ScheduleVersion.placement_session_id == session_id,
        ScheduleVersion.version_number < v.version_number
    ).order_by(ScheduleVersion.version_number.desc()).first()
    
    replan_run = db.query(ReplanningRun).filter(
        ReplanningRun.placement_session_id == session_id,
        ReplanningRun.resulting_version_id == v.id
    ).first()

    changes = []
    if replan_run:
        sc_list = db.query(ScheduleChange).filter(ScheduleChange.replanning_run_id == replan_run.id).all()
        students = {s.id: s for s in db.query(Student).filter(Student.placement_session_id == session_id).all()}
        companies = {c.id: c for c in db.query(Company).filter(Company.placement_session_id == session_id).all()}
        rooms = {r.id: r for r in db.query(Room).filter(Room.placement_session_id == session_id).all()}
        panels = {p.id: p for p in db.query(Panel).filter(Panel.placement_session_id == session_id).all()}

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
        students = {s.id: s for s in db.query(Student).filter(Student.placement_session_id == session_id).all()}
        companies = {c.id: c for c in db.query(Company).filter(Company.placement_session_id == session_id).all()}
        rooms = {r.id: r for r in db.query(Room).filter(Room.placement_session_id == session_id).all()}
        panels = {p.id: p for p in db.query(Panel).filter(Panel.placement_session_id == session_id).all()}

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
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    if not version_id:
        latest = db.query(ScheduleVersion).filter(
            ScheduleVersion.placement_session_id == session_id
        ).order_by(ScheduleVersion.version_number.desc()).first()
        if not latest:
            return []
        version_id = latest.id

    # Flexible target student resolution
    target_student_id = student_id
    if student_id:
        st_match = db.query(Student).filter(
            Student.placement_session_id == session_id,
            (Student.id == student_id) | (Student.user_id == student_id) | (Student.student_code == student_id)
        ).first()
        if st_match:
            target_student_id = st_match.id

    query = db.query(Interview).filter(
        Interview.schedule_version_id == version_id,
        Interview.placement_session_id == session_id
    )
    if target_student_id:
        query = query.filter(Interview.student_id == target_student_id)
    if company_id:
        query = query.filter(Interview.company_id == company_id)
    if room_id:
        query = query.filter(Interview.room_id == room_id)
    if panel_id:
        query = query.filter(Interview.panel_id == panel_id)
    if slot_index is not None:
        query = query.filter(Interview.slot_index == slot_index)

    interviews = query.order_by(Interview.slot_index).all()

    # Query cancellations scoped by target_student_id or company_id if provided
    canc_query = db.query(InterviewCancellation).filter(
        InterviewCancellation.placement_session_id == session_id
    )
    if target_student_id:
        canc_query = canc_query.filter(InterviewCancellation.student_id == target_student_id)
    if company_id:
        canc_query = canc_query.filter(InterviewCancellation.company_id == company_id)
    
    cancellations = canc_query.all()
    cancelled_map = {(c.student_id, c.company_id): c for c in cancellations}

    all_students = db.query(Student).filter(Student.placement_session_id == session_id).all()
    students = {}
    for s in all_students:
        students[s.id] = s
        if s.student_code:
            students[s.student_code] = s
        if s.user_id:
            students[s.user_id] = s

    all_companies = db.query(Company).filter(Company.placement_session_id == session_id).all()
    companies = {}
    for c in all_companies:
        companies[c.id] = c
        if c.company_code:
            companies[c.company_code] = c

    rooms = {r.id: r for r in db.query(Room).filter(Room.placement_session_id == session_id).all()}
    panels = {p.id: p for p in db.query(Panel).filter(Panel.placement_session_id == session_id).all()}

    results = []
    seen_cancelled_keys = set()

    for iv in interviews:
        s = students.get(iv.student_id)
        c = companies.get(iv.company_id)
        r = rooms.get(iv.room_id)
        p = panels.get(iv.panel_id)
        audit_meta = json.loads(iv.audit_metadata) if iv.audit_metadata else {}

        current_status = iv.status
        if (iv.student_id, iv.company_id) in cancelled_map:
            canc = cancelled_map[(iv.student_id, iv.company_id)]
            if iv.slot_index == canc.slot_index or iv.status == "CANCELLED":
                current_status = "CANCELLED"
                audit_meta["cancellation_reason"] = canc.reason
                if canc.comment:
                    audit_meta["comment"] = canc.comment
                if canc.cancelled_by_role:
                    audit_meta["cancelled_by_role"] = canc.cancelled_by_role
                seen_cancelled_keys.add((iv.student_id, iv.company_id))

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
            status=current_status,
            audit_metadata=InterviewAuditMetadata(**audit_meta) if audit_meta else None
        ))

    # Ensure any cancellation record not present in version is appended
    for (cand_s_id, cand_c_id), canc in cancelled_map.items():
        if (cand_s_id, cand_c_id) not in seen_cancelled_keys:
            s = students.get(cand_s_id)
            c = companies.get(cand_c_id)
            if s and c:
                r = rooms.get(canc.freed_room_id)
                p = panels.get(canc.freed_panel_id)
                times = TIME_SLOT_MAP.get(canc.slot_index, ("12:45", "13:30"))
                results.append(InterviewOut(
                    id=f"canc-{canc.id}",
                    schedule_version_id=version_id,
                    student_id=cand_s_id,
                    student_code=s.student_code,
                    student_name=s.name,
                    student_branch=s.branch,
                    student_cgpa=s.cgpa,
                    company_id=cand_c_id,
                    company_name=c.name,
                    company_tier=c.priority_tier,
                    room_id=canc.freed_room_id or (r.id if r else ""),
                    room_code=r.room_code if r else "R15",
                    panel_id=canc.freed_panel_id or (p.id if p else ""),
                    panel_code=p.panel_code if p else "P1",
                    day_number=canc.day_number,
                    slot_index=canc.slot_index,
                    start_time_str=times[0],
                    end_time_str=times[1],
                    status="CANCELLED",
                    audit_metadata=InterviewAuditMetadata(cancellation_reason=canc.reason, comment=canc.comment)
                ))
                seen_cancelled_keys.add((cand_s_id, cand_c_id))

    # Ensure all candidate shortlisted companies are included for student view
    if target_student_id:
        student_shortlists = db.query(Shortlist).filter(
            Shortlist.placement_session_id == session_id,
            Shortlist.student_id == target_student_id
        ).all()
        existing_company_ids = {res.company_id for res in results}
        
        for sh in student_shortlists:
            if sh.company_id not in existing_company_ids:
                s = students.get(target_student_id)
                c = companies.get(sh.company_id)
                if s and c:
                    is_withdrawn = sh.status == "WITHDRAWN"
                    results.append(InterviewOut(
                        id=f"unassigned-{sh.id}",
                        schedule_version_id=version_id,
                        student_id=target_student_id,
                        student_code=s.student_code,
                        student_name=s.name,
                        student_branch=s.branch,
                        student_cgpa=s.cgpa,
                        company_id=sh.company_id,
                        company_name=c.name,
                        company_tier=c.priority_tier,
                        room_id="",
                        room_code="TBD" if not is_withdrawn else "N/A",
                        panel_id="",
                        panel_code="TBD" if not is_withdrawn else "N/A",
                        day_number=1,
                        slot_index=0,
                        start_time_str="Pending" if not is_withdrawn else "Cancelled",
                        end_time_str="Slot Allocation" if not is_withdrawn else "Slot",
                        status="UNSCHEDULED" if not is_withdrawn else "CANCELLED",
                        audit_metadata=InterviewAuditMetadata(replan_reason="Shortlist application withdrawn" if is_withdrawn else "Awaiting slot allocation")
                    ))

    return results
