from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class BottleneckItem(BaseModel):
    time_window: str  # e.g., "13:00–15:00"
    entity_name: str  # e.g., "TechNova", "Room Block A", "Panel P2"
    entity_type: str  # company, panel, room, student_cluster
    utilization_pct: float
    risk_level: str   # LOW, MEDIUM, HIGH, CRITICAL
    reason: str
    suggested_action: str

class ResourceUtilizationItem(BaseModel):
    name: str
    code: str
    type: str  # room or panel
    utilization_pct: float
    total_slots: int
    used_slots: int

class AnalyticsDashboardOut(BaseModel):
    total_students: int
    total_companies: int
    total_rooms: int
    total_panels: int
    total_interviews: int
    scheduled_interviews: int
    unscheduled_interviews: int
    active_conflicts_count: int
    schedule_stability: float
    current_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    room_utilization_avg: float
    panel_utilization_avg: float
    student_waiting_avg: float
    bottlenecks: List[BottleneckItem]
    top_utilized_rooms: List[ResourceUtilizationItem]
    top_utilized_panels: List[ResourceUtilizationItem]
    hourly_interview_density: Dict[str, int]
    company_load_distribution: List[Dict[str, Any]]

class ConflictItem(BaseModel):
    conflict_id: str
    conflict_type: str  # STUDENT_OVERLAP, ROOM_OVERLAP, PANEL_OVERLAP, ELIGIBILITY_VIOLATION, COMPANY_UNAVAILABLE, UNSCHEDULED
    severity: str       # LOW, MEDIUM, HIGH, CRITICAL
    time_slot: str
    day_number: int
    student_code: Optional[str] = None
    company_name: Optional[str] = None
    room_code: Optional[str] = None
    panel_code: Optional[str] = None
    explanation: str
    suggested_action: str

class ConflictsResponse(BaseModel):
    total_conflicts: int
    conflicts: List[ConflictItem]
