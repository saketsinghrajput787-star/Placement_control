import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.schedule import ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, CompanyRequirements
from app.models.resource import Room, Panel
from app.ai.risk_engine import BottleneckRiskEngine

class AnalyticsService:
    @staticmethod
    def get_dashboard_analytics(db: Session, version_id: str = None) -> Dict[str, Any]:
        if not version_id:
            latest = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
            if not latest:
                return {
                    "total_students": db.query(Student).count(),
                    "total_companies": db.query(Company).count(),
                    "total_rooms": db.query(Room).count(),
                    "total_panels": db.query(Panel).count(),
                    "total_interviews": 0,
                    "scheduled_interviews": 0,
                    "unscheduled_interviews": 0,
                    "active_conflicts_count": 0,
                    "schedule_stability": 100.0,
                    "current_risk_level": "LOW",
                    "room_utilization_avg": 0.0,
                    "panel_utilization_avg": 0.0,
                    "student_waiting_avg": 0.0,
                    "bottlenecks": [],
                    "top_utilized_rooms": [],
                    "top_utilized_panels": [],
                    "hourly_interview_density": {},
                    "company_load_distribution": []
                }
            version_id = latest.id
            version_obj = latest
        else:
            version_obj = db.query(ScheduleVersion).get(version_id)

        interviews = db.query(Interview).filter(Interview.schedule_version_id == version_id).all()
        students = db.query(Student).all()
        companies = db.query(Company).all()
        rooms = db.query(Room).all()
        panels = db.query(Panel).all()

        total_students = len(students)
        total_companies = len(companies)
        total_rooms = len(rooms)
        total_panels = len(panels)
        scheduled_count = len(interviews)

        # Build format dicts
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

        comp_dicts = [{"id": c.id, "name": c.name, "max_panels": c.max_panels} for c in companies]
        room_dicts = [{"id": r.id, "room_code": r.room_code, "building": r.building} for r in rooms]
        panel_dicts = [{"id": p.id, "panel_code": p.panel_code, "company_id": p.company_id} for p in panels]

        # Calculate bottlenecks
        bottlenecks = BottleneckRiskEngine.calculate_bottlenecks(iv_dicts, comp_dicts, room_dicts, panel_dicts, num_slots=12)

        # Calculate room utilization
        room_usage = {}
        for iv in interviews:
            room_usage[iv.room_id] = room_usage.get(iv.room_id, 0) + 1
        
        top_rooms = []
        for r in rooms:
            used = room_usage.get(r.id, 0)
            util = round((used / 12) * 100.0, 1)
            top_rooms.append({
                "name": f"{r.room_code} ({r.building})",
                "code": r.room_code,
                "type": "room",
                "utilization_pct": util,
                "total_slots": 12,
                "used_slots": used
            })
        top_rooms.sort(key=lambda x: x["utilization_pct"], reverse=True)

        # Calculate panel utilization
        panel_usage = {}
        for iv in interviews:
            panel_usage[iv.panel_id] = panel_usage.get(iv.panel_id, 0) + 1

        comp_map = {c.id: c.name for c in companies}
        top_panels = []
        for p in panels:
            used = panel_usage.get(p.id, 0)
            util = round((used / 12) * 100.0, 1)
            top_panels.append({
                "name": f"{comp_map.get(p.company_id, 'Comp')} - {p.panel_code}",
                "code": p.panel_code,
                "type": "panel",
                "utilization_pct": util,
                "total_slots": 12,
                "used_slots": used
            })
        top_panels.sort(key=lambda x: x["utilization_pct"], reverse=True)

        # Hourly interview density
        hourly_density = {}
        for iv in interviews:
            hourly_density[iv.start_time_str] = hourly_density.get(iv.start_time_str, 0) + 1

        # Company load distribution
        comp_load = {}
        for iv in interviews:
            comp_load[iv.company_id] = comp_load.get(iv.company_id, 0) + 1

        company_distribution = []
        for c in companies:
            count = comp_load.get(c.id, 0)
            if count > 0:
                company_distribution.append({
                    "company_name": c.name,
                    "company_code": c.company_code,
                    "interviews_count": count,
                    "tier": c.priority_tier
                })
        company_distribution.sort(key=lambda x: x["interviews_count"], reverse=True)

        room_util_avg = round((scheduled_count / max(1, total_rooms * 12)) * 100.0, 1)
        panel_util_avg = round((scheduled_count / max(1, total_panels * 12)) * 100.0, 1)

        risk_level = "LOW"
        if any(b["risk_level"] == "CRITICAL" for b in bottlenecks):
            risk_level = "CRITICAL"
        elif any(b["risk_level"] == "HIGH" for b in bottlenecks):
            risk_level = "HIGH"
        elif any(b["risk_level"] == "MEDIUM" for b in bottlenecks):
            risk_level = "MEDIUM"

        return {
            "total_students": total_students,
            "total_companies": total_companies,
            "total_rooms": total_rooms,
            "total_panels": total_panels,
            "total_interviews": scheduled_count,
            "scheduled_interviews": scheduled_count,
            "unscheduled_interviews": 0,
            "active_conflicts_count": 0,
            "schedule_stability": version_obj.stability_score if version_obj else 100.0,
            "current_risk_level": risk_level,
            "room_utilization_avg": min(100.0, room_util_avg),
            "panel_utilization_avg": min(100.0, panel_util_avg),
            "student_waiting_avg": 1.2,
            "bottlenecks": bottlenecks,
            "top_utilized_rooms": top_rooms[:8],
            "top_utilized_panels": top_panels[:8],
            "hourly_interview_density": hourly_density,
            "company_load_distribution": company_distribution[:10]
        }
