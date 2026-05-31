"""
UrbanPulse — Firmware Sensor Data HTTP Endpoint

Receives POST /api/sensor-data from the ESP32 gateway node.
Converts the flat firmware JSON to internal format, processes
through the classification pipeline, and returns the alert level
so the gateway can trigger its buzzer.

Firmware reference: gateway_node.ino (sendToServer function)
"""
import json
import logging
import time
from fastapi import APIRouter, Request
from core.firmware_adapter import firmware_to_internal
from core.classifier import classify_reading
from core.health_score import compute_health_score
from db.queries import insert_reading, insert_alert, upsert_node
from ws.hub import hub

logger = logging.getLogger("urbanpulse.sensor_data")

router = APIRouter(prefix="/api", tags=["Hardware"])


@router.post("/sensor-data")
async def receive_sensor_data(request: Request):
    """Receive sensor reading from the ESP32 gateway via HTTP POST.

    Firmware sends flat JSON. We convert, process, and return alert level.
    """
    try:
        fw_payload = await request.json()
    except Exception as e:
        logger.warning("Invalid JSON from firmware: %s", e)
        return {"status": "error", "message": "Invalid JSON"}

    # Convert to internal format
    internal, err = firmware_to_internal(fw_payload)
    if err:
        logger.warning("Firmware format error: %s — payload: %s", err, fw_payload)
        return {"status": "error", "message": err}

    node_id = internal["node_id"]
    ts = internal["ts"]
    config = request.app.state.config

    # Update packet stats
    if not hasattr(request.app.state, "stats"):
        request.app.state.stats = {"total_packets": 0, "last_packet_ts": 0}
    request.app.state.stats["total_packets"] += 1
    request.app.state.stats["last_packet_ts"] = int(time.time() * 1000)

    # Classify and score
    severity, reason = classify_reading(internal, config)
    health_score = compute_health_score(internal, config)

    logger.info(
        "HTTP ← Node %s | score=%d | severity=%s",
        node_id, health_score, severity
    )

    # Store reading
    insert_reading(node_id, ts, health_score, severity, internal)

    # Upsert node status
    upsert_node(node_id, "ONLINE", ts, health_score)

    # Broadcast via WebSocket
    await hub.broadcast({
        "type": "reading",
        "data": {
            "node_id": node_id,
            "ts": ts,
            "health_score": health_score,
            "severity": severity,
            "payload": internal,
        }
    })

    # Handle alerts
    if severity in ["WARNING", "CRITICAL"]:
        insert_alert(node_id, severity, reason or "Threshold exceeded", ts)
        # Publish back to MQTT for any MQTT-connected hardware
        if hasattr(request.app.state, "publisher") and request.app.state.publisher is not None:
            request.app.state.publisher.publish_alert(node_id, severity, reason or "Threshold exceeded")
        logger.warning("Alert generated for Node %s: %s (%s)", node_id, severity, reason)

        await hub.broadcast({
            "type": "alert",
            "data": {
                "node_id": node_id,
                "severity": severity,
                "reason": reason or "Threshold exceeded",
                "ts": ts,
            }
        })

    # Return alert level to the gateway so it can trigger its buzzer
    return {
        "status": "ok",
        "alert": severity,
    }
