from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.websocket_manager import manager
from app.models.user import User
from app.core.security import get_current_user
from app.core.config import settings
from jose import jwt, JWTError
import json
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    session_id: str = Query(None),
):
    """Main WebSocket endpoint — authenticate via token query param"""
    user_id = None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id, session_id)
    try:
        # Send connected confirmation
        await websocket.send_text(json.dumps({
            "event": "connected",
            "data": {"user_id": user_id, "session_id": session_id},
        }))

        # Heartbeat loop
        async def heartbeat():
            while True:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                try:
                    await websocket.send_text(json.dumps({"event": "ping"}))
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event = message.get("event")

            if event == "pong":
                continue
            elif event == "typing" and session_id:
                await manager.broadcast_to_session(
                    session_id, "typing",
                    {"user_id": user_id},
                    exclude_user=user_id,
                )

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {user_id}")
    finally:
        manager.disconnect(websocket, user_id, session_id)
        try:
            heartbeat_task.cancel()
        except Exception:
            pass
