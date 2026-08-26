import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel
from app.scheduler.solver import PlacementScheduler

class ScheduleService:
    @staticmethod
    def get_or_create_default_schedule(db: Session) -> Schedule:
        sched = db.query(Schedule).filter(Schedule.status == "ACTIVE").first()
        if not sched:
            sched = Schedule(
                id=str(uuid.uuid4()),
                name="University Placement Week 2026",
                academic_year="2025-2026",
                status="ACTIVE"
            )
            db.add(sched)
            db.commit()
            db.refresh(sched)
        return sched

    @staticmethod
    def get_latest_schedule_version(db: Session, schedule_id: Optional[str] = None) -> Optional[ScheduleVersion]:
        query = db.query(ScheduleVersion)
        if schedule_id:
            query = query.filter(ScheduleVersion.schedule_id == schedule_id)
        return query.order_by(ScheduleVersion.version_number.desc()).first()

    @staticmethod
    def generate_initial_schedule(
        db: Session,
        schedule_id: Optional[str] = None,
        day_number: int = 1,
        max_time_seconds: int = 30
    ) -> Dict[str, Any]:
        schedule = ScheduleService.get_or_create_default_schedule(db) if not schedule_id else db.query(Schedule).get(schedule_id)
        if not schedule:
            raise ValueError("Schedule not found")

        # 1. Load entities
        students = db.query(Student).filter(Student.is_active == True, Student.is_withdrawn == False).all()
        companies = db.query(Company).filter(Company.is_active == True).all()
        rooms = db.query(Room).filter(Room.is_active == True).all()
        panels = db.query(Panel).filter(Panel.is_active == True).all()
        shortlists = db.query(Shortlist).filter(Shortlist.status != "WITHDRAWN").all()

        # Format dictionaries
        students_data = [
            {"id": s.id, "student_code": s.student_code, "name": s.name, "branch": s.branch, "cgpa": s.cgpa, "is_withdrawn": s.is_withdrawn}
            for s in students
        ]

        companies_data = []
        for c in companies:
            req = db.query(CompanyRequirements).filter(CompanyRequirements.company_id == c.id).first()
            branches = json.loads(req.eligible_branches) if req and req.eligible_branches else []
            min_cgpa = req.min_cgpa if req else 6.0
            
            avail = db.query(CompanyAvailability).filter(CompanyAvailability.company_id == c.id).first()
            start_slot = avail.start_time_slot if avail else 0
            end_slot = avail.end_time_slot if avail else 12

            companies_data.append({
                "id": c.id,
                "company_code": c.company_code,
                "name": c.name,
                "priority_tier": c.priority_tier,
                "interview_duration_mins": c.interview_duration_mins,
                "max_panels": c.max_panels,
                "is_active": c.is_active,
                "requirements": {
                    "min_cgpa": min_cgpa,
                    "eligible_branches": branches
                },
                "availability": {
                    "start_time_slot": start_slot,
                    "end_time_slot": end_slot
                }
            })

        rooms_data = [{"id": r.id, "room_code": r.room_code, "building": r.building, "is_active": r.is_active} for r in rooms]
        panels_data = [{"id": p.id, "company_id": p.company_id, "panel_code": p.panel_code, "is_active": p.is_active} for p in panels]
        shortlists_data = [{"id": sh.id, "student_id": sh.student_id, "company_id": sh.company_id} for sh in shortlists]

        # 2. Instantiate and Run CP-SAT Solver
        scheduler = PlacementScheduler(
            students=students_data,
            companies=companies_data,
            rooms=rooms_data,
            panels=panels_data,
            shortlists=shortlists_data,
            num_slots=12,
            day_number=day_number
        )

        solve_result = scheduler.solve(max_time_seconds=max_time_seconds, strategy_mode="BALANCED")
        
        if solve_result["status"] != "SUCCESS" and len(solve_result["interviews"]) == 0:
            return solve_result

        # 3. Create new ScheduleVersion
        last_version = ScheduleService.get_latest_schedule_version(db, schedule.id)
        new_version_num = (last_version.version_number + 1) if last_version else 1

        new_version = ScheduleVersion(
            id=str(uuid.uuid4()),
            schedule_id=schedule.id,
            version_number=new_version_num,
            stability_score=solve_result["metrics"]["schedule_stability"],
            metrics_snapshot=json.dumps(solve_result["metrics"])
        )
        db.add(new_version)
        db.flush()

        # 4. Save Interviews
        for iv in solve_result["interviews"]:
            db_iv = Interview(
                id=str(uuid.uuid4()),
                schedule_version_id=new_version.id,
                student_id=iv["student_id"],
                company_id=iv["company_id"],
                room_id=iv["room_id"],
                panel_id=iv["panel_id"],
                day_number=iv["day_number"],
                slot_index=iv["slot_index"],
                start_time_str=iv["start_time_str"],
                end_time_str=iv["end_time_str"],
                status="SCHEDULED",
                audit_metadata=json.dumps(iv.get("audit_metadata", {}))
            )
            db.add(db_iv)

        db.commit()
        db.refresh(new_version)

        solve_result["schedule_version_id"] = new_version.id
        solve_result["version_number"] = new_version.version_number
        return solve_result
