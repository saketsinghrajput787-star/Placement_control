from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.company import Company
from app.models.resource import Panel
from app.schemas.resource import PanelOut, PanelCreate
from app.api.deps import get_current_user, require_role, get_current_session_id
from app.services.disruption_service import DisruptionService
from app.services.event_service import EventService

router = APIRouter(prefix="/panels", tags=["panels"])

@router.get("", response_model=List[PanelOut])
def list_panels(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Panel).filter(Panel.placement_session_id == session_id)
    if company_id:
        query = query.filter(Panel.company_id == company_id)

    panels = query.order_by(Panel.panel_code).all()
    comp_map = {c.id: c.name for c in db.query(Company).filter(Company.placement_session_id == session_id).all()}

    return [
        PanelOut(
            id=p.id,
            company_id=p.company_id,
            panel_code=p.panel_code,
            interviewer_names=p.interviewer_names,
            is_active=p.is_active,
            company_name=comp_map.get(p.company_id, "Company")
        )
        for p in panels
    ]

@router.post("", response_model=PanelOut)
def create_panel(
    panel_in: PanelCreate,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COORDINATOR", "COMPANY"]))
):
    panel = Panel(
        placement_session_id=session_id,
        **panel_in.dict()
    )
    db.add(panel)
    db.commit()
    db.refresh(panel)
    return panel

@router.post("/{id}/availability")
async def toggle_panel_availability(
    id: str,
    is_active: bool = Body(..., embed=True),
    reason: str = Body("Panel member unavailable", embed=True),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    panel = db.query(Panel).filter(
        Panel.id == id,
        Panel.placement_session_id == session_id
    ).first()
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")

    panel.is_active = is_active
    db.commit()

    if not is_active:
        res = DisruptionService.simulate_disruption(
            db=db,
            placement_session_id=session_id,
            event_type="PANEL_UNAVAILABLE",
            target_entity_type="panel",
            target_entity_id=panel.id,
            reason=reason
        )
        EventService.create_audit_log(
            db,
            action="PANEL_MARKED_UNAVAILABLE",
            entity_type="PANEL",
            entity_id=panel.id,
            reason=reason
        )
        await EventService.broadcast_live_event({
            "type": "PANEL_UNAVAILABLE",
            "placement_session_id": session_id,
            "panel_id": panel.id,
            "panel_code": panel.panel_code,
            "message": f"Panel {panel.panel_code} marked unavailable."
        })
        return res

    return {"status": "SUCCESS", "message": f"Panel {panel.panel_code} marked available."}
