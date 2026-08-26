from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.resource import Room
from app.schemas.resource import RoomOut, RoomCreate
from app.api.deps import get_current_user, require_role
from app.services.disruption_service import DisruptionService
from app.services.event_service import EventService

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get("", response_model=List[RoomOut])
def list_rooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rooms = db.query(Room).order_by(Room.room_code).all()
    return rooms

@router.post("", response_model=RoomOut)
def create_room(
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR"]))
):
    room = Room(**room_in.dict())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

@router.post("/{id}/availability")
async def toggle_room_availability(
    id: str,
    is_active: bool = Body(..., embed=True),
    reason: str = Body("Technical issue", embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = db.query(Room).get(id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    room.is_active = is_active
    db.commit()

    if not is_active:
        res = DisruptionService.simulate_disruption(
            db=db,
            event_type="ROOM_UNAVAILABLE",
            target_entity_type="room",
            target_entity_id=room.id,
            reason=reason
        )
        EventService.create_audit_log(
            db,
            action="ROOM_MARKED_UNAVAILABLE",
            entity_type="ROOM",
            entity_id=room.id,
            reason=reason
        )
        await EventService.broadcast_live_event({
            "type": "ROOM_UNAVAILABLE",
            "room_id": room.id,
            "room_code": room.room_code,
            "message": f"Room {room.room_code} marked unavailable."
        })
        return res

    return {"status": "SUCCESS", "message": f"Room {room.room_code} marked available."}
