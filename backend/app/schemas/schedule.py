from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class InterviewAuditMetadata(BaseModel):
    constraint_checks: Dict[str, bool] = {}
    optimization_reasons: List[str] = []
    rejected_alternatives: List[Dict[str, str]] = []
    replan_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None
    comment: Optional[str] = None
    cancelled_by_role: Optional[str] = None
    assignment_reason: Optional[str] = None
    candidate_score: Optional[float] = None
    candidate_rank: Optional[int] = None

    class Config:
        extra = "ignore"

class InterviewOut(BaseModel):
    id: str
    schedule_version_id: str
    student_id: str
    student_code: str
    student_name: str
    student_branch: str
    student_cgpa: float
    company_id: str
    company_name: str
    company_tier: int
    room_id: str
    room_code: str
    panel_id: str
    panel_code: str
    day_number: int
    slot_index: int
    start_time_str: str
    end_time_str: str
    status: str
    audit_metadata: Optional[InterviewAuditMetadata] = None

    class Config:
        from_attributes = True

class ScheduleMetrics(BaseModel):
    total_interviews: int = 0
    scheduled_interviews: int = 0
    unscheduled_interviews: int = 0
    total_students: int = 0
    total_companies: int = 0
    total_rooms: int = 0
    total_panels: int = 0
    active_conflicts: int = 0
    schedule_stability: float = 100.0
    room_utilization_pct: float = 0.0
    panel_utilization_pct: float = 0.0
    avg_student_waiting_slots: float = 0.0
    bottleneck_risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

class ScheduleVersionOut(BaseModel):
    id: str
    schedule_id: str
    version_number: int
    stability_score: float
    metrics: ScheduleMetrics
    created_at: str

class GenerateScheduleRequest(BaseModel):
    schedule_id: Optional[str] = None
    day_number: Optional[int] = 1
    max_solve_time_seconds: Optional[int] = 30
    weight_scheduled: Optional[int] = 1000
    weight_waiting: Optional[int] = 5
    weight_room_idle: Optional[int] = 2
    weight_panel_idle: Optional[int] = 2
    weight_priority: Optional[int] = 10
