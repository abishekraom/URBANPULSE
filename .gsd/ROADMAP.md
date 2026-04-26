# ROADMAP.md — UrbanPulse Backend Build Roadmap

> **Current Phase**: Not started
> **Milestone**: v1.0 — Demo-Ready Backend
> **Scope**: Backend only (AI/ML discarded)

---

## Must-Haves (from SPEC + Phase 1 Discussion)

- [ ] MQTT ingestion from 3 ESP32 nodes (paho-mqtt, thread-bridge)
- [ ] SQLite time-series storage with WAL mode
- [ ] Rule-based severity classification (threshold config.json)
- [ ] Health score computation 0–100 per node in backend
- [ ] Node heartbeat + OFFLINE detection (10s timeout)
- [ ] Alert back-publish to MQTT (LED/buzzer trigger)
- [ ] REST API: nodes, alerts, history, health, thresholds, CSV export
- [ ] WebSocket broadcast hub (snapshot + deltas, <1s latency)
- [ ] Mock MQTT publisher with normal + fault simulation modes
- [ ] Runs 100% offline, no internet dependency

---

## Phases

### Phase 1: Foundation — MQTT + Skeleton
**Status**: ✅ Complete
**Objective**: Runnable FastAPI server with MQTT ingestion working end-to-end; mock publisher lets entire backend be tested without any ESP32 hardware
**Deliverables**:
- FastAPI app with lifespan (startup/shutdown hooks)
- Mosquitto broker local config (`mosquitto.conf`) + startup instructions
- `mqtt/ingester.py` — paho subscriber thread-bridge → asyncio queue
- `mqtt/publisher.py` — alert back-publish to `urbanpulse/alerts`
- `mock_publisher.py` — two modes: `--mode normal` (healthy) | `--mode fault --node B` (CRITICAL burst)
- `config.json` — broker settings, MQTT topics, severity thresholds, health score boundaries
- Verified: mock publisher → Mosquitto → ingester → asyncio queue (logged to console)
**Requirements**: SPEC § MQTT Contract, SPEC § Constraints (offline), ADR-004, ADR-005, ADR-007

### Phase 2: Storage + Processing Pipeline
**Status**: ✅ Complete
**Objective**: Every MQTT packet is classified, health score computed, stored in SQLite; node registry and heartbeat detection working
**Deliverables**:
- `db/connection.py` — SQLite WAL mode, schema migrations (readings, alerts, nodes tables)
- `db/queries.py` — insert_reading(), insert_alert(), upsert_node(), get_history()
- `core/classifier.py` — rule-based threshold classification (returns severity + reason)
- `core/health_score.py` — computes 0–100 health score from FFT features
- `core/heartbeat.py` — async task: checks last_seen per node, broadcasts OFFLINE if >10s
- `core/pipeline.py` — async loop: dequeue → classify → score → store → emit
- Unit tests: classifier (all severity levels), health_score (edge cases 0 and 100)
**Requirements**: SPEC § SQLite Schema, SPEC § Health Score Algorithm, ADR-007, ADR-008

### Phase 3: REST API
**Status**: ✅ Complete
**Objective**: All 7 REST endpoints serving correct data; curl-verified against mock publisher stream
**Deliverables**:
- `GET /api/nodes` — nodes with health_score, state, last_seen, online status
- `GET /api/nodes/{id}/data?limit=50` — readings (FFT + raw values + health_score)
- `GET /api/nodes/{id}/history?minutes=10` — health score trend (timestamp + score pairs)
- `GET /api/alerts?limit=20` — alert events with ts, node_id, severity, reason
- `GET /api/alerts/export` — StreamingResponse CSV download
- `GET /api/health` — uptime_s, total_packets, last_packet_age_ms
- `GET /api/config/thresholds` — current Warning/Critical values from config.json
- CORS enabled (localhost:5173 default, configurable)
**Requirements**: SPEC § REST API Surface, SPEC § Frontend Data Contract, ADR-009

### Phase 4: WebSocket Hub
**Status**: ✅ Complete
**Objective**: React dashboard receives live updates via WebSocket within 1s of sensor data arriving
**Deliverables**:
- `ws/hub.py` — BroadcastHub (per-client bounded queues, fan-out)
- `GET /ws` — WebSocket endpoint: snapshot on connect, delta stream
- WebSocket message envelope schema (type: snapshot | reading | alert)
- Heartbeat ping/pong (30s interval)
- Integration test: mock publisher → backend → ws client receives update
**Requirements**: SPEC § Success Criteria (WebSocket <1s)

### Phase 5: Integration + Hardening
**Status**: ✅ Complete
**Objective**: Backend connects to real ESP32 hardware; thresholds calibrated; 24h stress test passes
**Deliverables**:
- End-to-end test with real gateway ESP32 publishing MQTT
- Alert back-publish verified (LED/buzzer fires on CRITICAL)
- Threshold tuning session with live sensor data → update `config.json`
- 24h continuous run log (no crash, no memory leak)
- `README.md` — how to start Mosquitto + backend for demo day
**Requirements**: SPEC § Success Criteria (all)
