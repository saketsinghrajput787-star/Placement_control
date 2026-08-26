import sys
import os
import json

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_root = os.path.join(project_root, "backend")
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.db.session import SessionLocal
from app.models.schedule import ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, CompanyRequirements
from app.models.resource import Room, Panel
from app.scheduler.validator import validate_schedule_integrity

def validate_active_schedule():
    db = SessionLocal()
    latest_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
    
    if not latest_version:
        print("[!] No active schedule version found to validate.")
        db.close()
        return False

    print(f"[*] Validating Schedule Version {latest_version.version_number} (ID: {latest_version.id})...")

    interviews = db.query(Interview).filter(Interview.schedule_version_id == latest_version.id).all()
    students = {s.id: {"id": s.id, "student_code": s.student_code, "branch": s.branch, "cgpa": s.cgpa} for s in db.query(Student).all()}
    
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

    print("\n" + "=" * 50)
    if is_valid:
        print("[+] VALIDATION PASSED -- ZERO HARD CONSTRAINT VIOLATIONS")
    else:
        print(f"[-] VALIDATION FAILED -- {len(violations)} VIOLATIONS FOUND")
    print("=" * 50)

    print(f"Total Scheduled Interviews : {len(interviews)}")
    print(f"Unique Students Scheduled  : {metrics.get('unique_students_scheduled')}")
    print(f"Unique Rooms Utilized      : {metrics.get('unique_rooms_used')}")
    print(f"Unique Panels Utilized     : {metrics.get('unique_panels_used')}")
    print(f"Active Violations          : {len(violations)}")

    if violations:
        print("\nViolations List:")
        for v in violations[:10]:
            print(f"  - [{v.get('type')}] {v.get('message')}")

    db.close()
    return is_valid

if __name__ == "__main__":
    success = validate_active_schedule()
    sys.exit(0 if success else 1)
