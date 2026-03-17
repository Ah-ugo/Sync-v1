from fastapi import WebSocket
from typing import Dict, List, Set
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # user_id -> list of websocket connections
        self.user_connections: Dict[str, List[WebSocket]] = {}
        # session_id -> set of user_ids
        self.session_users: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, session_id: str = None):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

        if session_id:
            if session_id not in self.session_users:
                self.session_users[session_id] = set()
            self.session_users[session_id].add(user_id)

        logger.info(f"WS connected: user={user_id}, session={session_id}")

    def disconnect(self, websocket: WebSocket, user_id: str, session_id: str = None):
        if user_id in self.user_connections:
            try:
                self.user_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        if session_id and session_id in self.session_users:
            if not self.user_connections.get(user_id):
                self.session_users[session_id].discard(user_id)

        logger.info(f"WS disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, event: str, data: dict):
        """Send event to all connections of a specific user"""
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if user_id in self.user_connections:
            dead = []
            for ws in self.user_connections[user_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                try:
                    self.user_connections[user_id].remove(ws)
                except ValueError:
                    pass

    async def broadcast_to_session(self, session_id: str, event: str, data: dict, exclude_user: str = None):
        """Broadcast event to all users in a session"""
        if session_id not in self.session_users:
            return
        for user_id in self.session_users[session_id]:
            if user_id != exclude_user:
                await self.send_to_user(user_id, event, data)

    def get_session_online_count(self, session_id: str) -> int:
        if session_id not in self.session_users:
            return 0
        return sum(
            1 for uid in self.session_users[session_id]
            if uid in self.user_connections and self.user_connections[uid]
        )


manager = ConnectionManager()
