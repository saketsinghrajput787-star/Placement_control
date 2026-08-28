import pytest
from app.db.session import SessionLocal
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.operations import Disruption, ReplanningRun
from app.models.company import Company
from app.models.resource import Panel
from app.models.student import Student
from app.services.disruption_service import DisruptionService
from app.services.replanning_service import ReplanningService
from app.scheduler.solver import PlacementScheduler
import json

from tests.conftest import TestingSessionLocal
from tests.test_disruption_recovery_scenarios import ensure_test_data_seeded, ensure_baseline_schedule

@pytest.fixture
def db():
    db_session = TestingSessionLocal()
    try:
        ensure_baseline_schedule(db_session)
        yield db_session
    finally:
        db_session.close()

def test_multi_disruption_impact_calculation(db):
    session_id = "test-session-001"
    company = db.query(Company).filter(Company.placement_session_id == session_id, (Company.company_code == "TECHNOVA") | (Company.company_code == "C001") | (Company.company_code == "COMP1")).first() or db.query(Company).filter(Company.placement_session_id == session_id).first()
    panel = db.query(Panel).filter(Panel.placement_session_id == session_id, Panel.company_id == company.id).first() if company else db.query(Panel).filter(Panel.placement_session_id == session_id).first()
    students = [s.id for s in db.query(Student).filter(Student.placement_session_id == session_id).limit(5).all()]

    sim_res = DisruptionService.simulate_disruption(
        db=db,
        placement_session_id=session_id,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=2,
        affected_panel_ids=[panel.id] if panel else [],
        withdrawn_student_ids=students,
        reason="Multi-disruption test"
    )

    assert sim_res["disruption_id"] is not None
    assert sim_res["affected_interviews_count"] > 0
    assert sim_res["affected_students_count"] > 0
    assert sim_res["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

def test_solver_strategy_modes_produce_different_metrics(db):
    session_id = "test-session-001"
    company = db.query(Company).filter(Company.placement_session_id == session_id).first()
    sim_res = DisruptionService.simulate_disruption(
        db=db,
        placement_session_id=session_id,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=3,
        reason="Test solver mode diff"
    )

    replan_res = ReplanningService.run_replanning(
        db=db,
        placement_session_id=session_id,
        disruption_id=sim_res["disruption_id"]
    )

    strats = replan_res["strategies_comparison"]
    assert len(strats) == 5

    for s in strats:
        assert "student_waiting_minutes" in s
        assert "stability_score" in s
        assert "overall_score" in s
        assert "panel_utilization_pct" in s
        assert "room_utilization_pct" in s

    moved_counts = [s["moved_interviews"] for s in strats]
    scores = [s["overall_score"] for s in strats]
    assert len(set(moved_counts)) > 1 or len(set(scores)) > 1

def test_replanning_run_persists_comparison_and_diff(db):
    session_id = "test-session-001"
    company = db.query(Company).filter(Company.placement_session_id == session_id).first()
    sim_res = DisruptionService.simulate_disruption(
        db=db,
        placement_session_id=session_id,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=2,
        reason="Replanning test"
    )

    replan_res = ReplanningService.run_replanning(
        db=db,
        placement_session_id=session_id,
        disruption_id=sim_res["disruption_id"]
    )

    assert replan_res["replanning_run_id"] is not None
    assert len(replan_res["strategies_comparison"]) == 5
    assert len(replan_res["diff"]) > 0

    strategies = replan_res["strategies_comparison"]
    scores = [s["overall_score"] for s in strategies]
    stabilities = [s["stability_score"] for s in strategies]

    assert len(set(scores)) > 1 or len(set(stabilities)) > 1, f"Strategies should produce different scores: {scores}"

def test_apply_recovery_strategy(db):
    session_id = "test-session-001"
    company = db.query(Company).filter(Company.placement_session_id == session_id).first()
    sim_res = DisruptionService.simulate_disruption(
        db=db,
        placement_session_id=session_id,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=1,
        reason="Apply test"
    )

    replan_res = ReplanningService.run_replanning(
        db=db,
        placement_session_id=session_id,
        disruption_id=sim_res["disruption_id"]
    )

    apply_res = ReplanningService.apply_replan_strategy(
        db=db,
        placement_session_id=session_id,
        replanning_run_id=replan_res["replanning_run_id"],
        strategy_type="BALANCED"
    )

    assert apply_res["status"] == "APPLIED"
    assert apply_res["new_schedule_version_id"] is not None
    assert apply_res["version_number"] > 1

    disruption = db.query(Disruption).filter(Disruption.id == sim_res["disruption_id"]).first()
    assert disruption.status == "APPLIED"
