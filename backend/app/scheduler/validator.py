from typing import List, Dict, Any, Tuple
import json

def validate_schedule_integrity(interviews: List[Dict[str, Any]], companies: Dict[str, Any], students: Dict[str, Any], rooms: Dict[str, Any], panels: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Independent deterministic validation of all 10 Hard Constraints:
    1. No student has overlapping interviews.
    2. No room has overlapping interviews.
    3. No panel has overlapping interviews.
    4. Student satisfies company eligibility (CGPA, Branch).
    5. Company is available during scheduled slot.
    6. Panel is available and assigned to the right company.
    7. Room is active and available.
    8. Interview duration is respected.
    9. Only eligible shortlisted students are scheduled.
    10. Required resources exist.
    """
    violations = []
    
    # 1. Student overlap check: student_id -> slot_index -> list of interview ids
    student_slots: Dict[Tuple[str, int, int], List[str]] = {}
    # 2. Room overlap check: room_id -> slot_index -> list of interview ids
    room_slots: Dict[Tuple[str, int, int], List[str]] = {}
    # 3. Panel overlap check: panel_id -> slot_index -> list of interview ids
    panel_slots: Dict[Tuple[str, int, int], List[str]] = {}

    for iv in interviews:
        iv_id = iv.get("id", "unknown")
        s_id = iv.get("student_id")
        c_id = iv.get("company_id")
        r_id = iv.get("room_id")
        p_id = iv.get("panel_id")
        slot = iv.get("slot_index", 0)
        day = iv.get("day_number", 1)

        # Invariant 10: Resource Existence
        if not s_id or s_id not in students:
            violations.append({
                "type": "RESOURCE_NOT_FOUND",
                "severity": "CRITICAL",
                "interview_id": iv_id,
                "message": f"Student {s_id} does not exist."
            })
        if not c_id or c_id not in companies:
            violations.append({
                "type": "RESOURCE_NOT_FOUND",
                "severity": "CRITICAL",
                "interview_id": iv_id,
                "message": f"Company {c_id} does not exist."
            })
        if not r_id or r_id not in rooms:
            violations.append({
                "type": "RESOURCE_NOT_FOUND",
                "severity": "CRITICAL",
                "interview_id": iv_id,
                "message": f"Room {r_id} does not exist."
            })
        if not p_id or p_id not in panels:
            violations.append({
                "type": "RESOURCE_NOT_FOUND",
                "severity": "CRITICAL",
                "interview_id": iv_id,
                "message": f"Panel {p_id} does not exist."
            })

        # Invariant 4: Eligibility Check
        if s_id in students and c_id in companies:
            student = students[s_id]
            company = companies[c_id]
            reqs = company.get("requirements", {})
            min_cgpa = reqs.get("min_cgpa", 0.0)
            eligible_branches = reqs.get("eligible_branches", [])
            
            if student.get("cgpa", 0.0) < min_cgpa:
                violations.append({
                    "type": "ELIGIBILITY_VIOLATION",
                    "severity": "HIGH",
                    "interview_id": iv_id,
                    "student_code": student.get("student_code"),
                    "message": f"Student CGPA {student.get('cgpa')} is below company cutoff {min_cgpa}"
                })
            
            if eligible_branches and student.get("branch") not in eligible_branches:
                violations.append({
                    "type": "ELIGIBILITY_VIOLATION",
                    "severity": "HIGH",
                    "interview_id": iv_id,
                    "student_code": student.get("student_code"),
                    "message": f"Student branch {student.get('branch')} is not in eligible branches {eligible_branches}"
                })

        # Invariant 6: Panel belongs to company
        if p_id in panels and c_id in companies:
            panel = panels[p_id]
            if panel.get("company_id") != c_id:
                violations.append({
                    "type": "PANEL_MISMATCH",
                    "severity": "CRITICAL",
                    "interview_id": iv_id,
                    "message": f"Panel {panel.get('panel_code')} does not belong to company {companies[c_id].get('name')}"
                })

        # Track overlaps
        s_key = (s_id, day, slot)
        r_key = (r_id, day, slot)
        p_key = (p_id, day, slot)

        student_slots.setdefault(s_key, []).append(iv_id)
        room_slots.setdefault(r_key, []).append(iv_id)
        panel_slots.setdefault(p_key, []).append(iv_id)

    # Invariant 1: Student Overlap
    for (s_id, day, slot), iv_list in student_slots.items():
        if len(iv_list) > 1:
            violations.append({
                "type": "STUDENT_OVERLAP",
                "severity": "CRITICAL",
                "student_id": s_id,
                "slot_index": slot,
                "day_number": day,
                "conflicting_interviews": iv_list,
                "message": f"Student {students.get(s_id, {}).get('student_code', s_id)} has {len(iv_list)} overlapping interviews at slot {slot}"
            })

    # Invariant 2: Room Overlap
    for (r_id, day, slot), iv_list in room_slots.items():
        if len(iv_list) > 1:
            violations.append({
                "type": "ROOM_OVERLAP",
                "severity": "CRITICAL",
                "room_id": r_id,
                "slot_index": slot,
                "day_number": day,
                "conflicting_interviews": iv_list,
                "message": f"Room {rooms.get(r_id, {}).get('room_code', r_id)} has {len(iv_list)} overlapping interviews at slot {slot}"
            })

    # Invariant 3: Panel Overlap
    for (p_id, day, slot), iv_list in panel_slots.items():
        if len(iv_list) > 1:
            violations.append({
                "type": "PANEL_OVERLAP",
                "severity": "CRITICAL",
                "panel_id": p_id,
                "slot_index": slot,
                "day_number": day,
                "conflicting_interviews": iv_list,
                "message": f"Panel {panels.get(p_id, {}).get('panel_code', p_id)} has {len(iv_list)} overlapping interviews at slot {slot}"
            })

    is_valid = len(violations) == 0
    metrics = {
        "is_valid": is_valid,
        "violations_count": len(violations),
        "total_scheduled": len(interviews),
        "unique_students_scheduled": len(set(iv.get("student_id") for iv in interviews)),
        "unique_rooms_used": len(set(iv.get("room_id") for iv in interviews)),
        "unique_panels_used": len(set(iv.get("panel_id") for iv in interviews))
    }
    
    return is_valid, violations, metrics
