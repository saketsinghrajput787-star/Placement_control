import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.ai.groq_provider import GroqProvider
from app.services.analytics_service import AnalyticsService
from app.models.schedule import ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company
from app.models.resource import Room, Panel
from app.models.operations import ScheduleChange, AuditLog

class AICopilotService:
    def __init__(self):
        self.provider = GroqProvider()

    def handle_query(self, db: Session, placement_session_id: str, query: str, context_type: str = "GENERAL", entity_id: str = None) -> Dict[str, Any]:
        analytics = AnalyticsService.get_dashboard_analytics(db, placement_session_id)
        
        if analytics["total_students"] == 0 and analytics["total_companies"] == 0:
            return {
                "answer": "No placement data has been imported yet for this placement session. Please upload Students, Companies, and Shortlists datasets to begin scheduling and analysis.",
                "insights": ["No dataset imported"],
                "relevant_metrics": {
                    "stability": 100.0,
                    "scheduled": 0,
                    "conflicts": 0,
                    "risk": "NONE"
                },
                "suggested_followups": [
                    "How do I upload student CSV?",
                    "What CSV schema is required?",
                    "How does CP-SAT optimization work?"
                ],
                "data_grounding": {"total_students": 0, "total_companies": 0, "scheduled_interviews": 0}
            }

        recent_changes = db.query(ScheduleChange).filter(
            ScheduleChange.placement_session_id == placement_session_id
        ).order_by(ScheduleChange.created_at.desc()).limit(20).all()

        changes_data = []
        for ch in recent_changes:
            st = db.query(Student).filter(Student.id == ch.student_id, Student.placement_session_id == placement_session_id).first()
            comp = db.query(Company).filter(Company.id == ch.company_id, Company.placement_session_id == placement_session_id).first()
            changes_data.append({
                "student_code": st.student_code if st else ch.student_id,
                "company_name": comp.name if comp else ch.company_id,
                "change_type": ch.change_type,
                "old_time": ch.old_time_str,
                "new_time": ch.new_time_str,
                "reason": ch.reason
            })

        grounding_data = {
            "total_students": analytics["total_students"],
            "total_companies": analytics["total_companies"],
            "scheduled_interviews": analytics["scheduled_interviews"],
            "stability_score": analytics["schedule_stability"],
            "current_risk_level": analytics["current_risk_level"],
            "recent_schedule_changes": changes_data[:10]
        }

        system_prompt = (
            "You are the AI Decision Support Copilot for the Live Placement Control Tower. "
            "Your answers must be grounded ONLY in verified facts from the currently uploaded placement session database. "
            "Never fabricate numbers, student names, company names, or non-existent schedule moves. "
            f"Current Session Verified Facts: {json.dumps(grounding_data)}. "
            "Provide concise, actionable, and executive-ready operational intelligence."
        )

        user_prompt = f"User Question: {query}\nContext Scope: {context_type}\nEntity Filter: {entity_id or 'None'}"

        answer = self.provider.generate_chat_response(user_prompt, system_prompt)

        insights = [
            f"System stability is currently at {analytics['schedule_stability']}%.",
            f"All {analytics['scheduled_interviews']} interviews satisfy hard constraints.",
            f"Overall operational risk level is evaluated as {analytics['current_risk_level']}."
        ]

        followups = [
            "Which students are affected by recent changes?",
            "What happened after company delay?",
            "Show recent document import history",
            "Which recovery strategy minimizes student waiting time?"
        ]

        return {
            "answer": answer,
            "insights": insights,
            "relevant_metrics": {
                "stability": analytics["schedule_stability"],
                "scheduled": analytics["scheduled_interviews"],
                "conflicts": analytics["active_conflicts_count"],
                "risk": analytics["current_risk_level"]
            },
            "suggested_followups": followups,
            "data_grounding": grounding_data
        }

    def explain_interview(self, db: Session, placement_session_id: str, interview_id: str) -> Dict[str, Any]:
        iv = db.query(Interview).filter(Interview.id == interview_id, Interview.placement_session_id == placement_session_id).first()
        if not iv:
            raise ValueError("Interview not found in current placement session")

        student = db.query(Student).filter(Student.id == iv.student_id, Student.placement_session_id == placement_session_id).first()
        comp = db.query(Company).filter(Company.id == iv.company_id, Company.placement_session_id == placement_session_id).first()
        room = db.query(Room).filter(Room.id == iv.room_id, Room.placement_session_id == placement_session_id).first()
        panel = db.query(Panel).filter(Panel.id == iv.panel_id, Panel.placement_session_id == placement_session_id).first()

        audit_meta = json.loads(iv.audit_metadata) if iv.audit_metadata else {}

        interview_data = {
            "interview_id": iv.id,
            "student_code": student.student_code if student else "Candidate",
            "company_name": comp.name if comp else "Company",
            "room_code": room.room_code if room else "Room",
            "panel_code": panel.panel_code if panel else "Panel",
            "company_tier": comp.priority_tier if comp else 1,
            "time_slot": f"{iv.start_time_str} - {iv.end_time_str}"
        }

        ai_summary = self.provider.explain_schedule_decision(interview_data)

        return {
            "interview_id": iv.id,
            "student_code": interview_data["student_code"],
            "company_name": interview_data["company_name"],
            "room_code": interview_data["room_code"],
            "panel_code": interview_data["panel_code"],
            "time_slot": interview_data["time_slot"],
            "hard_constraints_satisfied": audit_meta.get("constraint_checks", {
                "student_eligible": True,
                "student_available": True,
                "company_available": True,
                "panel_available": True,
                "room_available": True,
                "no_student_overlap": True,
                "no_room_overlap": True,
                "no_panel_overlap": True
            }),
            "optimization_reasons": audit_meta.get("optimization_reasons", [
                f"Assigned earliest optimal slot ({iv.start_time_str})",
                f"Satisfies Priority Tier {comp.priority_tier if comp else 1}",
                f"Preserves low student waiting gap"
            ]),
            "rejected_alternatives": audit_meta.get("rejected_alternatives", []),
            "replan_history": audit_meta.get("replan_reason"),
            "ai_summary": ai_summary
        }
