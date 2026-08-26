import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.operations import ChangeEvent, Notification, AuditLog
from app.core.websocket_manager import manager

logger = logging.getLogger("placement_control_tower.event_service")

class EventService:
    @staticmethod
    def record_change_event(
        db: Session,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str],
        payload: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> ChangeEvent:
        event = ChangeEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=json.dumps(payload),
            created_by_user_id=user_id
        )
        db.add(event)
        return event

    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        title: str,
        message: str,
        category: str = "SCHEDULE_CHANGE",
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        schedule_version_id: Optional[str] = None
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            schedule_version_id=schedule_version_id
        )
        db.add(notif)
        return notif

    @staticmethod
    def create_audit_log(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        trigger_event: Optional[str] = None,
        schedule_version_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        log_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=json.dumps(before_state or {}),
            after_state=json.dumps(after_state or {}),
            reason=reason,
            trigger_event=trigger_event,
            schedule_version_id=schedule_version_id,
            details=json.dumps(details or {})
        )
        db.add(log_entry)
        return log_entry

    @staticmethod
    async def broadcast_live_event(event_data: Dict[str, Any]):
        """
        Safely broadcasts WebSocket event after DB transaction commit.
        """
        try:
            await manager.broadcast_event(event_data)
        except Exception as exc:
            logger.error(f"Error broadcasting live WebSocket event: {exc}")
