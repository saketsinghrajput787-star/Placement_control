import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel
from app.scheduler.solver import PlacementScheduler
from app.scheduler.validator import validate_scheduler_preconditions

class ScheduleService:
    @staticmethod
    def get_or_create_default_schedule(db: Session, placement_session_id: str) -> Schedule:
        sched = db.query(Schedule).filter(
            Schedule.placement_session_id == placement_session_id,
            Schedule.status == "ACTIVE"
        ).first()
        if not sched:
            sched = Schedule(
                id=str(uuid.uuid4()),
                placement_session_id=placement_session_id,
                name="University Placement Week 2026",
                academic_year="2025-2026",
                status="ACTIVE"
            )
            db.add(sched)
            db.commit()
            db.refresh(sched)
        return sched

    @staticmethod
    def get_latest_schedule_version(db: Session, placement_session_id: str, schedule_id: Optional[str] = None) -> Optional[ScheduleVersion]:
        query = db.query(ScheduleVersion).filter(ScheduleVersion.placement_session_id == placement_session_id)
        if schedule_id:
            query = query.filter(ScheduleVersion.schedule_id == schedule_id)
        return query.order_by(ScheduleVersion.version_number.desc()).first()

    @staticmethod
    def generate_initial_schedule(
        db: Session,
        placement_session_id: str,
        schedule_id: Optional[str] = None,
        day_number: int = 1,
        max_time_seconds: int = 30
    ) -> Dict[str, Any]:
        # Precondition Validation
        pre_check = validate_scheduler_preconditions(db, placement_session_id)
        if not pre_check["is_ready"]:
            return {
                "status": "BLOCKED",
                "message": pre_check["message"],
                "missing_datasets": pre_check["missing_datasets"],
                "counts": pre_check["counts"],
                "interviews": [],
                "metrics": {
                    "total_interviews": 0,
                    "scheduled_interviews": 0,
                    "unscheduled_interviews": 0,
                    "total_students": pre_check["counts"]["students"],
                    "total_companies": pre_check["counts"]["companies"],
                    "total_rooms": pre_check["counts"]["rooms"],
                    "total_panels": pre_check["counts"]["panels"],
                    "active_conflicts": 0,
                    "schedule_stability": 0.0,
                    "room_utilization_pct": 0.0,
                    "panel_utilization_pct": 0.0,
                    "total_waiting_minutes": 0,
                    "avg_student_waiting_minutes": 0.0,
                    "max_student_waiting_minutes": 0,
                    "waiting_level": "LOW",
                    "avg_student_waiting_slots": 0.0,
                    "bottleneck_risk_level": "NONE",
                    "solve_duration_seconds": 0.0,
                    "solver_status": "BLOCKED"
                }
            }

        schedule = db.query(Schedule).filter(
            Schedule.id == schedule_id,
            Schedule.placement_session_id == placement_session_id
        ).first() if schedule_id else ScheduleService.get_or_create_default_schedule(db, placement_session_id)

        if not schedule:
            raise ValueError("Schedule not found")

        # 1. Load entities for placement_session_id
        students = db.query(Student).filter(
            Student.placement_session_id == placement_session_id,
            Student.is_active == True,
            Student.is_withdrawn == False
        ).all()
        companies = db.query(Company).filter(
            Company.placement_session_id == placement_session_id,
            Company.is_active == True
        ).all()
        rooms = db.query(Room).filter(
            Room.placement_session_id == placement_session_id,
            Room.is_active == True
        ).all()
        panels = db.query(Panel).filter(
            Panel.placement_session_id == placement_session_id,
            Panel.is_active == True
        ).all()
        shortlists = db.query(Shortlist).filter(
            Shortlist.placement_session_id == placement_session_id,
            Shortlist.status != "WITHDRAWN"
        ).all()

        students_data = [
            {"id": s.id, "student_code": s.student_code, "name": s.name, "branch": s.branch, "cgpa": s.cgpa, "is_withdrawn": s.is_withdrawn}
            for s in students
        ]

        companies_data = []
        for c in companies:
            req = db.query(CompanyRequirements).filter(
                CompanyRequirements.placement_session_id == placement_session_id,
                CompanyRequirements.company_id == c.id
            ).first()
            branches = json.loads(req.eligible_branches) if req and req.eligible_branches else []
            min_cgpa = req.min_cgpa if req else 6.0
            
            avail = db.query(CompanyAvailability).filter(
                CompanyAvailability.placement_session_id == placement_session_id,
                CompanyAvailability.company_id == c.id
            ).first()
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

        comp_panels_count = {}
        for p in panels:
            comp_panels_count[p.company_id] = comp_panels_count.get(p.company_id, 0) + 1

        comp_shortlists = {}
        for sh in shortlists:
            comp_shortlists.setdefault(sh.company_id, []).append(sh)

        pruned_shortlists = []
        for c_id, sh_list in comp_shortlists.items():
            num_p = comp_panels_count.get(c_id, 1)
            sh_list_sorted = sorted(sh_list, key=lambda x: (x.preference_rank or 1))
            pruned_shortlists.extend(sh_list_sorted[:max(15, num_p * 20)])

        shortlists_data = [{"id": sh.id, "student_id": sh.student_id, "company_id": sh.company_id} for sh in pruned_shortlists]

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
        last_version = ScheduleService.get_latest_schedule_version(db, placement_session_id, schedule.id)
        new_version_num = (last_version.version_number + 1) if last_version else 1

        new_version = ScheduleVersion(
            id=str(uuid.uuid4()),
            placement_session_id=placement_session_id,
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
                placement_session_id=placement_session_id,
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
