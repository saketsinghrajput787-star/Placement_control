from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsDashboardOut
from app.services.analytics_service import AnalyticsService
from app.api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard", response_model=AnalyticsDashboardOut)
def get_dashboard_analytics(
    version_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_dashboard_analytics(db, version_id=version_id)
