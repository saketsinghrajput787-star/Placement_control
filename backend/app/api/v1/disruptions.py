from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.operations import Disruption
from app.schemas.disruption import SimulateDisruptionRequest, DisruptionSimulationOut, DisruptionOut
from app.services.disruption_service import DisruptionService
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/disruptions", tags=["disruptions"])

@router.post("/simulate", response_model=DisruptionSimulationOut)
def simulate_disruption(
    req: SimulateDisruptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR", "COMPANY"]))
):
    try:
        res = DisruptionService.simulate_disruption(
            db=db,
            event_type=req.event_type,
            target_entity_type=req.target_entity_type,
            target_entity_id=req.target_entity_id,
            delay_slots=req.delay_slots,
            affected_panel_ids=req.affected_panel_ids,
            withdrawn_student_ids=req.withdrawn_student_ids,
            reason=req.reason or "Operational disruption reported"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[DisruptionOut])
def list_disruptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import json
    disruptions = db.query(Disruption).order_by(Disruption.created_at.desc()).limit(50).all()
    return [
        DisruptionOut(
            id=d.id,
            event_type=d.event_type,
            target_entity_type=d.target_entity_type,
            target_entity_id=d.target_entity_id,
            severity=d.severity,
            status=d.status,
            parameters=json.loads(d.parameters) if d.parameters else {},
            created_at=d.created_at.isoformat()
        )
        for d in disruptions
    ]

@router.delete("/clear")
def clear_disruptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    from app.models.operations import ReplanningRun, ScheduleChange
    try:
        db.query(ScheduleChange).delete()
        db.query(ReplanningRun).delete()
        count = db.query(Disruption).delete()
        db.commit()
        return {"status": "SUCCESS", "message": f"Cleared {count} disruption logs."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
