import asyncio
import logging
import time
from core.classifier import classify_reading
from core.health_score import compute_health_score
from core.contract import validate_data_payload, validate_heartbeat_payload
from db.queries import insert_reading, insert_alert, upsert_node
from ws.hub import hub

logger = logging.getLogger("urbanpulse.pipeline")


async def _update_baseline(app_state, node_id, payload):
    """Update running frequency average for baseline deviation detection."""
    mpu_freq = payload.get("mpu", {}).get("dom_freq", 0)
    piezo_freq = payload.get("piezo", {}).get("dom_freq", 0)

    if mpu_freq <= 0 and piezo_freq <= 0:
        return

    async with app_state.freq_baseline_lock:
        bl = app_state.freq_baselines.get(node_id, {"mpu": 0.0, "piezo": 0.0, "samples": 0})
        bl["samples"] += 1
        n = bl["samples"]
        if mpu_freq > 0:
            bl["mpu"] = bl["mpu"] * ((n - 1) / n) + mpu_freq / n
        if piezo_freq > 0:
            bl["piezo"] = bl["piezo"] * ((n - 1) / n) + piezo_freq / n
        app_state.freq_baselines[node_id] = bl


async def _get_baseline(app_state, node_id):
    """Get running baseline frequency for a node. Returns mpu_baseline or None."""
    async with app_state.freq_baseline_lock:
        bl = app_state.freq_baselines.get(node_id)
        if bl and bl["samples"] >= 10:  # need at least 10 readings to establish baseline
            return bl["mpu"]
    return None


async def process_queue(app_state):
    logger.info("Pipeline processor started.")
    config = app_state.config
    queue = app_state.queue
    publisher = app_state.publisher

    # Packet statistics tracked in shared state for /api/health
    app_state.stats = {"total_packets": 0, "last_packet_ts": 0}

    try:
        while True:
            event = await queue.get()
            topic = event.get("topic", "")
            payload = event.get("payload", {})

            node_id = payload.get("node_id", "UNKNOWN")
            # Mock publisher sends "ts"; real ESP32 may send "ts" — both handled
            ts = payload.get("ts") or payload.get("timestamp") or int(time.time() * 1000)

            # Track packet statistics
            app_state.stats["total_packets"] += 1
            app_state.stats["last_packet_ts"] = int(time.time() * 1000)

            if topic.endswith("/data"):
                # ── Contract validation ───────────────────────────────────────
                valid, reason = validate_data_payload(payload)
                if not valid:
                    logger.warning("Contract violation from %s: %s — payload dropped", node_id, reason)
                    queue.task_done()
                    continue

                # ── Frequency baseline for deviation penalty ─────────────────
                await _update_baseline(app_state, node_id, payload)
                baseline = await _get_baseline(app_state, node_id)

                # Process data reading
                severity, reason = classify_reading(payload, config)
                health_score = compute_health_score(payload, config, baseline_freq=baseline)

                logger.info(
                    "Pipeline ← %s | score=%d | severity=%s%s",
                    node_id, health_score, severity,
                    f" | baseline={baseline:.1f}Hz" if baseline else ""
                )

                # Store reading
                insert_reading(node_id, ts, health_score, severity, payload)

                # Upsert node status
                upsert_node(node_id, "ONLINE", ts, health_score)

                # Broadcast reading via throttled hub
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
                    publisher.publish_alert(node_id, severity, reason or "Threshold exceeded")
                    logger.warning(f"Alert generated for {node_id}: {severity} ({reason})")

                    # Broadcast alert (passed through, not deduped)
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
                # ── Contract validation ───────────────────────────────────────
                valid, reason = validate_heartbeat_payload(payload)
                if not valid:
                    logger.warning("Heartbeat contract violation from %s: %s — dropped", node_id, reason)
                    queue.task_done()
                    continue

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
