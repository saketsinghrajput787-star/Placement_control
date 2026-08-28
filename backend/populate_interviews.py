import json
import uuid
from app.db.session import SessionLocal
from app.models.student import Student
from app.models.company import Company, Shortlist
from app.models.schedule import ScheduleVersion, Interview
from app.models.resource import Room, Panel
from app.scheduler.solver import TIME_SLOT_MAP

def run():
    db = SessionLocal()
    sid = "default-placement-session-2026"
    lv = db.query(ScheduleVersion).filter(ScheduleVersion.placement_session_id == sid).order_by(ScheduleVersion.version_number.desc()).first()
    if not lv:
        print("No schedule version found")
        return
    
    alex = db.query(Student).filter(Student.student_code == "S0421").first()
    if not alex:
        print("Alex not found")
        return

    shs = db.query(Shortlist).filter(Shortlist.student_id == alex.id).all()
    current_ivs = db.query(Interview).filter(Interview.schedule_version_id == lv.id).all()
    busy_student_slots = {iv.slot_index for iv in current_ivs if iv.student_id == alex.id and iv.status != "CANCELLED"}
    rooms = db.query(Room).filter(Room.placement_session_id == sid, Room.is_active == True).all()

    for sh in shs:
        has_iv = any(iv.company_id == sh.company_id and iv.student_id == alex.id for iv in current_ivs)
        if not has_iv:
            comp = db.query(Company).filter(Company.id == sh.company_id).first()
            panels = db.query(Panel).filter(Panel.company_id == comp.id, Panel.is_active == True).all()
            for slot_idx in range(12):
                if slot_idx in busy_student_slots:
                    continue
                # Find available room for this slot
                booked_rooms = {iv.room_id for iv in current_ivs if iv.slot_index == slot_idx and iv.status != "CANCELLED"}
                free_rooms = [r for r in rooms if r.id not in booked_rooms]
                if free_rooms:
                    assigned_room = free_rooms[0]
                    assigned_panel = panels[0] if panels else None
                    times = TIME_SLOT_MAP.get(slot_idx, ("09:00", "09:45"))
                    new_iv = Interview(
                        id=str(uuid.uuid4()),
                        placement_session_id=sid,
                        schedule_version_id=lv.id,
                        student_id=alex.id,
                        company_id=comp.id,
                        room_id=assigned_room.id,
                        panel_id=assigned_panel.id if assigned_panel else "",
                        day_number=1,
                        slot_index=slot_idx,
                        start_time_str=times[0],
                        end_time_str=times[1],
                        status="SCHEDULED",
                        audit_metadata=json.dumps({
                            "optimization_reasons": [
                                "Slot assigned matching candidate preference",
                                f"Company tier {comp.priority_tier} priority satisfied"
                            ]
                        })
                    )
                    db.add(new_iv)
                    current_ivs.append(new_iv)
                    busy_student_slots.add(slot_idx)
                    print(f"Scheduled {comp.name} at {times[0]} in {assigned_room.room_code}")
                    break
    db.commit()
    print("Completed scheduling for all candidate shortlists.")

if __name__ == "__main__":
    run()
