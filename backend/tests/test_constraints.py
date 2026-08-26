import pytest
from app.scheduler.validator import validate_schedule_integrity

def test_validator_detects_student_overlap():
    companies = {"C1": {"name": "Comp1", "requirements": {"min_cgpa": 7.0, "eligible_branches": ["CSE"]}}}
    students = {"S1": {"student_code": "S0001", "branch": "CSE", "cgpa": 8.0}}
    rooms = {"R1": {"room_code": "R01"}, "R2": {"room_code": "R02"}}
    panels = {"P1": {"panel_code": "P1", "company_id": "C1"}, "P2": {"panel_code": "P2", "company_id": "C1"}}

    # Same student at slot 0 in two different rooms
    interviews = [
        {"id": "IV1", "student_id": "S1", "company_id": "C1", "room_id": "R1", "panel_id": "P1", "slot_index": 0, "day_number": 1},
        {"id": "IV2", "student_id": "S1", "company_id": "C1", "room_id": "R2", "panel_id": "P2", "slot_index": 0, "day_number": 1},
    ]

    is_valid, violations, _ = validate_schedule_integrity(interviews, companies, students, rooms, panels)
    assert not is_valid
    assert any(v["type"] == "STUDENT_OVERLAP" for v in violations)

def test_validator_detects_room_overlap():
    companies = {"C1": {"name": "Comp1", "requirements": {"min_cgpa": 7.0, "eligible_branches": ["CSE"]}}}
    students = {
        "S1": {"student_code": "S0001", "branch": "CSE", "cgpa": 8.0},
        "S2": {"student_code": "S0002", "branch": "CSE", "cgpa": 8.0}
    }
    rooms = {"R1": {"room_code": "R01"}}
    panels = {"P1": {"panel_code": "P1", "company_id": "C1"}, "P2": {"panel_code": "P2", "company_id": "C1"}}

    # Two different students in the same room at the same slot
    interviews = [
        {"id": "IV1", "student_id": "S1", "company_id": "C1", "room_id": "R1", "panel_id": "P1", "slot_index": 0, "day_number": 1},
        {"id": "IV2", "student_id": "S2", "company_id": "C1", "room_id": "R1", "panel_id": "P2", "slot_index": 0, "day_number": 1},
    ]

    is_valid, violations, _ = validate_schedule_integrity(interviews, companies, students, rooms, panels)
    assert not is_valid
    assert any(v["type"] == "ROOM_OVERLAP" for v in violations)

def test_validator_detects_panel_overlap():
    companies = {"C1": {"name": "Comp1", "requirements": {"min_cgpa": 7.0, "eligible_branches": ["CSE"]}}}
    students = {
        "S1": {"student_code": "S0001", "branch": "CSE", "cgpa": 8.0},
        "S2": {"student_code": "S0002", "branch": "CSE", "cgpa": 8.0}
    }
    rooms = {"R1": {"room_code": "R01"}, "R2": {"room_code": "R02"}}
    panels = {"P1": {"panel_code": "P1", "company_id": "C1"}}

    # Same panel assigned to two interviews at same slot
    interviews = [
        {"id": "IV1", "student_id": "S1", "company_id": "C1", "room_id": "R1", "panel_id": "P1", "slot_index": 0, "day_number": 1},
        {"id": "IV2", "student_id": "S2", "company_id": "C1", "room_id": "R2", "panel_id": "P1", "slot_index": 0, "day_number": 1},
    ]

    is_valid, violations, _ = validate_schedule_integrity(interviews, companies, students, rooms, panels)
    assert not is_valid
    assert any(v["type"] == "PANEL_OVERLAP" for v in violations)

def test_validator_detects_eligibility_violation():
    companies = {"C1": {"name": "Comp1", "requirements": {"min_cgpa": 8.0, "eligible_branches": ["CSE"]}}}
    students = {"S1": {"student_code": "S0001", "branch": "MECH", "cgpa": 7.0}}  # Below CGPA and wrong branch
    rooms = {"R1": {"room_code": "R01"}}
    panels = {"P1": {"panel_code": "P1", "company_id": "C1"}}

    interviews = [
        {"id": "IV1", "student_id": "S1", "company_id": "C1", "room_id": "R1", "panel_id": "P1", "slot_index": 0, "day_number": 1}
    ]

    is_valid, violations, _ = validate_schedule_integrity(interviews, companies, students, rooms, panels)
    assert not is_valid
    assert any(v["type"] == "ELIGIBILITY_VIOLATION" for v in violations)
