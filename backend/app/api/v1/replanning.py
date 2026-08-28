from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.replanning import RunReplanningRequest, ReplanningResultOut, ApplyStrategyRequest
from app.services.replanning_service import ReplanningService
from app.services.event_service import EventService
from app.api.deps import get_current_user, require_role, get_current_session_id

router = APIRouter(prefix="/replanning", tags=["replanning"])

@router.post("/run", response_model=ReplanningResultOut)
def run_replanning(
    req: RunReplanningRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        res = ReplanningService.run_replanning(
            db=db,
            placement_session_id=session_id,
            disruption_id=req.disruption_id,
            source_version_id=req.schedule_version_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/compare", response_model=ReplanningResultOut)
def compare_strategies(
    req: RunReplanningRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        res = ReplanningService.run_replanning(
            db=db,
            placement_session_id=session_id,
            disruption_id=req.disruption_id,
            source_version_id=req.schedule_version_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/apply")
async def apply_strategy(
    req: ApplyStrategyRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        res = ReplanningService.apply_replan_strategy(
            db=db,
            placement_session_id=session_id,
            replanning_run_id=req.replanning_run_id,
            strategy_type=req.strategy_type
        )
        version_num = res.get("version_number", "")
        
        # Broadcast real-time schedule update
        await EventService.broadcast_live_event({
            "type": "SCHEDULE_UPDATED",
            "placement_session_id": session_id,
            "message": f"Applied {req.strategy_type} recovery plan (Schedule Version V{version_num})."
        })
        
        # Log to audit timeline
        EventService.create_audit_log(
            db=db,
            placement_session_id=session_id,
            event_type="REPLANNING_APPLIED",
            description=f"Applied {req.strategy_type} recovery plan resulting in Schedule Version V{version_num}.",
            user_id=current_user.id
        )
        
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

