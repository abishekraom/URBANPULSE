import asyncio
import time
import logging
from db.queries import get_nodes, upsert_node
from ws.hub import hub

logger = logging.getLogger("urbanpulse.heartbeat")

async def heartbeat_monitor(app_state):
    config = app_state.config
    timeout_s = config.get("heartbeat", {}).get("offline_timeout_s", 10)
    
    logger.info("Heartbeat monitor started.")
    try:
        while True:
            await asyncio.sleep(5)
            nodes = get_nodes()
            current_time = int(time.time() * 1000)
            
            for node in nodes:
                last_seen = node["last_seen"]
                node_id = node["node_id"]
                state = node["state"]
                health_score = node["last_health_score"]
                
                # Check if older than timeout
                if (current_time - last_seen) > (timeout_s * 1000) and state != "OFFLINE":
                    logger.warning(f"Node {node_id} is OFFLINE. Last seen {last_seen}")
                    upsert_node(node_id, "OFFLINE", last_seen, health_score)
                    
                    # Broadcast offline status
                    await hub.broadcast({
                        "type": "node_update",
                        "data": {
                            "node_id": node_id,
                            "state": "OFFLINE",
                            "last_seen": last_seen,
                            "last_health_score": health_score
                        }
                    })
                    
    except asyncio.CancelledError:
        logger.info("Heartbeat monitor stopped.")
