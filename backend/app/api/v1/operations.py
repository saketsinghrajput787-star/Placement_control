import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.operations import Notification, AuditLog
from app.api.deps import get_current_user, get_current_session_id

router = APIRouter(tags=["operations"])

def format_dt(dt):
    if not dt:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)

@router.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    notifs = db.query(Notification).filter(
        (Notification.placement_session_id == session_id) | (Notification.placement_session_id.is_(None)),
        (Notification.user_id == current_user.id) | (Notification.user_id == "GLOBAL")
    ).order_by(Notification.created_at.desc()).limit(100).all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "category": n.category,
            "is_read": n.is_read,
            "schedule_version_id": n.schedule_version_id,
            "created_at": format_dt(n.created_at)
        }
        for n in notifs
    ]

@router.patch("/notifications/{id}/read")
def mark_notification_read(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).get(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "SUCCESS"}

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    logs = db.query(AuditLog).filter(
        (AuditLog.placement_session_id == session_id) | (AuditLog.placement_session_id.is_(None))
    ).order_by(AuditLog.created_at.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "user_email": l.user_email,
            "user_role": l.user_role,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "before_state": json.loads(l.before_state) if l.before_state else {},
            "after_state": json.loads(l.after_state) if l.after_state else {},
            "reason": l.reason,
            "trigger_event": l.trigger_event,
            "schedule_version_id": l.schedule_version_id,
            "details": json.loads(l.details) if l.details else {},
            "created_at": format_dt(l.created_at)
        }
        for l in logs
    ]
