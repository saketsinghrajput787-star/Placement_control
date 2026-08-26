from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.replanning import RunReplanningRequest, ReplanningResultOut, ApplyStrategyRequest
from app.services.replanning_service import ReplanningService
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/replanning", tags=["replanning"])

@router.post("/run", response_model=ReplanningResultOut)
def run_replanning(
    req: RunReplanningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        res = ReplanningService.run_replanning(
            db=db,
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
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        res = ReplanningService.run_replanning(
            db=db,
            disruption_id=req.disruption_id,
            source_version_id=req.schedule_version_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/apply")
def apply_strategy(
    req: ApplyStrategyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    try:
        res = ReplanningService.apply_replan_strategy(
            db=db,
            replanning_run_id=req.replanning_run_id,
            strategy_type=req.strategy_type
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
