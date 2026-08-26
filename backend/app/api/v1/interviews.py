import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.student import Student
from app.models.company import Company
from app.models.schedule import Interview
from app.api.deps import get_current_user
from app.services.event_service import EventService
from app.services.cancellation_service import CancellationService

router = APIRouter(prefix="/interviews", tags=["interviews"])

@router.post("/{id}/cancel")
async def cancel_interview(
    id: str,
    reason: str = Body(..., embed=True),
    comment: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = db.query(Interview).get(id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Security check: if student, can only cancel own interview
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if current_user.role == "STUDENT":
        if not student or interview.student_id != student.id:
            raise HTTPException(status_code=403, detail="You can only cancel your own interviews")

    res = CancellationService.handle_student_cancellation(
        db=db,
        interview_id=id,
        reason=reason,
        comment=comment,
        current_user=current_user
    )

    company = db.query(Company).get(interview.company_id)

    # Broadcast live WebSocket event to ALL portals
    await EventService.broadcast_live_event({
        "type": "STUDENT_CANCELLED",
        "interview_id": interview.id,
        "student_id": interview.student_id,
        "student_code": res["cancelling_student_code"],
        "company_id": interview.company_id,
        "company_name": res["company_name"],
        "slot_index": interview.slot_index,
        "time_str": res["freed_slot_time"],
        "freed_room": res["freed_room_code"],
        "freed_panel": res["freed_panel_code"],
        "replacement_assigned": res["replacement_assigned"],
        "replacement_student_code": res["replacement_student_code"],
        "replacement_student_name": res["replacement_student_name"],
        "new_version_number": res["new_version_number"],
        "schedule_version_id": res["new_schedule_version_id"],
        "message": res["audit_message"]
    })

    return {
        "status": "SUCCESS",
        "message": res["audit_message"],
        "cancellation_id": res["cancellation_id"],
        "interview_id": interview.id,
        "new_schedule_version_id": res["new_schedule_version_id"],
        "new_version_number": res["new_version_number"],
        "replacement_assigned": res["replacement_assigned"],
        "replacement_student_code": res["replacement_student_code"],
        "replacement_student_name": res["replacement_student_name"]
    }
