from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import manager

router = APIRouter(tags=["websockets"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None),
    role: str = Query("COORDINATOR"),
    company_id: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None)
):
    await manager.connect(
        websocket=websocket,
        user_id=user_id,
        role=role.upper(),
        company_id=company_id,
        student_id=student_id
    )
    try:
        while True:
            # Keep connection open and receive optional ping messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
