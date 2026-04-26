import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class BroadcastHub:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
            
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to websocket: {e}")
                disconnected.add(connection)
                
        for conn in disconnected:
            self.disconnect(conn)

# Singleton instance to be shared across the app
hub = BroadcastHub()
