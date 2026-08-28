from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.services.conflict_service import ConflictService
from app.schemas.analytics import ConflictsResponse
from app.api.deps import get_current_user, get_current_session_id

router = APIRouter(prefix="/conflicts", tags=["conflicts"])

@router.get("", response_model=ConflictsResponse)
def get_conflicts(
    version_id: Optional[str] = None,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    result = ConflictService.get_conflicts_for_latest_version(db, placement_session_id=session_id, version_id=version_id)
    return ConflictsResponse(
        total_conflicts=result["total_conflicts"],
        conflicts=result["conflicts"]
    )
