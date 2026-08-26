from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    AICopilotQueryRequest, AICopilotQueryResponse,
    ExplainInterviewRequest, ExplainInterviewResponse
)
from app.ai.copilot_service import AICopilotService
from app.api.deps import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])
copilot_service = AICopilotService()

@router.post("/copilot/query", response_model=AICopilotQueryResponse)
def query_copilot(
    req: AICopilotQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        res = copilot_service.handle_query(
            db=db,
            query=req.query,
            context_type=req.context_type,
            entity_id=req.entity_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/explain/interview", response_model=ExplainInterviewResponse)
def explain_interview(
    req: ExplainInterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        res = copilot_service.explain_interview(
            db=db,
            interview_id=req.interview_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
