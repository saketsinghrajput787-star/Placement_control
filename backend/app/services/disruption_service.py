import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.operations import Disruption
from app.models.schedule import ScheduleVersion, Interview
from app.models.company import Company
from app.models.resource import Panel, Room
from app.models.student import Student

class DisruptionService:
    @staticmethod
    def simulate_disruption(
        db: Session,
        placement_session_id: str,
        event_type: str,
        target_entity_type: str,
        target_entity_id: str,
        delay_slots: int = 0,
        affected_panel_ids: Optional[List[str]] = None,
        withdrawn_student_ids: Optional[List[str]] = None,
        reason: str = "Operational disruption reported"
    ) -> Dict[str, Any]:
        affected_panel_ids = affected_panel_ids or []
        withdrawn_student_ids = withdrawn_student_ids or []

        versions = db.query(ScheduleVersion).filter(
            ScheduleVersion.placement_session_id == placement_session_id
        ).order_by(ScheduleVersion.version_number.desc()).all()
        
        latest_version = None
        for v in versions:
            if db.query(Interview).filter(Interview.schedule_version_id == v.id).count() > 0:
                latest_version = v
                break
        if not latest_version and versions:
            latest_version = versions[0]
        if not latest_version:
            raise ValueError("No active schedule version found to disrupt")

        interviews = db.query(Interview).filter(Interview.schedule_version_id == latest_version.id).all()
        
        affected_interviews_set = set()
        affected_students = set()
        affected_rooms = set()
        affected_panels = set()

        panel_ids_to_check = set(affected_panel_ids)
        if event_type == "PANEL_UNAVAILABLE" and target_entity_id:
            panel_ids_to_check.add(target_entity_id)

        student_ids_to_check = set(withdrawn_student_ids)
        if event_type in ["STUDENT_WITHDRAWAL", "STUDENT_CANCELLED_INTERVIEW"] and target_entity_id:
            student_ids_to_check.add(target_entity_id)

        for iv in interviews:
            is_affected = False
            
            if (event_type == "COMPANY_DELAY" or target_entity_type == "company") and iv.company_id == target_entity_id:
                is_affected = True

            if (event_type == "COMPANY_CANCELLATION") and iv.company_id == target_entity_id:
                is_affected = True

            if iv.panel_id in panel_ids_to_check:
                is_affected = True

            if iv.student_id in student_ids_to_check:
                is_affected = True

            if event_type == "ROOM_UNAVAILABLE" and iv.room_id == target_entity_id:
                is_affected = True

            if is_affected:
                affected_interviews_set.add(iv.id)
                affected_students.add(iv.student_id)
                affected_rooms.add(iv.room_id)
                affected_panels.add(iv.panel_id)

        affected_interviews = [iv for iv in interviews if iv.id in affected_interviews_set]

        count = len(affected_interviews)
        severity = "LOW"
        if count > 30 or delay_slots >= 4:
            severity = "CRITICAL"
        elif count > 15 or delay_slots >= 2:
            severity = "HIGH"
        elif count > 5:
            severity = "MEDIUM"

        params = {
            "delay_slots": delay_slots,
            "affected_panel_ids": list(affected_panel_ids),
            "withdrawn_student_ids": list(withdrawn_student_ids),
            "reason": reason
        }

        disruption = Disruption(
            id=str(uuid.uuid4()),
            placement_session_id=placement_session_id,
            event_type=event_type,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            severity=severity,
            parameters=json.dumps(params),
            status="SIMULATED"
        )
        
        db.add(disruption)
        db.commit()
        db.refresh(disruption)

        affected_details = []
        for iv in affected_interviews:
            student = db.query(Student).filter(Student.id == iv.student_id, Student.placement_session_id == placement_session_id).first()
            comp = db.query(Company).filter(Company.id == iv.company_id, Company.placement_session_id == placement_session_id).first()
            room = db.query(Room).filter(Room.id == iv.room_id, Room.placement_session_id == placement_session_id).first()
            panel = db.query(Panel).filter(Panel.id == iv.panel_id, Panel.placement_session_id == placement_session_id).first()
            affected_details.append({
                "interview_id": iv.id,
                "student_code": student.student_code if student else "N/A",
                "student_name": student.name if student else "N/A",
                "company_name": comp.name if comp else "N/A",
                "room_code": room.room_code if room else "N/A",
                "panel_code": panel.panel_code if panel else "N/A",
                "time_slot": iv.start_time_str
            })

        expected_delay_hours = round(delay_slots * 0.75, 2)
        explanation = (
            f"Simulated {event_type.replace('_', ' ').title()}: Directly affects {count} scheduled interviews "
            f"across {len(affected_students)} students, {len(affected_panels)} panels, and {len(affected_rooms)} rooms."
        )

        return {
            "disruption_id": disruption.id,
            "event_type": event_type,
            "severity": severity,
            "affected_interviews_count": count,
            "affected_students_count": len(affected_students),
            "affected_rooms_count": len(affected_rooms),
            "affected_panels_count": len(affected_panels),
            "expected_delay_hours": expected_delay_hours,
            "risk_level": severity,
            "affected_interviews": affected_details[:20],
            "explanation": explanation
        }
