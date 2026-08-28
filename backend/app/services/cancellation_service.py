import json
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.student import Student
from app.models.company import Company, Shortlist, CompanyRequirements
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.cancellation import InterviewCancellation
from app.models.resource import Room, Panel
from app.models.operations import ScheduleChange
from app.services.event_service import EventService

class CancellationService:
    @staticmethod
    def handle_student_cancellation(
        db: Session,
        placement_session_id: str,
        interview_id: str,
        reason: str,
        comment: Optional[str],
        current_user: User
    ) -> Dict[str, Any]:
        # 1. Fetch interview
        interview = db.query(Interview).filter(
            Interview.id == interview_id,
            Interview.placement_session_id == placement_session_id
        ).first()
        if not interview:
            raise ValueError("Interview not found in current placement session")

        cancelling_student = db.query(Student).filter(Student.id == interview.student_id, Student.placement_session_id == placement_session_id).first()
        company = db.query(Company).filter(Company.id == interview.company_id, Company.placement_session_id == placement_session_id).first()
        room = db.query(Room).filter(Room.id == interview.room_id, Room.placement_session_id == placement_session_id).first()
        panel = db.query(Panel).filter(Panel.id == interview.panel_id, Panel.placement_session_id == placement_session_id).first()

        source_version_id = interview.schedule_version_id
        source_version = db.query(ScheduleVersion).filter(ScheduleVersion.id == source_version_id, ScheduleVersion.placement_session_id == placement_session_id).first()
        if not source_version:
            raise ValueError("Source schedule version not found")

        # 2. Mark original interview cancelled & shortlist withdrawn
        interview.status = "CANCELLED"
        shortlist = db.query(Shortlist).filter(
            Shortlist.placement_session_id == placement_session_id,
            Shortlist.student_id == interview.student_id,
            Shortlist.company_id == interview.company_id
        ).first()
        if shortlist:
            shortlist.status = "WITHDRAWN"

        # Record cancellation
        cancellation = InterviewCancellation(
            id=str(uuid.uuid4()),
            placement_session_id=placement_session_id,
            interview_id=interview.id,
            schedule_version_id=source_version_id,
            student_id=interview.student_id,
            company_id=interview.company_id,
            freed_room_id=interview.room_id,
            freed_panel_id=interview.panel_id,
            slot_index=interview.slot_index,
            day_number=interview.day_number,
            reason=reason,
            comment=comment,
            cancelled_by_role=current_user.role,
            cancelled_by_user_id=current_user.id
        )
        db.add(cancellation)
        db.flush()

        # 3. Find current active scheduled interviews in source_version
        active_interviews = db.query(Interview).filter(
            Interview.placement_session_id == placement_session_id,
            Interview.schedule_version_id == source_version_id,
            Interview.status == "SCHEDULED",
            Interview.id != interview.id
        ).all()

        busy_student_ids_in_slot = {
            iv.student_id for iv in active_interviews
            if iv.slot_index == interview.slot_index and iv.day_number == interview.day_number
        }
        busy_student_ids_in_slot.add(interview.student_id)

        student_interview_counts: Dict[str, int] = {}
        for iv in active_interviews:
            student_interview_counts[iv.student_id] = student_interview_counts.get(iv.student_id, 0) + 1

        req = db.query(CompanyRequirements).filter(
            CompanyRequirements.placement_session_id == placement_session_id,
            CompanyRequirements.company_id == company.id
        ).first()
        min_cgpa = req.min_cgpa if req else 6.0
        eligible_branches = json.loads(req.eligible_branches) if req and req.eligible_branches else []

        potential_shortlists = db.query(Shortlist).filter(
            Shortlist.placement_session_id == placement_session_id,
            Shortlist.company_id == company.id,
            Shortlist.status != "WITHDRAWN",
            ~Shortlist.student_id.in_(busy_student_ids_in_slot)
        ).all()

        candidate_evaluations: List[Dict[str, Any]] = []

        for sh in potential_shortlists:
            cand_student = db.query(Student).filter(Student.id == sh.student_id, Student.placement_session_id == placement_session_id).first()
            if not cand_student or not cand_student.is_active or cand_student.is_withdrawn:
                continue

            if cand_student.cgpa < min_cgpa:
                continue
            if eligible_branches and cand_student.branch not in eligible_branches:
                continue

            already_scheduled_same_company = any(
                iv.student_id == cand_student.id and iv.company_id == company.id
                for iv in active_interviews
            )
            if already_scheduled_same_company:
                continue

            current_count = student_interview_counts.get(cand_student.id, 0)
            fairness_score = 1000 if current_count == 0 else max(0, 500 - (current_count * 100))
            cgpa_score = cand_student.cgpa * 10
            pref_rank = getattr(sh, 'preference_rank', 1) or 1
            rank_score = max(0, 100 - pref_rank)

            total_candidate_score = fairness_score + cgpa_score + rank_score

            candidate_evaluations.append({
                "student": cand_student,
                "shortlist": sh,
                "score": total_candidate_score,
                "current_interview_count": current_count
            })

        candidate_evaluations.sort(key=lambda c: c["score"], reverse=True)

        # 4. Create new Schedule Version
        last_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.placement_session_id == placement_session_id
        ).order_by(ScheduleVersion.version_number.desc()).first()
        new_version_num = (last_version.version_number + 1) if last_version else 1
        schedule = db.query(Schedule).filter(Schedule.id == source_version.schedule_id, Schedule.placement_session_id == placement_session_id).first()

        new_version = ScheduleVersion(
            id=str(uuid.uuid4()),
            placement_session_id=placement_session_id,
            schedule_id=schedule.id,
            version_number=new_version_num,
            stability_score=source_version.stability_score,
            metrics_snapshot=source_version.metrics_snapshot
        )
        db.add(new_version)
        db.flush()

        for iv in active_interviews:
            db_iv = Interview(
                id=str(uuid.uuid4()),
                placement_session_id=placement_session_id,
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
            )
            db.add(db_iv)

        source_cancelled = db.query(Interview).filter(
            Interview.placement_session_id == placement_session_id,
            Interview.schedule_version_id == source_version_id,
            Interview.status == "CANCELLED",
            Interview.id != interview.id
        ).all()
        for sc_iv in source_cancelled:
            db_iv = Interview(
                id=str(uuid.uuid4()),
                placement_session_id=placement_session_id,
                schedule_version_id=new_version.id,
                student_id=sc_iv.student_id,
                company_id=sc_iv.company_id,
                room_id=sc_iv.room_id,
                panel_id=sc_iv.panel_id,
                day_number=sc_iv.day_number,
                slot_index=sc_iv.slot_index,
                start_time_str=sc_iv.start_time_str,
                end_time_str=sc_iv.end_time_str,
                status="CANCELLED",
                audit_metadata=sc_iv.audit_metadata
            )
            db.add(db_iv)

        new_cancelled_iv = Interview(
            id=str(uuid.uuid4()),
            placement_session_id=placement_session_id,
            schedule_version_id=new_version.id,
            student_id=interview.student_id,
            company_id=interview.company_id,
            room_id=interview.room_id,
            panel_id=interview.panel_id,
            day_number=interview.day_number,
            slot_index=interview.slot_index,
            start_time_str=interview.start_time_str,
            end_time_str=interview.end_time_str,
            status="CANCELLED",
            audit_metadata=json.dumps({
                "cancellation_reason": reason,
                "comment": comment,
                "cancelled_by_role": current_user.role
            })
        )
        db.add(new_cancelled_iv)

        replacement_student: Optional[Student] = None
        if candidate_evaluations:
            best_match = candidate_evaluations[0]
            replacement_student = best_match["student"]

            new_iv = Interview(
                id=str(uuid.uuid4()),
                placement_session_id=placement_session_id,
                schedule_version_id=new_version.id,
                student_id=replacement_student.id,
                company_id=company.id,
                room_id=room.id,
                panel_id=panel.id,
                day_number=interview.day_number,
                slot_index=interview.slot_index,
                start_time_str=interview.start_time_str,
                end_time_str=interview.end_time_str,
                status="RESCHEDULED",
                audit_metadata=json.dumps({
                    "assignment_reason": f"Reassigned freed slot from candidate cancellation ({cancelling_student.student_code if cancelling_student else 'S0000'})",
                    "candidate_score": best_match["score"],
                    "candidate_rank": getattr(best_match["shortlist"], "preference_rank", 1)
                })
            )
            db.add(new_iv)

        cancellation.resulting_schedule_version_id = new_version.id

        if cancelling_student and cancelling_student.user_id:
            EventService.create_notification(
                db=db,
                user_id=cancelling_student.user_id,
                title="Interview Cancelled",
                message=f"Your interview with {company.name if company else 'Company'} at {interview.start_time_str} has been cancelled.",
                category="SCHEDULE_CHANGE",
                related_entity_type="INTERVIEW",
                related_entity_id=interview.id,
                schedule_version_id=new_version.id
            )

        if replacement_student and replacement_student.user_id:
            EventService.create_notification(
                db=db,
                user_id=replacement_student.user_id,
                title="New Interview Assigned!",
                message=f"You have been assigned to an interview slot with {company.name if company else 'Company'} at {interview.start_time_str} in Room {room.room_code if room else ''}.",
                category="SCHEDULE_CHANGE",
                related_entity_type="INTERVIEW",
                related_entity_id=new_iv.id,
                schedule_version_id=new_version.id
            )

        before_state = {
            "interview_id": interview.id,
            "student_code": cancelling_student.student_code if cancelling_student else "N/A",
            "time": interview.start_time_str,
            "room": room.room_code if room else "N/A",
            "panel": panel.panel_code if panel else "N/A",
            "status": "SCHEDULED"
        }
        after_state = {
            "interview_id": interview.id,
            "status": "CANCELLED",
            "reason": reason,
            "freed_slot": interview.start_time_str,
            "replacement_candidate": replacement_student.student_code if replacement_student else "None Available"
        }

        audit_message = (
            f"Student {cancelling_student.student_code if cancelling_student else 'Candidate'} cancelled interview at {interview.start_time_str}. "
        )
        if replacement_student:
            audit_message += f"Freed slot in room {room.room_code if room else 'R01'} / panel {panel.panel_code if panel else 'P1'} reassigned to eligible candidate {replacement_student.student_code} ({replacement_student.name})."
        else:
            audit_message += "No eligible replacement student available. Slot left vacant."

        EventService.create_audit_log(
            db,
            action="STUDENT_CANCELLED_INTERVIEW",
            entity_type="INTERVIEW",
            entity_id=interview.id,
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role,
            before_state=before_state,
            after_state=after_state,
            reason=audit_message,
            trigger_event="STUDENT_CANCELLED_INTERVIEW",
            schedule_version_id=new_version.id
        )

        db.commit()
        db.refresh(new_version)

        return {
            "cancellation_id": cancellation.id,
            "interview_id": interview.id,
            "cancelling_student_code": cancelling_student.student_code if cancelling_student else "N/A",
            "cancelling_student_name": cancelling_student.name if cancelling_student else "N/A",
            "company_name": company.name if company else "N/A",
            "replacement_assigned": replacement_student is not None,
            "replacement_student_code": replacement_student.student_code if replacement_student else None,
            "replacement_student_name": replacement_student.name if replacement_student else None,
            "freed_slot_time": interview.start_time_str,
            "freed_room_code": room.room_code if room else "N/A",
            "freed_panel_code": panel.panel_code if panel else "N/A",
            "new_schedule_version_id": new_version.id,
            "new_version_number": new_version.version_number,
            "audit_message": audit_message
        }
