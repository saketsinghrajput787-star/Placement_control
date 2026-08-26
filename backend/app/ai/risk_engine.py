from typing import List, Dict, Any

class BottleneckRiskEngine:
    """
    Deterministic risk and bottleneck computation engine.
    Analyzes panel capacity, room saturation, interview density, and student contention.
    """
    @staticmethod
    def calculate_bottlenecks(
        interviews: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        panels: List[Dict[str, Any]],
        num_slots: int = 12
    ) -> List[Dict[str, Any]]:
        bottlenecks = []
        
        # 1. Group interviews by company and slot
        comp_slot_counts: Dict[str, Dict[int, int]] = {}
        room_slot_counts: Dict[str, Dict[int, int]] = {}
        slot_density: Dict[int, int] = {t: 0 for t in range(num_slots)}

        for iv in interviews:
            c_id = iv["company_id"]
            r_id = iv["room_id"]
            slot = iv["slot_index"]
            comp_slot_counts.setdefault(c_id, {}).setdefault(slot, 0)
            comp_slot_counts[c_id][slot] += 1
            room_slot_counts.setdefault(r_id, {}).setdefault(slot, 0)
            room_slot_counts[r_id][slot] += 1
            slot_density[slot] = slot_density.get(slot, 0) + 1

        comp_dict = {c["id"]: c for c in companies}
        panel_counts = {}
        for p in panels:
            panel_counts[p["company_id"]] = panel_counts.get(p["company_id"], 0) + 1

        # Check company panel pressure
        for c_id, slot_map in comp_slot_counts.items():
            comp = comp_dict.get(c_id, {})
            max_panels = max(1, panel_counts.get(c_id, comp.get("max_panels", 2)))
            
            for slot, count in slot_map.items():
                util_pct = round((count / max_panels) * 100.0, 1)
                if util_pct >= 80:
                    start_hour = 9 + slot // 2
                    start_min = "00" if (slot % 2 == 0) else "45"
                    end_hour = 9 + (slot + 1) // 2
                    end_min = "00" if ((slot + 1) % 2 == 0) else "45"
                    time_str = f"{start_hour:02d}:{start_min}–{end_hour:02d}:{end_min}"
                    
                    risk = "CRITICAL" if util_pct >= 100 else ("HIGH" if util_pct >= 90 else "MEDIUM")
                    bottlenecks.append({
                        "time_window": time_str,
                        "entity_name": comp.get("name", "Company"),
                        "entity_type": "company",
                        "utilization_pct": util_pct,
                        "risk_level": risk,
                        "reason": f"Panel capacity is running at {util_pct}% ({count}/{max_panels} panels active)",
                        "suggested_action": "Maintain standby interviewer panel or allocate adjacent slot overflow"
                    })

        # Check overall peak density windows
        total_rooms = max(1, len(rooms))
        for slot, count in slot_density.items():
            room_util = round((count / total_rooms) * 100.0, 1)
            if room_util >= 85:
                start_hour = 9 + slot // 2
                start_min = "00" if (slot % 2 == 0) else "45"
                end_hour = 9 + (slot + 1) // 2
                end_min = "00" if ((slot + 1) % 2 == 0) else "45"
                bottlenecks.append({
                    "time_window": f"{start_hour:02d}:{start_min}–{end_hour:02d}:{end_min}",
                    "entity_name": "Campus Room Infrastructure",
                    "entity_type": "room_cluster",
                    "utilization_pct": room_util,
                    "risk_level": "HIGH" if room_util >= 90 else "MEDIUM",
                    "reason": f"Peak campus room utilization at {room_util}% ({count}/{total_rooms} rooms in use)",
                    "suggested_action": "Ensure video conferencing bandwidth and on-ground corridor flow management"
                })

        return bottlenecks
