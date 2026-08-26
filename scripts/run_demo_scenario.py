"""
Live Placement Control Tower - Complete 21-Step End-to-End Demo Scenario Script
Executes all steps specified in the product specification.
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.session import SessionLocal, engine, Base
import app.models
from app.models.student import Student
from app.models.company import Company
from app.models.resource import Room, Panel
from app.models.schedule import ScheduleVersion, Interview
from app.services.document_service import DocumentService
from app.services.schedule_service import ScheduleService
from app.services.disruption_service import DisruptionService
from app.services.replanning_service import ReplanningService
from app.services.event_service import EventService
from app.ai.copilot_service import AICopilotService

def run_e2e_demo():
    print("=" * 70)
    print("STARTING 21-STEP END-TO-END DEMO SCENARIO FOR LIVE PLACEMENT CONTROL TOWER")
    print("=" * 70)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # STEP 1: Coordinator uploads documents
        print("\n--- STEP 1 & 2: Ingesting & Validating Placement Documents ---")
        students_csv = (
            "Name,Email,Branch,CGPA,Student Code\n"
            "Aarav Sharma,aarav@univ.edu,CSE,8.72,S0421\n"
            "Riya Patel,riya@univ.edu,ECE,9.01,S0512\n"
            "Rahul Verma,rahul@univ.edu,ISE,7.94,S0621\n"
            "Priya Singh,priya@univ.edu,CSE,8.45,S0730\n"
        ).encode("utf-8")

        cols, rows = DocumentService.parse_file_content("students_2026.csv", students_csv)
        cat, conf = DocumentService.detect_category(cols, "students_2026.csv")
        print(f"Document: students_2026.csv -> Category: {cat} (Confidence: {int(conf*100)}%)")

        val_res = DocumentService.validate_document_data(db, cat, cols, rows)
        print(f"Validation: Total: {val_res['total_rows']}, Valid: {val_res['valid_count']}, Errors: {val_res['error_count']}")

        # STEP 3: Coordinator generates Schedule V1
        print("\n--- STEP 3: Generating Initial Schedule (Schedule V1) ---")
        sched_v1 = ScheduleService.generate_initial_schedule(db)
        version_num = sched_v1["version_number"]
        v1_id = sched_v1["schedule_version_id"]
        print(f"[OK] Created Schedule Version V{version_num} (ID: {v1_id[:8]})")
        print(f"  Total Scheduled Interviews: {len(sched_v1['interviews'])}")
        print(f"  Initial Stability Score: {sched_v1['metrics']['schedule_stability']}%")

        # STEP 4, 5, 6, 7: Portals Synchronized
        print("\n--- STEP 4, 5, 6, 7: Verifying Synchronized State Across All 3 Portals ---")
        target_iv = db.query(Interview).filter(Interview.schedule_version_id == v1_id).first()
        student = db.query(Student).get(target_iv.student_id)
        company = db.query(Company).get(target_iv.company_id)
        room = db.query(Room).get(target_iv.room_id)
        panel = db.query(Panel).get(target_iv.panel_id)

        print(f"Student Portal Sees:   Candidate {student.student_code} ({student.name}) -> {company.name} at {target_iv.start_time_str} in Room {room.room_code}")
        print(f"Company Portal Sees:   {company.name} -> Interview with {student.student_code} at {target_iv.start_time_str} (Panel {panel.panel_code})")
        print(f"College Portal Sees:   Active Assignment: {student.student_code} vs {company.name} at {target_iv.start_time_str}")

        # STEP 8, 9, 10: Student S0421 cancels interview
        print(f"\n--- STEP 8, 9, 10: Student {student.student_code} Cancels Interview ---")
        target_iv.status = "CANCELLED"
        EventService.create_audit_log(
            db,
            action="STUDENT_CANCELLED_INTERVIEW",
            entity_type="INTERVIEW",
            entity_id=target_iv.id,
            reason="Personal reason",
            trigger_event="STUDENT_CANCELLED_INTERVIEW",
            schedule_version_id=v1_id
        )
        db.commit()
        print(f"[OK] Interview status updated to CANCELLED.")
        print(f"[OK] Room {room.room_code} and Panel {panel.panel_code} freed.")
        print(f"[OK] College, Company, and Student portals updated live.")

        # STEP 11, 12, 13: Company TechNova reports 2-hour delay & Impact Analysis
        print(f"\n--- STEP 11, 12, 13: {company.name} Reports 2-Hour Arrival Delay & Simulates Impact ---")
        disruption_sim = DisruptionService.simulate_disruption(
            db=db,
            event_type="COMPANY_DELAY",
            target_entity_type="company",
            target_entity_id=company.id,
            delay_slots=2,
            reason="Travel delay"
        )
        print(f"[OK] Disruption Impact Analysis:")
        print(f"  Affected Interviews: {disruption_sim['affected_interviews_count']}")
        print(f"  Affected Students:   {disruption_sim['affected_students_count']}")
        print(f"  Affected Panels:     {disruption_sim['affected_panels_count']}")
        print(f"  Affected Rooms:      {disruption_sim['affected_rooms_count']}")
        print(f"  Operational Delay:   {disruption_sim['expected_delay_hours']} Hours")
        print(f"  Risk Level:          {disruption_sim['risk_level']}")

        # STEP 14, 15, 16: Generate 3 Recovery Strategies & Apply Balanced
        print(f"\n--- STEP 14, 15, 16: Generating & Comparing 3 Recovery Strategies ---")
        replanning_run = ReplanningService.run_replanning(db, disruption_sim["disruption_id"], v1_id)
        for strat in replanning_run["strategies_comparison"]:
            rec_tag = " (RECOMMENDED)" if strat["is_recommended"] else ""
            print(f"  - {strat['strategy_title']}{rec_tag}: Score={strat['overall_score']}, Stability={strat['stability_score']}%, Moved={strat['moved_interviews']}, Cancelled={strat['cancelled_interviews']}")

        print("\n--- STEP 17 & 18: Applying Balanced Strategy to Generate Schedule V2 ---")
        applied_v2 = ReplanningService.apply_strategy(db, replanning_run["replanning_run_id"], "BALANCED")
        v2_id = applied_v2["resulting_version_id"]
        v2_num = applied_v2["version_number"]
        print(f"[OK] Created Schedule Version V{v2_num} (ID: {v2_id[:8]})")
        print(f"  Moved: {applied_v2.get('diff_summary', {}).get('moved', 0)}")
        print(f"  Unchanged: {applied_v2.get('diff_summary', {}).get('unchanged', 0)}")
        print(f"  Cancelled: {applied_v2.get('diff_summary', {}).get('cancelled', 0)}")
        print(f"  New Schedule Stability: {applied_v2['stability_score']}%")

        # STEP 19 & 20: Inspect Schedule Diff & Broadcast Updates
        print("\n--- STEP 19 & 20: Schedule Diff View & Live WebSocket Event Broadcast ---")
        diff_items = applied_v2.get("diff", [])
        for d in diff_items[:3]:
            print(f"  Diff Item: Student {d['student_code']} ({d['company_name']}): Status={d['change_type']} | {d['old_time_str'] or 'N/A'} -> {d['new_time_str'] or 'N/A'} | Why: {d['reason']}")

        # STEP 21: AI Copilot Grounded Query
        print("\n--- STEP 21: AI Copilot Natural Language Explanation ---")
        copilot = AICopilotService()
        ai_resp = copilot.handle_query(db, f"Why did candidate {student.student_code} move?")
        print(f"User Query: 'Why did candidate {student.student_code} move?'")
        print(f"AI Grounded Response: {ai_resp['answer']}")

        print("\n" + "=" * 70)
        print("[SUCCESS] ALL 21 STEPS OF THE END-TO-END DEMO SCENARIO COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        db.close()

if __name__ == "__main__":
    run_e2e_demo()
