import asyncio
import logging
import time
from core.classifier import classify_reading
from core.health_score import compute_health_score
from db.queries import insert_reading, insert_alert, upsert_node
from ws.hub import hub

logger = logging.getLogger("urbanpulse.pipeline")

async def process_queue(app_state):
    logger.info("Pipeline processor started.")
    config = app_state.config
    queue = app_state.queue
    publisher = app_state.publisher
    
    try:
        while True:
            event = await queue.get()
            topic = event.get("topic", "")
            payload = event.get("payload", {})
            
            node_id = payload.get("node_id", "UNKNOWN")
            ts = payload.get("ts", int(time.time() * 1000))
            
            if topic.endswith("/data"):
                # Process data reading
                severity, reason = classify_reading(payload, config)
                health_score = compute_health_score(payload, config)
                
                # Store reading
                insert_reading(node_id, ts, health_score, severity, payload)
                
                # Upsert node status
                upsert_node(node_id, "ONLINE", ts, health_score)
                
                # Broadcast reading
                await hub.broadcast({
                    "type": "reading",
                    "data": {
                        "node_id": node_id,
                        "ts": ts,
                        "health_score": health_score,
                        "severity": severity,
                        "payload": payload
                    }
                })
                
                # Handle alerts
                if severity in ["WARNING", "CRITICAL"]:
                    insert_alert(node_id, severity, reason or "Threshold exceeded", ts)
                    publisher.publish_alert(node_id, severity, reason or "Threshold exceeded", payload)
                    logger.warning(f"Alert generated for {node_id}: {severity} ({reason})")
                    
                    # Broadcast alert
                    await hub.broadcast({
                        "type": "alert",
                        "data": {
                            "node_id": node_id,
                            "severity": severity,
                            "reason": reason or "Threshold exceeded",
                            "ts": ts
                        }
                    })
                    
            elif topic.endswith("/heartbeat"):
                # Handle heartbeat
                from db.queries import get_nodes
                nodes = get_nodes()
                current_node = next((n for n in nodes if n["node_id"] == node_id), None)
                last_health_score = current_node["last_health_score"] if current_node else 100
                
                upsert_node(node_id, "ONLINE", ts, last_health_score)
                
                # Broadcast node update
                await hub.broadcast({
                    "type": "node_update",
                    "data": {
                        "node_id": node_id,
                        "state": "ONLINE",
                        "last_seen": ts,
                        "last_health_score": last_health_score
                    }
                })
                
            queue.task_done()
            
    except asyncio.CancelledError:
        logger.info("Pipeline processor stopped.")
