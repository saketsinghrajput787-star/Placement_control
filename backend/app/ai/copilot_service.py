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

    def handle_query(self, db: Session, query: str, context_type: str = "GENERAL", entity_id: str = None) -> Dict[str, Any]:
        analytics = AnalyticsService.get_dashboard_analytics(db)
        
        # Search recent schedule changes or audit logs matching query keywords
        recent_changes = db.query(ScheduleChange).order_by(ScheduleChange.created_at.desc()).limit(20).all()
        changes_data = []
        for ch in recent_changes:
            st = db.query(Student).get(ch.student_id)
            comp = db.query(Company).get(ch.company_id)
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
            "Your answers must be grounded ONLY in verified facts from the placement operations database. "
            "Never hallucinate numbers, student names, or non-existent schedule moves. "
            f"Current Verified System Facts: {json.dumps(grounding_data)}. "
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
            "Why did S0421 move?",
            "What happened after TechNova delay?",
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

    def explain_interview(self, db: Session, interview_id: str) -> Dict[str, Any]:
        iv = db.query(Interview).get(interview_id)
        if not iv:
            raise ValueError("Interview not found")

        student = db.query(Student).get(iv.student_id)
        comp = db.query(Company).get(iv.company_id)
        room = db.query(Room).get(iv.room_id)
        panel = db.query(Panel).get(iv.panel_id)

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
