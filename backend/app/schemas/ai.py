from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AICopilotQueryRequest(BaseModel):
    query: str
    context_type: Optional[str] = "GENERAL"  # GENERAL, BOTTLENECK, DISRUPTION, REPLANNING, STUDENT, COMPANY
    entity_id: Optional[str] = None

class AICopilotQueryResponse(BaseModel):
    answer: str
    insights: List[str] = []
    relevant_metrics: Dict[str, Any] = {}
    suggested_followups: List[str] = []
    data_grounding: Dict[str, Any] = {}  # Exact DB facts supporting the answer

class ExplainInterviewRequest(BaseModel):
    interview_id: str

class ExplainInterviewResponse(BaseModel):
    interview_id: str
    student_code: str
    company_name: str
    room_code: str
    panel_code: str
    time_slot: str
    hard_constraints_satisfied: Dict[str, bool]
    optimization_reasons: List[str]
    rejected_alternatives: List[Dict[str, str]]
    replan_history: Optional[str] = None
    ai_summary: str
