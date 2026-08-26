import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.schedule import ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, CompanyRequirements
from app.models.resource import Room, Panel
from app.scheduler.validator import validate_schedule_integrity

class ConflictService:
    @staticmethod
    def get_conflicts_for_latest_version(db: Session, version_id: Optional[str] = None) -> Dict[str, Any]:
        if not version_id:
            latest = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
            if not latest:
                return {"total_conflicts": 0, "conflicts": []}
            version_id = latest.id

        interviews = db.query(Interview).filter(Interview.schedule_version_id == version_id).all()
        students = {s.id: {"id": s.id, "student_code": s.student_code, "name": s.name, "branch": s.branch, "cgpa": s.cgpa} for s in db.query(Student).all()}
        companies = {}
        for c in db.query(Company).all():
            req = db.query(CompanyRequirements).filter(CompanyRequirements.company_id == c.id).first()
            companies[c.id] = {
                "id": c.id,
                "company_code": c.company_code,
                "name": c.name,
                "requirements": {
                    "min_cgpa": req.min_cgpa if req else 6.0,
                    "eligible_branches": json.loads(req.eligible_branches) if req and req.eligible_branches else []
                }
            }
        rooms = {r.id: {"id": r.id, "room_code": r.room_code, "building": r.building} for r in db.query(Room).all()}
        panels = {p.id: {"id": p.id, "panel_code": p.panel_code, "company_id": p.company_id} for p in db.query(Panel).all()}

        iv_dicts = [
            {
                "id": iv.id,
                "student_id": iv.student_id,
                "company_id": iv.company_id,
                "room_id": iv.room_id,
                "panel_id": iv.panel_id,
                "slot_index": iv.slot_index,
                "day_number": iv.day_number,
                "start_time_str": iv.start_time_str
            }
            for iv in interviews
        ]

        is_valid, violations, metrics = validate_schedule_integrity(iv_dicts, companies, students, rooms, panels)
        
        conflict_items = []
        for i, v in enumerate(violations):
            conflict_items.append({
                "conflict_id": f"CONF-{i+1:03d}",
                "conflict_type": v.get("type", "GENERAL_CONFLICT"),
                "severity": v.get("severity", "MEDIUM"),
                "time_slot": f"Slot {v.get('slot_index', 0)}",
                "day_number": v.get("day_number", 1),
                "student_code": students.get(v.get("student_id"), {}).get("student_code") if v.get("student_id") else None,
                "company_name": companies.get(v.get("company_id"), {}).get("name") if v.get("company_id") else None,
                "room_code": rooms.get(v.get("room_id"), {}).get("room_code") if v.get("room_id") else None,
                "panel_code": panels.get(v.get("panel_id"), {}).get("panel_code") if v.get("panel_id") else None,
                "explanation": v.get("message", "Conflict detected in schedule"),
                "suggested_action": "Execute replanning run to resolve resource contention"
            })

        return {
            "total_conflicts": len(conflict_items),
            "conflicts": conflict_items,
            "is_valid": is_valid,
            "metrics": metrics
        }
