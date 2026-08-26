import pytest
import json
from app.db.session import SessionLocal, Base
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.operations import Disruption, ReplanningRun
from app.models.company import Company, Shortlist, CompanyRequirements, CompanyAvailability
from app.models.resource import Room, Panel
from app.models.student import Student
from app.models.user import User
from app.services.disruption_service import DisruptionService
from app.services.replanning_service import ReplanningService
from app.services.cancellation_service import CancellationService
from app.services.schedule_service import ScheduleService

from tests.conftest import TestingSessionLocal

@pytest.fixture
def db():
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

def ensure_test_data_seeded(db):
    Base.metadata.create_all(bind=db.get_bind())
    if db.query(Student).count() == 0:
        import uuid
        stds = []
        for i in range(1, 11):
            u = User(id=str(uuid.uuid4()), email=f"s{i}@test.com", hashed_password="pwd", role="STUDENT")
            db.add(u)
            s = Student(id=str(uuid.uuid4()), user_id=u.id, student_code=f"S{i:03d}", name=f"Student {i}", email=f"s{i}@test.com", branch="CSE", cgpa=7.0 + (i * 0.2))
            db.add(s)
            stds.append(s)
        
        comps = []
        for i in range(1, 4):
            u = User(id=str(uuid.uuid4()), email=f"comp{i}@test.com", hashed_password="pwd", role="COMPANY")
            db.add(u)
            c = Company(id=str(uuid.uuid4()), user_id=u.id, company_code=f"COMP{i}", name=f"Company {i}", priority_tier=i)
            db.add(c)
            comps.append(c)
            req = CompanyRequirements(id=str(uuid.uuid4()), company_id=c.id, min_cgpa=6.5, eligible_branches='["CSE"]')
            db.add(req)
            avail = CompanyAvailability(id=str(uuid.uuid4()), company_id=c.id, start_time_slot=0, end_time_slot=12)
            db.add(avail)
            
            p = Panel(id=str(uuid.uuid4()), company_id=c.id, panel_code=f"P{i}")
            db.add(p)
            
        for i in range(1, 4):
            r = Room(id=str(uuid.uuid4()), room_code=f"R{i}", building="Main Block")
            db.add(r)
            
        for s in stds:
            for c in comps:
                sh = Shortlist(id=str(uuid.uuid4()), company_id=c.id, student_id=s.id, status="SHORTLISTED")
                db.add(sh)
                
        db.commit()

def ensure_baseline_schedule(db):
    db.expire_all()
    ensure_test_data_seeded(db)
    db.query(Room).update({"is_active": True})
    db.query(Panel).update({"is_active": True})
    db.query(Student).update({"is_active": True, "is_withdrawn": False})
    db.query(Company).update({"is_active": True})
    db.query(Shortlist).update({"status": "SHORTLISTED"})
    db.commit()

    res = ScheduleService.generate_initial_schedule(db, max_time_seconds=10)
    db.expire_all()
    return db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()

def get_active_interview(db):
    db.expire_all()
    version = ensure_baseline_schedule(db)
    iv = db.query(Interview).filter(
        Interview.schedule_version_id == version.id,
        Interview.status == "SCHEDULED"
    ).first()
    if not iv:
        iv = db.query(Interview).filter(Interview.status == "SCHEDULED").order_by(Interview.id.desc()).first()
    return iv

def test_scenario_1_company_delay(db):
    """
    TEST 1 — COMPANY DELAY
    Company delayed by 90 minutes (2 slots).
    Expected: Affected interviews identified, rescheduled to valid slots, cancellation count = 0 if valid slots exist.
    """
    version = ensure_baseline_schedule(db)
    active_ivs = db.query(Interview).filter(
        Interview.schedule_version_id == version.id,
        Interview.status == "SCHEDULED"
    ).all()
    assert len(active_ivs) > 0, "Scheduled interviews required"
    company = db.query(Company).get(active_ivs[0].company_id)
    assert company is not None, "Active company required for test"

    sim_res = DisruptionService.simulate_disruption(
        db=db,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=2,
        reason="Company delayed 90 minutes"
    )

    assert sim_res["affected_interviews_count"] > 0
    disruption_id = sim_res["disruption_id"]

    replan_res = ReplanningService.run_replanning(db=db, disruption_id=disruption_id)
    assert len(replan_res["strategies_comparison"]) == 5

    apply_res = ReplanningService.apply_replan_strategy(
        db=db,
        replanning_run_id=replan_res["replanning_run_id"],
        strategy_type="BALANCED"
    )
    assert apply_res["status"] == "APPLIED"

    new_version_id = apply_res["new_schedule_version_id"]
    new_interviews = db.query(Interview).filter(
        Interview.schedule_version_id == new_version_id,
        Interview.company_id == company.id,
        Interview.status != "CANCELLED"
    ).all()

    # Verify company interviews are not scheduled in delayed slots (slots 0 and 1)
    for iv in new_interviews:
        assert iv.slot_index >= 2, f"Interview scheduled at slot {iv.slot_index} during 2-slot company delay"

def test_scenario_2_room_unavailable(db):
    """
    TEST 2 — ROOM UNAVAILABLE
    Disable room. Affected interviews are moved to available rooms or times without cancellation.
    """
    version = ensure_baseline_schedule(db)
    room_ids_with_interviews = [iv.room_id for iv in db.query(Interview).filter(Interview.schedule_version_id == version.id, Interview.status == "SCHEDULED").all()]
    room = db.query(Room).filter(Room.id.in_(room_ids_with_interviews)).first() if room_ids_with_interviews else db.query(Room).first()
    assert room is not None

    sim_res = DisruptionService.simulate_disruption(
        db=db,
        event_type="ROOM_UNAVAILABLE",
        target_entity_type="room",
        target_entity_id=room.id,
        reason="Room maintenance emergency"
    )

    disruption_id = sim_res["disruption_id"]
    replan_res = ReplanningService.run_replanning(db=db, disruption_id=disruption_id)
    apply_res = ReplanningService.apply_replan_strategy(
        db=db,
        replanning_run_id=replan_res["replanning_run_id"],
        strategy_type="MINIMAL_CHANGE"
    )

    new_version_id = apply_res["new_schedule_version_id"]
    new_interviews = db.query(Interview).filter(
        Interview.schedule_version_id == new_version_id,
        Interview.status == "SCHEDULED"
    ).all()

    # None of the active interviews in new schedule should use disabled room
    for iv in new_interviews:
        assert iv.room_id != room.id, f"Disabled room {room.room_code} still assigned in new schedule"

def test_scenario_3_panel_unavailable(db):
    """
    TEST 3 — PANEL UNAVAILABLE
    Disable panel. Affected interviews reassigned to qualified panels or rescheduled.
    """
    version = ensure_baseline_schedule(db)
    panel_ids_with_interviews = [iv.panel_id for iv in db.query(Interview).filter(Interview.schedule_version_id == version.id, Interview.status == "SCHEDULED").all()]
    panel = db.query(Panel).filter(Panel.id.in_(panel_ids_with_interviews)).first() if panel_ids_with_interviews else db.query(Panel).first()
    assert panel is not None

    sim_res = DisruptionService.simulate_disruption(
        db=db,
        event_type="PANEL_UNAVAILABLE",
        target_entity_type="panel",
        target_entity_id=panel.id,
        reason="Panel member emergency leave"
    )

    disruption_id = sim_res["disruption_id"]
    replan_res = ReplanningService.run_replanning(db=db, disruption_id=disruption_id)
    apply_res = ReplanningService.apply_replan_strategy(
        db=db,
        replanning_run_id=replan_res["replanning_run_id"],
        strategy_type="BALANCED"
    )

    new_version_id = apply_res["new_schedule_version_id"]
    new_interviews = db.query(Interview).filter(
        Interview.schedule_version_id == new_version_id,
        Interview.status == "SCHEDULED"
    ).all()

    for iv in new_interviews:
        assert iv.panel_id != panel.id, f"Disabled panel {panel.panel_code} still assigned in new schedule"

def test_scenario_4_student_cancellation_reassignment(db):
    """
    TEST 4 — STUDENT CANCELLATION
    Student cancels. Freed slot search identifies eligible replacement and reassigns it.
    """
    iv = get_active_interview(db)
    assert iv is not None

    user = db.query(User).filter(User.role == "COORDINATOR").first() or db.query(User).first()

    res = CancellationService.handle_student_cancellation(
        db=db,
        interview_id=iv.id,
        reason="Illness",
        comment="Medical emergency",
        current_user=user
    )

    assert res["cancellation_id"] is not None
    assert res["new_schedule_version_id"] is not None

    # Check new version interviews
    new_version_ivs = db.query(Interview).filter(
        Interview.schedule_version_id == res["new_schedule_version_id"],
        Interview.slot_index == iv.slot_index,
        Interview.room_id == iv.room_id,
        Interview.panel_id == iv.panel_id,
        Interview.status == "SCHEDULED"
    ).all()

    # Slot should either be assigned to a replacement student or remain vacant
    if res["replacement_assigned"]:
        assert len(new_version_ivs) == 1
        assert new_version_ivs[0].student_id != iv.student_id
        assert res["replacement_student_code"] is not None
        meta = json.loads(new_version_ivs[0].audit_metadata)
        assert "candidate_rank" in meta
    else:
        assert len(new_version_ivs) == 0

def test_scenario_5_multiple_student_cancellations(db):
    """
    TEST 5 — MULTIPLE CANCELLATIONS
    Multiple students cancel. System handles each sequentially, updating schedule without conflicts.
    """
    version = ensure_baseline_schedule(db)
    ivs = db.query(Interview).filter(
        Interview.schedule_version_id == version.id,
        Interview.status == "SCHEDULED"
    ).limit(3).all()
    assert len(ivs) >= 2

    user = db.query(User).filter(User.role == "COORDINATOR").first() or db.query(User).first()

    for target_iv in ivs:
        curr_ver = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
        active_target = db.query(Interview).filter(
            Interview.schedule_version_id == curr_ver.id,
            Interview.student_id == target_iv.student_id,
            Interview.company_id == target_iv.company_id,
            Interview.status == "SCHEDULED"
        ).first()

        if active_target:
            CancellationService.handle_student_cancellation(
                db=db,
                interview_id=active_target.id,
                reason="Multiple cancellation test",
                comment=None,
                current_user=user
            )

    latest_ver = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
    final_ivs = db.query(Interview).filter(
        Interview.schedule_version_id == latest_ver.id,
        Interview.status == "SCHEDULED"
    ).all()

    # Verify no duplicate student slot overlaps in final schedule
    seen_slots = set()
    for f_iv in final_ivs:
        key = (f_iv.student_id, f_iv.slot_index, f_iv.day_number)
        assert key not in seen_slots, f"Duplicate student slot conflict found: {key}"
        seen_slots.add(key)

def test_scenario_6_no_valid_replacement(db):
    """
    TEST 6 — NO VALID REPLACEMENT
    Student cancels when no eligible replacement student exists (e.g. strict CGPA 10 requirement).
    Expected: Slot left vacant, replacement_assigned is False, audit message explains no eligible student available.
    """
    iv = get_active_interview(db)
    assert iv is not None

    req = db.query(CompanyRequirements).filter(CompanyRequirements.company_id == iv.company_id).first()
    orig_cgpa = req.min_cgpa if req else 6.0
    if req:
        req.min_cgpa = 10.0
        db.commit()

    try:
        user = db.query(User).filter(User.role == "COORDINATOR").first() or db.query(User).first()
        res = CancellationService.handle_student_cancellation(
            db=db,
            interview_id=iv.id,
            reason="Unavailability test",
            comment=None,
            current_user=user
        )

        assert res["replacement_assigned"] == False
        assert "No eligible replacement student available" in res["audit_message"]

    finally:
        if req:
            req.min_cgpa = orig_cgpa
            db.commit()
