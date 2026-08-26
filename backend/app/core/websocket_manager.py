import json
import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("placement_control_tower.websocket")

class ConnectionManager:
    def __init__(self):
        # Map connection -> metadata
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        role: str = "COORDINATOR",
        company_id: Optional[str] = None,
        student_id: Optional[str] = None
    ):
        await websocket.accept()
        self.active_connections[websocket] = {
            "user_id": user_id,
            "role": role,
            "company_id": company_id,
            "student_id": student_id,
        }
        logger.info(f"WebSocket connected: user_id={user_id}, role={role}, company_id={company_id}, student_id={student_id}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            meta = self.active_connections.pop(websocket)
            logger.info(f"WebSocket disconnected: {meta}")

    async def broadcast_event(self, event_data: Dict[str, Any]):
        """
        Broadcasts an event with role-based and entity-ownership filtering.
        """
        message_text = json.dumps(event_data)
        event_type = event_data.get("type", "")
        affected_user_ids = set(event_data.get("affected_user_ids", []))
        affected_student_ids = set(event_data.get("affected_student_ids", []))
        target_company_id = event_data.get("company_id")

        disconnected: List[WebSocket] = []

        for connection, meta in list(self.active_connections.items()):
            role = meta.get("role")
            user_id = meta.get("user_id")
            student_id = meta.get("student_id")
            company_id = meta.get("company_id")

            # Coordinators see all system events
            should_send = False
            if role == "COORDINATOR":
                should_send = True
            elif role == "COMPANY":
                # Company sees general schedule events, company-specific disruptions, or events targeting its company_id
                if not target_company_id or target_company_id == company_id or event_type in ["SCHEDULE_UPDATED", "DATA_IMPORTED"]:
                    should_send = True
            elif role == "STUDENT":
                # Student sees global schedule version updates or events affecting their student_id / user_id
                if (
                    event_type in ["SCHEDULE_UPDATED", "SCHEDULE_GENERATED"]
                    or (user_id and user_id in affected_user_ids)
                    or (student_id and student_id in affected_student_ids)
                ):
                    should_send = True

            if should_send:
                try:
                    await connection.send_text(message_text)
                except Exception as exc:
                    logger.warning(f"Failed to send WS message to {meta}: {exc}")
                    disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
