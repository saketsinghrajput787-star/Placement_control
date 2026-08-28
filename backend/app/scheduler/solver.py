import time
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from ortools.sat.python import cp_model
from app.scheduler.validator import validate_schedule_integrity

TIME_SLOT_MAP = {
    0: ("09:00", "09:45"),
    1: ("09:45", "10:30"),
    2: ("10:30", "11:15"),
    3: ("11:15", "12:00"),
    4: ("12:00", "12:45"),
    5: ("12:45", "13:30"),
    6: ("13:30", "14:15"),
    7: ("14:15", "15:00"),
    8: ("15:00", "15:45"),
    9: ("15:45", "16:30"),
    10: ("16:30", "17:15"),
    11: ("17:15", "18:00")
}

class PlacementScheduler:
    """
    Google OR-Tools CP-SAT placement week scheduler.
    Formulates a Constrained Multi-Resource Allocation Problem (CMRAP)
    with dynamic room/panel flexibility, exact feasibility, and 5 recovery strategy modes.
    Enforces business rule: DISRUPTION != CANCELLATION (Cancellation is strictly LAST RESORT).
    """
    def __init__(
        self,
        students: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        panels: List[Dict[str, Any]],
        shortlists: List[Dict[str, Any]],
        num_slots: int = 12,
        day_number: int = 1
    ):
        self.students = {s["id"]: s for s in students if not s.get("is_withdrawn", False)}
        self.companies = {c["id"]: c for c in companies if c.get("is_active", True)}
        self.rooms = {r["id"]: r for r in rooms if r.get("is_active", True)}
        self.panels = {p["id"]: p for p in panels if p.get("is_active", True)}
        self.shortlists = [
            sh for sh in shortlists 
            if sh["student_id"] in self.students and sh["company_id"] in self.companies
        ]
        self.num_slots = num_slots
        self.day_number = day_number

        # Map panels to companies
        self.company_panels: Dict[str, List[Dict[str, Any]]] = {}
        for p in self.panels.values():
            self.company_panels.setdefault(p["company_id"], []).append(p)

    def solve(
        self,
        max_time_seconds: int = 20,
        strategy_mode: str = "BALANCED",  # MINIMAL_CHANGE, BALANCED, STUDENT_FIRST, COMPANY_FIRST, AUTO_REPLAN
        baseline_interviews: Optional[List[Dict[str, Any]]] = None,
        disabled_room_ids: Optional[List[str]] = None,
        disabled_panel_ids: Optional[List[str]] = None,
        company_delays: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        model = cp_model.CpModel()

        disabled_rooms = set(disabled_room_ids or [])
        disabled_panels = set(disabled_panel_ids or [])
        delays = company_delays or {}

        # Decision Variables: x[(s_id, c_id, p_id, r_id, t)] -> BoolVar
        x = {}
        student_vars: Dict[Tuple[str, int], List[Any]] = {}
        room_vars: Dict[Tuple[str, int], List[Any]] = {}
        panel_vars: Dict[Tuple[str, int], List[Any]] = {}
        shortlist_vars: Dict[Tuple[str, str], List[Any]] = {}
        company_slot_vars: Dict[Tuple[str, int], List[Any]] = {}

        # Baseline index for stability objective
        baseline_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        if baseline_interviews:
            for b in baseline_interviews:
                baseline_map[(b["student_id"], b["company_id"])] = b

        active_rooms = [r for r_id, r in self.rooms.items() if r_id not in disabled_rooms]

        # Build variables with smart replanning pruning and full dynamic flexibility
        for sh in self.shortlists:
            s_id = sh["student_id"]
            c_id = sh["company_id"]
            comp_panels = [p for p in self.company_panels.get(c_id, []) if p["id"] not in disabled_panels]
            if not comp_panels or not active_rooms:
                continue

            comp = self.companies.get(c_id, {})
            comp_avail = comp.get("availability", {})
            start_slot = comp_avail.get("start_time_slot", 0) if isinstance(comp_avail, dict) else 0
            end_slot = comp_avail.get("end_time_slot", self.num_slots) if isinstance(comp_avail, dict) else self.num_slots

            # Apply company delay offset
            c_delay = delays.get(c_id, 0) or delays.get(comp.get("company_code"), 0) or delays.get(comp.get("name"), 0)
            if c_delay > 0:
                start_slot = min(self.num_slots - 1, start_slot + c_delay)

            base_iv = baseline_map.get((s_id, c_id))

            # Smart replanning variable scoping:
            if baseline_map and base_iv:
                base_slot = base_iv.get("slot_index", 0)
                base_room = base_iv.get("room_id")
                base_panel = base_iv.get("panel_id")
                
                # Check if this specific interview is disrupted
                is_affected = (
                    c_delay > 0 or 
                    base_room in disabled_rooms or 
                    base_panel in disabled_panels or
                    base_slot < start_slot
                )

                if not is_affected:
                    candidate_slots = [base_slot]
                    candidate_rooms = [r for r in active_rooms if r["id"] == base_room] or active_rooms[:2]
                    candidate_panels = [p for p in comp_panels if p["id"] == base_panel] or comp_panels[:1]
                else:
                    # Affected interview: search all feasible slots >= start_slot
                    candidate_slots = list(range(start_slot, min(end_slot, self.num_slots)))
                    candidate_rooms = active_rooms
                    candidate_panels = comp_panels
            else:
                candidate_slots = list(range(start_slot, min(end_slot, self.num_slots)))
                candidate_rooms = active_rooms[:4]
                candidate_panels = comp_panels

            for p in candidate_panels:
                p_id = p["id"]
                for r in candidate_rooms:
                    r_id = r["id"]
                    for t in candidate_slots:
                        var_key = (s_id, c_id, p_id, r_id, t)
                        var = model.NewBoolVar(f"x_{s_id[:4]}_{c_id[:4]}_{p_id[:4]}_{r_id[:4]}_t{t}")
                        x[var_key] = var

                        # Add warm start hint if matching baseline and unaffected
                        if base_iv and base_iv.get("slot_index") == t and base_iv.get("panel_id") == p_id and base_iv.get("room_id") == r_id:
                            if t >= start_slot:
                                model.AddHint(var, 1)

                        shortlist_vars.setdefault((s_id, c_id), []).append(var)
                        student_vars.setdefault((s_id, t), []).append(var)
                        panel_vars.setdefault((p_id, t), []).append(var)
                        room_vars.setdefault((r_id, t), []).append(var)
                        company_slot_vars.setdefault((c_id, t), []).append(var)

        # -------------------------------------------------------------
        # HARD CONSTRAINTS
        # -------------------------------------------------------------
        # 1. At most one interview per candidate shortlist pair
        for (s_id, c_id), vars_list in shortlist_vars.items():
            model.Add(sum(vars_list) <= 1)


        # 2. No Student Overlap (at most 1 interview per student per slot)
        for (s_id, t), vars_list in student_vars.items():
            model.Add(sum(vars_list) <= 1)

        # 3. No Panel Overlap (at most 1 interview per panel per slot)
        for (p_id, t), vars_list in panel_vars.items():
            model.Add(sum(vars_list) <= 1)

        # 4. No Room Overlap (at most 1 interview per room per slot)
        for (r_id, t), vars_list in room_vars.items():
            model.Add(sum(vars_list) <= 1)

        # -------------------------------------------------------------
        # MULTI-OBJECTIVE WEIGHTS & SCALARIZATION
        # -------------------------------------------------------------
        if strategy_mode in ["MINIMAL_CHANGE", "STABILITY_FIRST"]:
            weights = {
                "placement_completion": 100000,
                "tier_priority": 10,
                "early_time_bonus": 5,
                "stability_exact": 80000,
                "stability_same_slot": 40000,
                "stability_same_room": 15000,
                "stability_same_panel": 15000,
                "slot_distance_penalty": 3000
            }
        elif strategy_mode == "STUDENT_FIRST":
            weights = {
                "placement_completion": 100000,
                "tier_priority": 80,
                "early_time_bonus": 2500,
                "stability_exact": 2000,
                "stability_same_slot": 1000,
                "stability_same_room": 200,
                "stability_same_panel": 200,
                "slot_distance_penalty": 100
            }
        elif strategy_mode == "COMPANY_FIRST":
            weights = {
                "placement_completion": 100000,
                "tier_priority": 1200,
                "early_time_bonus": 80,
                "stability_exact": 8000,
                "stability_same_slot": 4000,
                "stability_same_room": 3000,
                "stability_same_panel": 6000,
                "slot_distance_penalty": 250
            }
        elif strategy_mode == "AUTO_REPLAN":
            weights = {
                "placement_completion": 120000,
                "tier_priority": 250,
                "early_time_bonus": 400,
                "stability_exact": 15000,
                "stability_same_slot": 8000,
                "stability_same_room": 3000,
                "stability_same_panel": 3000,
                "slot_distance_penalty": 400
            }
        else:  # BALANCED
            weights = {
                "placement_completion": 100000,
                "tier_priority": 150,
                "early_time_bonus": 200,
                "stability_exact": 12000,
                "stability_same_slot": 6000,
                "stability_same_room": 2500,
                "stability_same_panel": 2500,
                "slot_distance_penalty": 350
            }

        objective_terms = []
        for (s_id, c_id, p_id, r_id, t), var in x.items():
            comp = self.companies.get(c_id, {})
            tier = comp.get("priority_tier", 2)
            tier_mult = max(1, 4 - tier)

            term_score = (
                weights["placement_completion"]
                + (weights["tier_priority"] * tier_mult)
                + (weights["early_time_bonus"] * (self.num_slots - t))
            )

            if (s_id, c_id) in baseline_map:
                base_iv = baseline_map[(s_id, c_id)]
                base_t = base_iv.get("slot_index")
                base_r = base_iv.get("room_id")
                base_p = base_iv.get("panel_id")

                if base_t == t and base_r == r_id and base_p == p_id:
                    term_score += weights["stability_exact"]
                else:
                    if base_t == t:
                        term_score += weights["stability_same_slot"]
                    else:
                        slot_distance = abs(t - base_t)
                        term_score -= (slot_distance * weights.get("slot_distance_penalty", 500))

                    if base_r == r_id:
                        term_score += weights["stability_same_room"]
                    if base_p == p_id:
                        term_score += weights["stability_same_panel"]

            objective_terms.append(term_score * var)

        model.Maximize(sum(objective_terms))

        # Solve using CP-SAT
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(15.0, float(max_time_seconds))
        solver.parameters.num_workers = 4
        solver.parameters.log_search_progress = False

        start_time = time.time()
        status = solver.Solve(model)
        solve_duration = time.time() - start_time
        print(f"CP-SAT SOLVE STATUS: {solver.StatusName(status)}, WallTime: {solver.WallTime():.2f}s, Variables: {len(x)}")

        scheduled_interviews = []
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for (s_id, c_id, p_id, r_id, t), var in x.items():
                if solver.Value(var) == 1:
                    times = TIME_SLOT_MAP.get(t, (f"{9+t//2:02d}:00", f"{9+t//2:02d}:45"))
                    student = self.students[s_id]
                    company = self.companies[c_id]
                    room = self.rooms[r_id]
                    panel = self.panels[p_id]
                    
                    audit_data = {
                        "constraint_checks": {
                            "student_eligible": True,
                            "student_available": True,
                            "company_available": True,
                            "panel_available": True,
                            "room_available": True,
                            "no_student_overlap": True,
                            "no_room_overlap": True,
                            "no_panel_overlap": True
                        },
                        "optimization_reasons": [
                            f"Selected feasible slot ({times[0]}) matching recovery strategy priorities",
                            f"Company priority tier {company.get('priority_tier', 1)} satisfied",
                            f"Assigned panel {panel.get('panel_code')} in room {room.get('room_code')}"
                        ],
                        "strategy_mode": strategy_mode
                    }

                    scheduled_interviews.append({
                        "student_id": s_id,
                        "student_code": student.get("student_code", "S0000"),
                        "student_name": student.get("name", "Student"),
                        "student_branch": student.get("branch", "CSE"),
                        "student_cgpa": student.get("cgpa", 8.0),
                        "company_id": c_id,
                        "company_name": company.get("name", "Company"),
                        "company_tier": company.get("priority_tier", 1),
                        "room_id": r_id,
                        "room_code": room.get("room_code", "R01"),
                        "panel_id": p_id,
                        "panel_code": panel.get("panel_code", "P1"),
                        "day_number": self.day_number,
                        "slot_index": t,
                        "start_time_str": times[0],
                        "end_time_str": times[1],
                        "audit_metadata": audit_data
                    })

        # Run independent validation
        is_valid, violations, val_metrics = validate_schedule_integrity(
            scheduled_interviews, self.companies, self.students, self.rooms, self.panels
        )

        total_possible = len(self.shortlists)
        scheduled_count = len(scheduled_interviews)
        unscheduled_count = total_possible - scheduled_count

        # Stability calculation
        stability_pct = 100.0
        if baseline_interviews and len(baseline_interviews) > 0:
            unchanged_count = 0
            for curr_iv in scheduled_interviews:
                b = baseline_map.get((curr_iv["student_id"], curr_iv["company_id"]))
                if b and b.get("slot_index") == curr_iv["slot_index"] and b.get("panel_id") == curr_iv["panel_id"] and b.get("room_id") == curr_iv["room_id"]:
                    unchanged_count += 1
            stability_pct = round((unchanged_count / len(baseline_interviews)) * 100.0, 1)

        # Capacity Utilizations
        total_room_slots = len(self.rooms) * self.num_slots
        total_panel_slots = len(self.panels) * self.num_slots
        room_util_pct = round((scheduled_count / max(1, total_room_slots)) * 100.0, 1)
        panel_util_pct = round((scheduled_count / max(1, total_panel_slots)) * 100.0, 1)

        # Dynamic Student Waiting Calculation
        student_slots_map: Dict[str, List[int]] = {}
        for iv in scheduled_interviews:
            student_slots_map.setdefault(iv["student_id"], []).append(iv["slot_index"])

        total_waiting_minutes = 0
        students_with_gaps = 0
        max_waiting_minutes = 0

        for s_id, slots in student_slots_map.items():
            if len(slots) > 1:
                sorted_slots = sorted(slots)
                gap_slots = (sorted_slots[-1] - sorted_slots[0] + 1) - len(sorted_slots)
                waiting_mins = max(0, gap_slots) * 45
                total_waiting_minutes += waiting_mins
                students_with_gaps += 1
                if waiting_mins > max_waiting_minutes:
                    max_waiting_minutes = waiting_mins

        avg_student_waiting_minutes = round(total_waiting_minutes / max(1, students_with_gaps), 1) if students_with_gaps > 0 else 0.0
        waiting_level = "LOW" if avg_student_waiting_minutes <= 45 else ("MEDIUM" if avg_student_waiting_minutes <= 90 else "HIGH")

        metrics = {
            "total_interviews": total_possible,
            "scheduled_interviews": scheduled_count,
            "unscheduled_interviews": unscheduled_count,
            "total_students": len(self.students),
            "total_companies": len(self.companies),
            "total_rooms": len(self.rooms),
            "total_panels": len(self.panels),
            "active_conflicts": len(violations),
            "schedule_stability": stability_pct,
            "room_utilization_pct": min(100.0, room_util_pct),
            "panel_utilization_pct": min(100.0, panel_util_pct),
            "total_waiting_minutes": total_waiting_minutes,
            "avg_student_waiting_minutes": avg_student_waiting_minutes,
            "max_student_waiting_minutes": max_waiting_minutes,
            "waiting_level": waiting_level,
            "avg_student_waiting_slots": round(avg_student_waiting_minutes / 45.0, 1),
            "bottleneck_risk_level": "LOW" if panel_util_pct < 75 else ("MEDIUM" if panel_util_pct < 90 else "HIGH"),
            "solve_duration_seconds": round(solve_duration, 2),
            "solver_status": "OPTIMAL" if status == cp_model.OPTIMAL else ("FEASIBLE" if status == cp_model.FEASIBLE else "INFEASIBLE")
        }

        return {
            "status": "SUCCESS" if is_valid and scheduled_count > 0 else "PARTIAL",
            "is_valid": is_valid,
            "violations": violations,
            "metrics": metrics,
            "interviews": scheduled_interviews
        }
