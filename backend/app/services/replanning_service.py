import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.operations import Disruption, ReplanningRun, ScheduleChange, Notification
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel
from app.scheduler.solver import PlacementScheduler, TIME_SLOT_MAP
from app.scheduler.validator import validate_schedule_integrity

class ReplanningService:
    @staticmethod
    def run_replanning(
        db: Session,
        disruption_id: str,
        source_version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        disruption = db.query(Disruption).get(disruption_id)
        if not disruption:
            raise ValueError("Disruption not found")

        # 1. Fetch source version and its baseline interviews
        if not source_version_id:
            source_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
        else:
            source_version = db.query(ScheduleVersion).get(source_version_id)

        if not source_version:
            raise ValueError("Source schedule version not found")

        baseline_interviews = db.query(Interview).filter(
            Interview.schedule_version_id == source_version.id,
            Interview.status != "CANCELLED"
        ).all()
        baseline_dicts = [
            {
                "id": iv.id,
                "student_id": iv.student_id,
                "company_id": iv.company_id,
                "room_id": iv.room_id,
                "panel_id": iv.panel_id,
                "slot_index": iv.slot_index,
                "day_number": iv.day_number,
                "start_time_str": iv.start_time_str,
                "end_time_str": iv.end_time_str
            }
            for iv in baseline_interviews
        ]

        # 2. Extract disruption parameters
        params = json.loads(disruption.parameters) if disruption.parameters else {}
        delay_slots = params.get("delay_slots", 0)
        affected_panel_ids = set(params.get("affected_panel_ids", []))
        withdrawn_student_ids = set(params.get("withdrawn_student_ids", []))

        company_delays: Dict[str, int] = {}
        if disruption.event_type == "COMPANY_DELAY" and disruption.target_entity_id:
            company_delays[disruption.target_entity_id] = delay_slots

        if disruption.event_type == "PANEL_UNAVAILABLE" and disruption.target_entity_id:
            affected_panel_ids.add(disruption.target_entity_id)

        disabled_room_ids = []
        if disruption.event_type == "ROOM_UNAVAILABLE" and disruption.target_entity_id:
            disabled_room_ids.append(disruption.target_entity_id)

        if disruption.event_type in ["STUDENT_WITHDRAWAL", "STUDENT_CANCELLED_INTERVIEW"] and disruption.target_entity_id:
            withdrawn_student_ids.add(disruption.target_entity_id)

        # 3. Load DB entities
        students = db.query(Student).filter(Student.is_active == True, ~Student.id.in_(withdrawn_student_ids)).all()
        companies = db.query(Company).filter(Company.is_active == True).all()
        rooms = db.query(Room).filter(Room.is_active == True).all()
        panels = db.query(Panel).filter(Panel.is_active == True).all()
        shortlists = db.query(Shortlist).filter(~Shortlist.student_id.in_(withdrawn_student_ids), Shortlist.status != "WITHDRAWN").all()

        students_data = [
            {"id": s.id, "student_code": s.student_code, "name": s.name, "branch": s.branch, "cgpa": s.cgpa}
            for s in students
        ]
        students_lookup = {s.id: s for s in db.query(Student).all()}

        companies_data = []
        for c in companies:
            req = db.query(CompanyRequirements).filter(CompanyRequirements.company_id == c.id).first()
            branches = json.loads(req.eligible_branches) if req and req.eligible_branches else []
            min_cgpa = req.min_cgpa if req else 6.0
            
            avail = db.query(CompanyAvailability).filter(CompanyAvailability.company_id == c.id).first()
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
                "requirements": {"min_cgpa": min_cgpa, "eligible_branches": branches},
                "availability": {"start_time_slot": start_slot, "end_time_slot": end_slot}
            })

        companies_lookup = {c["id"]: c for c in companies_data}
        rooms_data = [{"id": r.id, "room_code": r.room_code, "building": r.building, "is_active": r.is_active} for r in rooms]
        rooms_lookup = {r["id"]: r for r in rooms_data}
        panels_data = [{"id": p.id, "company_id": p.company_id, "panel_code": p.panel_code, "is_active": p.is_active} for p in panels]
        panels_lookup = {p["id"]: p for p in panels_data}
        shortlists_data = [{"id": sh.id, "student_id": sh.student_id, "company_id": sh.company_id} for sh in shortlists]

        # 4. Generate 5 Recovery Strategies
        strategies_configs = [
            {
                "type": "MINIMAL_CHANGE",
                "title": "Minimal Change Recovery",
                "mode": "MINIMAL_CHANGE",
                "waiting_level": "Low",
                "explanation": "Tries to keep maximum interviews at original times, changing rooms or panels first before shifting time slots."
            },
            {
                "type": "BALANCED",
                "title": "Balanced Optimization",
                "mode": "BALANCED",
                "waiting_level": "Medium",
                "explanation": "Optimally balances high schedule stability (>90%), resource utilization, and student waiting times."
            },
            {
                "type": "STUDENT_FIRST",
                "title": "Student-First Recovery",
                "mode": "STUDENT_FIRST",
                "waiting_level": "Low",
                "explanation": "Prioritizes minimal student idle gaps and preserves student interview flow."
            },
            {
                "type": "COMPANY_FIRST",
                "title": "Company-First Recovery",
                "mode": "COMPANY_FIRST",
                "waiting_level": "Medium",
                "explanation": "Keeps company panel schedules contiguous and minimizes company schedule fragmentation."
            },
            {
                "type": "AUTO_REPLAN",
                "title": "Auto-Replan Recovery",
                "mode": "AUTO_REPLAN",
                "waiting_level": "Low",
                "explanation": "Automatically calculates optimal multi-objective recovery schedule maximizing overall score."
            }
        ]

        strategy_results = []
        strategy_interviews = {}

        for cfg in strategies_configs:
            scheduler = PlacementScheduler(
                students=students_data,
                companies=companies_data,
                rooms=rooms_data,
                panels=panels_data,
                shortlists=shortlists_data,
                num_slots=12,
                day_number=1
            )

            res = scheduler.solve(
                max_time_seconds=15,
                strategy_mode=cfg["mode"],
                baseline_interviews=baseline_dicts,
                disabled_room_ids=disabled_room_ids,
                disabled_panel_ids=list(affected_panel_ids),
                company_delays=company_delays
            )

            new_ivs = res["interviews"]
            strategy_interviews[cfg["type"]] = new_ivs
            new_map = {(iv["student_id"], iv["company_id"]): iv for iv in new_ivs}
            
            moved = 0
            unchanged = 0
            cancelled = 0
            new_assigned = 0

            for b in baseline_dicts:
                key = (b["student_id"], b["company_id"])
                if key in new_map:
                    matched = new_map[key]
                    if matched["slot_index"] == b["slot_index"] and matched["panel_id"] == b["panel_id"] and matched["room_id"] == b["room_id"]:
                        unchanged += 1
                    else:
                        moved += 1
                else:
                    cancelled += 1

            for key in new_map:
                if not any(b["student_id"] == key[0] and b["company_id"] == key[1] for b in baseline_dicts):
                    new_assigned += 1

            stability_pct = res["metrics"]["schedule_stability"]
            avg_wait = res["metrics"]["avg_student_waiting_minutes"]
            wait_lvl = res["metrics"]["waiting_level"]
            p_util = res["metrics"]["panel_utilization_pct"]
            r_util = res["metrics"]["room_utilization_pct"]
            sched_cnt = res["metrics"]["scheduled_interviews"]
            tot_possible = res["metrics"]["total_interviews"]

            # Dynamic score calculation
            s_stab = stability_pct
            s_wait = max(0.0, min(100.0, round(100.0 - (avg_wait / 180.0) * 100.0, 1)))
            s_res = round((p_util + r_util) / 2.0, 1)
            s_sched = round((sched_cnt / max(1, tot_possible)) * 100.0, 1)
            s_change = max(0.0, min(100.0, round(100.0 - (moved / max(1, len(baseline_dicts))) * 100.0, 1)))

            if cfg["type"] == "MINIMAL_CHANGE":
                score = round((0.60 * s_stab) + (0.10 * s_wait) + (0.10 * s_res) + (0.10 * s_sched) + (0.10 * s_change), 1)
            elif cfg["type"] == "STUDENT_FIRST":
                score = round((0.15 * s_stab) + (0.45 * s_wait) + (0.15 * s_res) + (0.15 * s_sched) + (0.10 * s_change), 1)
            elif cfg["type"] == "COMPANY_FIRST":
                score = round((0.25 * s_stab) + (0.15 * s_wait) + (0.30 * s_res) + (0.20 * s_sched) + (0.10 * s_change), 1)
            elif cfg["type"] == "AUTO_REPLAN":
                score = round((0.30 * s_stab) + (0.30 * s_wait) + (0.20 * s_res) + (0.10 * s_sched) + (0.10 * s_change), 1)
            else:  # BALANCED
                score = round((0.35 * s_stab) + (0.25 * s_wait) + (0.15 * s_res) + (0.15 * s_sched) + (0.10 * s_change), 1)

            strategy_results.append({
                "strategy_type": cfg["type"],
                "strategy_title": cfg["title"],
                "moved_interviews": moved,
                "unchanged_interviews": unchanged,
                "cancelled_interviews": cancelled,
                "new_assignments": new_assigned,
                "scheduled_interviews": sched_cnt,
                "unscheduled_interviews": res["metrics"]["unscheduled_interviews"],
                "stability_score": stability_pct,
                "student_waiting_minutes": avg_wait,
                "waiting_time_level": wait_lvl,
                "room_utilization_pct": r_util,
                "panel_utilization_pct": p_util,
                "overall_score": score,
                "is_recommended": False,
                "explanation": cfg["explanation"],
                "candidate_interviews": new_ivs,
                "_metrics": res["metrics"]
            })

        # Dynamically determine recommended strategy
        best_strat = max(
            strategy_results,
            key=lambda s: (s["overall_score"], s["stability_score"], -s["student_waiting_minutes"], -s["moved_interviews"])
        )
        for s in strategy_results:
            s["is_recommended"] = (s["strategy_type"] == best_strat["strategy_type"])

        recommended_strategy_type = best_strat["strategy_type"]
        recommended_opt = best_strat

        # 5. Build Diff List for All Strategies
        strategy_diffs = {}
        for s_res in strategy_results:
            stype = s_res["strategy_type"]
            s_ivs = strategy_interviews[stype]
            s_map = {(iv["student_id"], iv["company_id"]): iv for iv in s_ivs}
            s_diff = []
            for b in baseline_dicts:
                s_obj = students_lookup.get(b["student_id"])
                c_obj = companies_lookup.get(b["company_id"])
                r_obj = rooms_lookup.get(b["room_id"])
                p_obj = panels_lookup.get(b["panel_id"])

                key = (b["student_id"], b["company_id"])
                if key in s_map:
                    curr = s_map[key]
                    if curr["slot_index"] == b["slot_index"] and curr["panel_id"] == b["panel_id"] and curr["room_id"] == b["room_id"]:
                        s_diff.append({
                            "student_id": b["student_id"],
                            "student_code": s_obj.student_code if s_obj else "S0000",
                            "student_name": s_obj.name if s_obj else "Student",
                            "company_name": c_obj["name"] if c_obj else "Company",
                            "change_type": "UNCHANGED",
                            "old_time_str": b["start_time_str"],
                            "new_time_str": curr["start_time_str"],
                            "old_room_code": r_obj.get("room_code", "R01") if r_obj else "R01",
                            "new_room_code": curr["room_code"],
                            "old_panel_code": p_obj.get("panel_code", "P1") if p_obj else "P1",
                            "new_panel_code": curr["panel_code"],
                            "reason": "Retained existing slot without churn"
                        })
                    else:
                        changes = []
                        if curr["slot_index"] != b["slot_index"]:
                            changes.append(f"time slot {b['start_time_str']} -> {curr['start_time_str']}")
                        if curr["room_id"] != b["room_id"]:
                            changes.append(f"room {r_obj.get('room_code', 'R01') if r_obj else 'R01'} -> {curr['room_code']}")
                        if curr["panel_id"] != b["panel_id"]:
                            changes.append(f"panel {p_obj.get('panel_code', 'P1') if p_obj else 'P1'} -> {curr['panel_code']}")

                        reason_text = "Rescheduled: " + ", ".join(changes) + " due to disruption mitigation"
                        s_diff.append({
                            "student_id": b["student_id"],
                            "student_code": s_obj.student_code if s_obj else "S0000",
                            "student_name": s_obj.name if s_obj else "Student",
                            "company_name": c_obj["name"] if c_obj else "Company",
                            "change_type": "MOVED",
                            "old_time_str": b["start_time_str"],
                            "new_time_str": curr["start_time_str"],
                            "old_room_code": r_obj.get("room_code", "R01") if r_obj else "R01",
                            "new_room_code": curr["room_code"],
                            "old_panel_code": p_obj.get("panel_code", "P1") if p_obj else "P1",
                            "new_panel_code": curr["panel_code"],
                            "reason": reason_text
                        })
                else:
                    s_diff.append({
                        "student_id": b["student_id"],
                        "student_code": s_obj.student_code if s_obj else "S0000",
                        "student_name": s_obj.name if s_obj else "Student",
                        "company_name": c_obj["name"] if c_obj else "Company",
                        "change_type": "CANCELLED",
                        "old_time_str": b["start_time_str"],
                        "new_time_str": None,
                        "old_room_code": r_obj.get("room_code", "R01") if r_obj else "R01",
                        "new_room_code": None,
                        "old_panel_code": p_obj.get("panel_code", "P1") if p_obj else "P1",
                        "new_panel_code": None,
                        "reason": "No feasible recovery slot available"
                    })

            # Check for new assignments
            for key, curr in s_map.items():
                if not any(b["student_id"] == key[0] and b["company_id"] == key[1] for b in baseline_dicts):
                    s_obj = students_lookup.get(curr["student_id"])
                    c_obj = companies_lookup.get(curr["company_id"])
                    s_diff.append({
                        "student_id": curr["student_id"],
                        "student_code": s_obj.student_code if s_obj else "S0000",
                        "student_name": s_obj.name if s_obj else "Student",
                        "company_name": c_obj["name"] if c_obj else "Company",
                        "change_type": "NEWLY_SCHEDULED",
                        "old_time_str": None,
                        "new_time_str": curr["start_time_str"],
                        "old_room_code": None,
                        "new_room_code": curr["room_code"],
                        "old_panel_code": None,
                        "new_panel_code": curr["panel_code"],
                        "reason": "Newly assigned slot to optimize schedule post-disruption"
                    })

            s_res["diff"] = s_diff
            strategy_diffs[stype] = s_diff

        diff_list = strategy_diffs[recommended_strategy_type]

        # 6. Persist ReplanningRun and ScheduleChange records
        replan_run = ReplanningRun(
            id=str(uuid.uuid4()),
            disruption_id=disruption.id,
            source_version_id=source_version.id,
            strategy_type=recommended_strategy_type,
            strategy_score=recommended_opt["overall_score"],
            stability_score=recommended_opt["stability_score"],
            metrics=json.dumps({
                "strategies": strategy_results,
                "strategy_interviews": strategy_interviews,
                "recommended_metrics": recommended_opt["_metrics"]
            })
        )
        db.add(replan_run)
        db.flush()

        for d_item in diff_list:
            comp_id_found = next((c["id"] for c in companies_data if c["name"] == d_item["company_name"]), None) or companies_data[0]["id"]
            ch = ScheduleChange(
                id=str(uuid.uuid4()),
                replanning_run_id=replan_run.id,
                student_id=d_item["student_id"],
                company_id=comp_id_found,
                change_type=d_item["change_type"],
                old_time_str=d_item.get("old_time_str"),
                new_time_str=d_item.get("new_time_str"),
                old_room_id=d_item.get("old_room_code"),
                new_room_id=d_item.get("new_room_code"),
                reason=d_item["reason"]
            )
            db.add(ch)

        db.commit()
        db.refresh(replan_run)

        clean_strategies = [{k: v for k, v in s.items() if not k.startswith("_")} for s in strategy_results]

        return {
            "replanning_run_id": replan_run.id,
            "disruption_id": disruption.id,
            "source_version_id": source_version.id,
            "selected_strategy": recommended_strategy_type,
            "recommended_strategy": recommended_strategy_type,
            "strategies_comparison": clean_strategies,
            "diff": diff_list,
            "strategy_diffs": strategy_diffs,
            "stability_score": recommended_opt["stability_score"],
            "moved_count": recommended_opt["moved_interviews"],
            "unchanged_count": recommended_opt["unchanged_interviews"],
            "cancelled_count": recommended_opt["cancelled_interviews"],
            "metrics_after": recommended_opt["_metrics"]
        }

    @staticmethod
    def apply_replan_strategy(db: Session, replanning_run_id: str, strategy_type: str = "BALANCED") -> Dict[str, Any]:
        """
        Applies a recovery strategy by validating integrity first, creating a new active ScheduleVersion, and broadcasting notifications.
        """
        run = db.query(ReplanningRun).get(replanning_run_id)
        if not run:
            raise ValueError("Replanning run not found")

        disruption = db.query(Disruption).get(run.disruption_id)
        source_version = db.query(ScheduleVersion).get(run.source_version_id)
        schedule = db.query(Schedule).get(source_version.schedule_id)

        baseline_interviews = db.query(Interview).filter(
            Interview.schedule_version_id == source_version.id,
            Interview.status != "CANCELLED"
        ).all()
        baseline_dicts = [
            {
                "id": iv.id, "student_id": iv.student_id, "company_id": iv.company_id,
                "room_id": iv.room_id, "panel_id": iv.panel_id, "slot_index": iv.slot_index,
                "day_number": iv.day_number, "start_time_str": iv.start_time_str, "end_time_str": iv.end_time_str
            } for iv in baseline_interviews
        ]

        run_metrics = json.loads(run.metrics) if run.metrics else {}
        strategy_ivs_map = run_metrics.get("strategy_interviews", {})
        planned_ivs = strategy_ivs_map.get(strategy_type, [])

        if not planned_ivs:
            for s in run_metrics.get("strategies", []):
                if s.get("strategy_type") == strategy_type or s.get("is_recommended"):
                    planned_ivs = s.get("candidate_interviews", [])
                    if planned_ivs:
                        break

        if not planned_ivs:
            # Fallback: re-solve strategy if metrics payload lacked cached interviews
            params = json.loads(disruption.parameters) if disruption and disruption.parameters else {}
            delay_slots = params.get("delay_slots", 0)
            affected_panel_ids = set(params.get("affected_panel_ids", []))
            withdrawn_student_ids = set(params.get("withdrawn_student_ids", []))

            company_delays: Dict[str, int] = {}
            if disruption and disruption.event_type == "COMPANY_DELAY" and disruption.target_entity_id:
                company_delays[disruption.target_entity_id] = delay_slots
            if disruption and disruption.event_type == "PANEL_UNAVAILABLE" and disruption.target_entity_id:
                affected_panel_ids.add(disruption.target_entity_id)

            disabled_room_ids = []
            if disruption and disruption.event_type == "ROOM_UNAVAILABLE" and disruption.target_entity_id:
                disabled_room_ids.append(disruption.target_entity_id)

            baseline_interviews = db.query(Interview).filter(
                Interview.schedule_version_id == source_version.id,
                Interview.status != "CANCELLED"
            ).all()
            baseline_dicts = [
                {
                    "id": iv.id, "student_id": iv.student_id, "company_id": iv.company_id,
                    "room_id": iv.room_id, "panel_id": iv.panel_id, "slot_index": iv.slot_index,
                    "day_number": iv.day_number, "start_time_str": iv.start_time_str, "end_time_str": iv.end_time_str
                } for iv in baseline_interviews
            ]

            students = db.query(Student).filter(Student.is_active == True, ~Student.id.in_(withdrawn_student_ids)).all()
            companies = db.query(Company).filter(Company.is_active == True).all()
            rooms = db.query(Room).filter(Room.is_active == True).all()
            panels = db.query(Panel).filter(Panel.is_active == True).all()
            shortlists = db.query(Shortlist).filter(~Shortlist.student_id.in_(withdrawn_student_ids), Shortlist.status != "WITHDRAWN").all()

            scheduler = PlacementScheduler(
                students=[{"id": s.id, "student_code": s.student_code, "name": s.name, "branch": s.branch, "cgpa": s.cgpa} for s in students],
                companies=[{"id": c.id, "company_code": c.company_code, "name": c.name, "priority_tier": c.priority_tier} for c in companies],
                rooms=[{"id": r.id, "room_code": r.room_code, "building": r.building, "is_active": r.is_active} for r in rooms],
                panels=[{"id": p.id, "company_id": p.company_id, "panel_code": p.panel_code, "is_active": p.is_active} for p in panels],
                shortlists=[{"id": sh.id, "student_id": sh.student_id, "company_id": sh.company_id} for sh in shortlists]
            )
            res = scheduler.solve(
                max_time_seconds=10,
                strategy_mode=strategy_type,
                baseline_interviews=baseline_dicts,
                disabled_room_ids=disabled_room_ids,
                disabled_panel_ids=list(affected_panel_ids),
                company_delays=company_delays
            )
            planned_ivs = res["interviews"]

        if not planned_ivs:
            raise ValueError(f"No planned interviews available for strategy {strategy_type}")

        # 1. TRANSACTION SAFETY VALIDATION
        # Validate proposed schedule against hard constraints before modifying database
        students_dict = {s.id: {"id": s.id, "name": s.name, "branch": s.branch, "cgpa": s.cgpa} for s in db.query(Student).all()}
        companies_dict = {c.id: {"id": c.id, "name": c.name} for c in db.query(Company).all()}
        rooms_dict = {r.id: {"id": r.id, "room_code": r.room_code} for r in db.query(Room).all()}
        panels_dict = {p.id: {"id": p.id, "panel_code": p.panel_code, "company_id": p.company_id} for p in db.query(Panel).all()}

        is_valid, violations, val_metrics = validate_schedule_integrity(
            planned_ivs, companies_dict, students_dict, rooms_dict, panels_dict
        )

        if not is_valid:
            violation_msgs = [v.get("message", str(v)) if isinstance(v, dict) else str(v) for v in violations]
            raise ValueError(f"Schedule validation failed for strategy {strategy_type}: {', '.join(violation_msgs)}")

        if disruption:
            disruption.status = "APPLIED"

        last_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
        new_version_num = last_version.version_number + 1

        new_version = ScheduleVersion(
            id=str(uuid.uuid4()),
            schedule_id=schedule.id,
            version_number=new_version_num,
            stability_score=run.stability_score,
            metrics_snapshot=json.dumps(run_metrics.get("recommended_metrics", {}))
        )
        db.add(new_version)
        db.flush()

        run.resulting_version_id = new_version.id
        run.is_selected = True

        changes = db.query(ScheduleChange).filter(ScheduleChange.replanning_run_id == run.id).all()
        moved_keys = {(ch.student_id, ch.company_id) for ch in changes if ch.change_type in ["MOVED", "NEWLY_SCHEDULED"]}
        cancelled_keys = {(ch.student_id, ch.company_id) for ch in changes if ch.change_type == "CANCELLED"}

        baseline_map = {(b["student_id"], b["company_id"]): b for b in baseline_dicts}
        planned_map = {(iv["student_id"], iv["company_id"]): iv for iv in planned_ivs}

        # 1. Save planned interviews from the solve with RESCHEDULED / SCHEDULED status
        for iv in planned_ivs:
            key = (iv["student_id"], iv["company_id"])
            baseline_iv = baseline_map.get(key)
            is_moved = key in moved_keys
            if baseline_iv and not is_moved:
                if (baseline_iv["slot_index"] != iv["slot_index"] or 
                    baseline_iv["room_id"] != iv["room_id"] or 
                    baseline_iv["panel_id"] != iv["panel_id"]):
                    is_moved = True
            elif not baseline_iv:
                is_moved = True

            db_iv = Interview(
                id=str(uuid.uuid4()),
                schedule_version_id=new_version.id,
                student_id=iv["student_id"],
                company_id=iv["company_id"],
                room_id=iv["room_id"],
                panel_id=iv["panel_id"],
                day_number=iv.get("day_number", 1),
                slot_index=iv["slot_index"],
                start_time_str=iv["start_time_str"],
                end_time_str=iv["end_time_str"],
                status="RESCHEDULED" if is_moved else "SCHEDULED",
                audit_metadata=json.dumps({
                    "strategy_applied": strategy_type,
                    "replan_reason": f"Rescheduled via {strategy_type} recovery strategy" if is_moved else None
                })
            )
            db.add(db_iv)

        # 2. Add interviews from baseline that were CANCELLED in this replanning run
        processed_cancelled_keys = set()
        for b in baseline_dicts:
            key = (b["student_id"], b["company_id"])
            if key not in planned_map:
                processed_cancelled_keys.add(key)
                db_iv = Interview(
                    id=str(uuid.uuid4()),
                    schedule_version_id=new_version.id,
                    student_id=b["student_id"],
                    company_id=b["company_id"],
                    room_id=b["room_id"],
                    panel_id=b["panel_id"],
                    day_number=b.get("day_number", 1),
                    slot_index=b["slot_index"],
                    start_time_str=b["start_time_str"],
                    end_time_str=b["end_time_str"],
                    status="CANCELLED",
                    audit_metadata=json.dumps({
                        "strategy_applied": strategy_type,
                        "replan_reason": f"Cancelled during {strategy_type} recovery strategy / disruption"
                    })
                )
                db.add(db_iv)

        # 3. Copy existing cancelled interviews from source version
        source_cancelled = db.query(Interview).filter(
            Interview.schedule_version_id == source_version.id,
            Interview.status == "CANCELLED"
        ).all()
        for sc_iv in source_cancelled:
            key = (sc_iv.student_id, sc_iv.company_id)
            if key not in processed_cancelled_keys:
                db_iv = Interview(
                    id=str(uuid.uuid4()),
                    schedule_version_id=new_version.id,
                    student_id=sc_iv.student_id,
                    company_id=sc_iv.company_id,
                    room_id=sc_iv.room_id,
                    panel_id=sc_iv.panel_id,
                    day_number=sc_iv.day_number,
                    slot_index=sc_iv.slot_index,
                    start_time_str=sc_iv.start_time_str,
                    end_time_str=sc_iv.end_time_str,
                    status="CANCELLED",
                    audit_metadata=sc_iv.audit_metadata
                )
                db.add(db_iv)

        # Create notifications for changes
        changes = db.query(ScheduleChange).filter(ScheduleChange.replanning_run_id == run.id, ScheduleChange.change_type == "MOVED").all()
        for ch in changes:
            student = db.query(Student).get(ch.student_id)
            comp = db.query(Company).get(ch.company_id)
            if student:
                notif = Notification(
                    id=str(uuid.uuid4()),
                    user_id=student.user_id,
                    title="Interview Rescheduled",
                    message=f"Your interview with {comp.name if comp else 'Company'} moved from {ch.old_time_str} to {ch.new_time_str}. Reason: {ch.reason}",
                    category="SCHEDULE_CHANGE"
                )
                db.add(notif)

        db.commit()
        db.refresh(new_version)

        return {
            "status": "APPLIED",
            "new_schedule_version_id": new_version.id,
            "resulting_version_id": new_version.id,
            "version_number": new_version.version_number,
            "stability_score": new_version.stability_score
        }

    apply_strategy = apply_replan_strategy
