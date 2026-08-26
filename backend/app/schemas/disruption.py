from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class SimulateDisruptionRequest(BaseModel):
    event_type: str  # COMPANY_DELAY, COMPANY_CANCELLATION, PANEL_UNAVAILABLE, ROOM_UNAVAILABLE, STUDENT_WITHDRAWAL
    target_entity_type: str  # company, panel, room, student
    target_entity_id: str
    delay_slots: Optional[int] = 0
    affected_panel_ids: Optional[List[str]] = []
    withdrawn_student_ids: Optional[List[str]] = []
    reason: Optional[str] = "Operational disruption reported"

class DisruptionSimulationOut(BaseModel):
    disruption_id: str
    event_type: str
    severity: str
    affected_interviews_count: int
    affected_students_count: int
    affected_rooms_count: int
    affected_panels_count: int
    expected_delay_hours: float
    risk_level: str
    affected_interviews: List[Dict[str, Any]]
    explanation: str

class DisruptionOut(BaseModel):
    id: str
    event_type: str
    target_entity_type: str
    target_entity_id: str
    severity: str
    status: str
    parameters: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True
