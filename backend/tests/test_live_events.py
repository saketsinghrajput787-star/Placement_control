import pytest
from app.services.schedule_service import ScheduleService
from app.services.disruption_service import DisruptionService
from app.services.replanning_service import ReplanningService
from app.models.schedule import Interview, ScheduleVersion
from app.models.student import Student
from app.models.company import Company

def test_student_cancellation_and_replanning_flow(db_session, sample_data):
    session_id = sample_data["session"].id
    # 1. Generate initial schedule
    init_res = ScheduleService.generate_initial_schedule(db_session, placement_session_id=session_id)
    assert "version_number" in init_res
    version_id = init_res["schedule_version_id"]

    # 2. Pick an interview to cancel
    interview = db_session.query(Interview).filter(Interview.placement_session_id == session_id, Interview.schedule_version_id == version_id).first()
    assert interview is not None

    student_id = interview.student_id

    # 3. Simulate cancellation disruption
    disrupt_res = DisruptionService.simulate_disruption(
        db_session,
        placement_session_id=session_id,
        event_type="STUDENT_CANCELLED_INTERVIEW",
        target_entity_type="student",
        target_entity_id=student_id,
        reason="Personal reason"
    )
    assert disrupt_res["affected_interviews_count"] >= 1

    # 4. Run replanning & apply
    replan_res = ReplanningService.run_replanning(db_session, placement_session_id=session_id, disruption_id=disrupt_res["disruption_id"], source_version_id=version_id)
    apply_res = ReplanningService.apply_strategy(db_session, placement_session_id=session_id, replanning_run_id=replan_res["replanning_run_id"], strategy_type="BALANCED")
    
    assert apply_res["version_number"] > 1
    assert apply_res["resulting_version_id"] is not None

def test_company_delay_reporting(db_session, sample_data):
    session_id = sample_data["session"].id
    init_res = ScheduleService.generate_initial_schedule(db_session, placement_session_id=session_id)
    assert "version_number" in init_res
    version_id = init_res["schedule_version_id"]

    company = db_session.query(Company).filter(Company.placement_session_id == session_id).first()
    assert company is not None

    disrupt_res = DisruptionService.simulate_disruption(
        db_session,
        placement_session_id=session_id,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=2,
        reason="Flight delay"
    )
    assert disrupt_res["affected_interviews_count"] >= 1

    replan_res = ReplanningService.run_replanning(db_session, placement_session_id=session_id, disruption_id=disrupt_res["disruption_id"], source_version_id=version_id)
    apply_res = ReplanningService.apply_strategy(db_session, placement_session_id=session_id, replanning_run_id=replan_res["replanning_run_id"], strategy_type="BALANCED")
    assert apply_res["version_number"] > 1
