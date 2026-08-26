from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.schemas.schedule import ScheduleMetrics

class RunReplanningRequest(BaseModel):
    disruption_id: str
    schedule_version_id: Optional[str] = None
    strategy: Optional[str] = "BALANCED"  # STUDENT_FIRST, BALANCED, STABILITY_FIRST, ALL

class ScheduleDiffItem(BaseModel):
    student_id: str
    student_code: str
    student_name: str
    company_name: str
    change_type: str  # UNCHANGED, MOVED, CANCELLED, NEW
    old_time_str: Optional[str] = None
    new_time_str: Optional[str] = None
    old_room_code: Optional[str] = None
    new_room_code: Optional[str] = None
    old_panel_code: Optional[str] = None
    new_panel_code: Optional[str] = None
    reason: str

class RecoveryStrategyOption(BaseModel):
    strategy_type: str  # STUDENT_FIRST, BALANCED, STABILITY_FIRST
    strategy_title: str
    moved_interviews: int
    unchanged_interviews: int
    cancelled_interviews: int
    new_assignments: int
    scheduled_interviews: Optional[int] = 0
    unscheduled_interviews: int
    stability_score: float
    student_waiting_minutes: Optional[float] = 0.0
    waiting_time_level: str  # Low, Medium, High
    room_utilization_pct: float
    panel_utilization_pct: float
    overall_score: float
    is_recommended: bool
    explanation: str
    candidate_interviews: Optional[List[Dict[str, Any]]] = None
    diff: Optional[List[ScheduleDiffItem]] = None

class ReplanningResultOut(BaseModel):
    replanning_run_id: str
    disruption_id: str
    source_version_id: str
    resulting_version_id: Optional[str] = None
    selected_strategy: str
    strategies_comparison: List[RecoveryStrategyOption]
    diff: List[ScheduleDiffItem]
    strategy_diffs: Optional[Dict[str, List[ScheduleDiffItem]]] = None
    stability_score: float
    moved_count: int
    unchanged_count: int
    cancelled_count: int
    metrics_after: ScheduleMetrics

class ApplyStrategyRequest(BaseModel):
    replanning_run_id: str
    strategy_type: str
