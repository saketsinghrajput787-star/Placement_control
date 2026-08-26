import pytest
from app.scheduler.solver import PlacementScheduler

def test_scheduler_generates_valid_schedule():
    students = [
        {"id": f"S{i}", "student_code": f"S000{i}", "branch": "CSE", "cgpa": 8.0} for i in range(1, 11)
    ]
    companies = [
        {
            "id": "C1",
            "name": "TechCorp",
            "priority_tier": 1,
            "max_panels": 2,
            "requirements": {"min_cgpa": 7.0, "eligible_branches": ["CSE"]},
            "availability": {"start_time_slot": 0, "end_time_slot": 12}
        },
        {
            "id": "C2",
            "name": "DataInc",
            "priority_tier": 2,
            "max_panels": 2,
            "requirements": {"min_cgpa": 7.5, "eligible_branches": ["CSE"]},
            "availability": {"start_time_slot": 0, "end_time_slot": 12}
        }
    ]
    rooms = [{"id": f"R{i}", "room_code": f"R0{i}", "building": "A"} for i in range(1, 6)]
    panels = [
        {"id": "P1", "company_id": "C1", "panel_code": "P1"},
        {"id": "P2", "company_id": "C1", "panel_code": "P2"},
        {"id": "P3", "company_id": "C2", "panel_code": "P1"},
        {"id": "P4", "company_id": "C2", "panel_code": "P2"},
    ]
    # Shortlists with multi-company overlap for pressure
    shortlists = []
    for s in students:
        shortlists.append({"student_id": s["id"], "company_id": "C1"})
        shortlists.append({"student_id": s["id"], "company_id": "C2"})

    scheduler = PlacementScheduler(
        students=students,
        companies=companies,
        rooms=rooms,
        panels=panels,
        shortlists=shortlists,
        num_slots=12,
        day_number=1
    )

    result = scheduler.solve(max_time_seconds=10)
    assert result["is_valid"] is True
    assert len(result["violations"]) == 0
    assert result["metrics"]["scheduled_interviews"] == 20  # All 20 shortlists scheduled
    assert result["metrics"]["active_conflicts"] == 0
