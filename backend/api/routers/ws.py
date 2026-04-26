import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws.hub import hub
from db.queries import get_nodes, get_alerts

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await hub.connect(websocket)
    
    try:
        # Send snapshot on connect
        snapshot = {
            "type": "snapshot",
            "nodes": get_nodes(),
            "alerts": get_alerts(20)
        }
        await websocket.send_json(snapshot)
        
        while True:
            # Wait for client messages (like ping/pong for keepalive)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        hub.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        hub.disconnect(websocket)
