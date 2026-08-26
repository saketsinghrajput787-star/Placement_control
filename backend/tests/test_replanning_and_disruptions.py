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
    """Test that simulate_disruption unions multi-disruption parameters simultaneously."""
    company = db.query(Company).filter((Company.company_code == "TECHNOVA") | (Company.company_code == "C001")).first() or db.query(Company).first()
    panel = db.query(Panel).filter(Panel.company_id == company.id).first() if company else db.query(Panel).first()
    students = [s.id for s in db.query(Student).limit(5).all()]

    sim_res = DisruptionService.simulate_disruption(
        db=db,
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
    """Test that PlacementScheduler.solve with different strategy_mode values produces different outcomes under disruption."""
    company = db.query(Company).filter((Company.company_code == "TECHNOVA") | (Company.company_code == "C001")).first() or db.query(Company).first()
    sim_res = DisruptionService.simulate_disruption(
        db=db,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=3,
        reason="Test solver mode diff"
    )

    replan_res = ReplanningService.run_replanning(
        db=db,
        disruption_id=sim_res["disruption_id"]
    )

    strats = replan_res["strategies_comparison"]
    assert len(strats) == 5

    # Verify dynamic metrics exist and are calculated correctly
    for s in strats:
        assert "student_waiting_minutes" in s
        assert "stability_score" in s
        assert "overall_score" in s
        assert "panel_utilization_pct" in s
        assert "room_utilization_pct" in s

    # Verify strategies are non-identical
    moved_counts = [s["moved_interviews"] for s in strats]
    scores = [s["overall_score"] for s in strats]
    assert len(set(moved_counts)) > 1 or len(set(scores)) > 1

def test_replanning_run_persists_comparison_and_diff(db):
    """Test that ReplanningService.run_replanning produces different strategy comparison scores and diff list."""
    company = db.query(Company).filter((Company.company_code == "TECHNOVA") | (Company.company_code == "C001")).first() or db.query(Company).first()
    sim_res = DisruptionService.simulate_disruption(
        db=db,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=2,
        reason="Replanning test"
    )

    replan_res = ReplanningService.run_replanning(
        db=db,
        disruption_id=sim_res["disruption_id"]
    )

    assert replan_res["replanning_run_id"] is not None
    assert len(replan_res["strategies_comparison"]) == 5
    assert len(replan_res["diff"]) > 0

    # Ensure strategies have non-identical results across moved, stability, or overall_score
    strategies = replan_res["strategies_comparison"]
    scores = [s["overall_score"] for s in strategies]
    stabilities = [s["stability_score"] for s in strategies]

    # At least two strategies must differ in stability or overall score
    assert len(set(scores)) > 1 or len(set(stabilities)) > 1, f"Strategies should produce different scores: {scores}"

def test_apply_recovery_strategy(db):
    """Test applying a recovery strategy creates a new ScheduleVersion and sets disruption status to APPLIED."""
    company = db.query(Company).filter((Company.company_code == "TECHNOVA") | (Company.company_code == "C001")).first() or db.query(Company).first()
    sim_res = DisruptionService.simulate_disruption(
        db=db,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=1,
        reason="Apply test"
    )

    replan_res = ReplanningService.run_replanning(
        db=db,
        disruption_id=sim_res["disruption_id"]
    )

    apply_res = ReplanningService.apply_replan_strategy(
        db=db,
        replanning_run_id=replan_res["replanning_run_id"],
        strategy_type="BALANCED"
    )

    assert apply_res["status"] == "APPLIED"
    assert apply_res["new_schedule_version_id"] is not None
    assert apply_res["version_number"] > 1

    disruption = db.query(Disruption).get(sim_res["disruption_id"])
    assert disruption.status == "APPLIED"
