# ROADMAP.md — UrbanPulse Backend Build Roadmap

> **Current Phase**: Not started
> **Milestone**: v1.0 — Demo-Ready Backend
> **Scope**: Backend only (AI/ML discarded)

---

## Must-Haves (from SPEC)

- [ ] MQTT ingestion from 3 ESP32 nodes (paho-mqtt, thread-bridge)
- [ ] SQLite time-series storage with WAL mode
- [ ] Rule-based severity classification (threshold config)
- [ ] Alert back-publish to MQTT (LED/buzzer trigger)
- [ ] REST API: `/api/nodes`, `/api/alerts`, `/api/health`
- [ ] WebSocket broadcast hub (snapshot + deltas, <1s latency)
- [ ] Mock MQTT publisher for hardware-independent testing
- [ ] Runs 100% offline, no internet dependency

---

## Phases

### Phase 1: Foundation — MQTT + Skeleton
**Status**: ⬜ Not Started
**Objective**: Runnable FastAPI server with MQTT ingestion working and mock publisher for testing without ESP32 hardware
**Deliverables**:
- FastAPI app with lifespan (startup/shutdown)
- Mosquitto broker configured and verified
- `mqtt/ingester.py` — paho subscriber thread-bridge → asyncio queue
- `mqtt/publisher.py` — alert back-publish
- `mock_publisher.py` — simulates 3 nodes publishing JSON packets
- `config.json` — broker host, port, MQTT topics, thresholds
**Requirements**: SPEC § MQTT Contract, SPEC § Constraints (offline)

### Phase 2: Storage + Processing Pipeline
**Status**: ⬜ Not Started
**Objective**: Every MQTT packet is classified for severity, stored in SQLite, and the node registry is maintained
**Deliverables**:
- `db/connection.py` — SQLite WAL mode, schema migrations on startup
- `db/queries.py` — insert_reading(), insert_alert(), get_node_state(), upsert_node()
- `core/classifier.py` — rule-based threshold classification per sensor
- `core/pipeline.py` — async loop: dequeue → classify → store → emit event
- Unit tests for classifier with known inputs
**Requirements**: SPEC § SQLite Schema, SPEC § Rule-Based Severity

### Phase 3: REST API
**Status**: ⬜ Not Started
**Objective**: All dashboard data is queryable via REST; Postman / curl verification
**Deliverables**:
- `GET /api/nodes` — all nodes + current_state + last_seen
- `GET /api/nodes/{id}/data?limit=50` — recent readings per node
- `GET /api/alerts?limit=20` — recent alert events
- `GET /api/health` — uptime, total packets ingested
- CORS enabled for React frontend on localhost:5173
**Requirements**: SPEC § REST API Surface

### Phase 4: WebSocket Hub
**Status**: ⬜ Not Started
**Objective**: React dashboard receives live updates via WebSocket within 1s of sensor data arriving
**Deliverables**:
- `ws/hub.py` — BroadcastHub (per-client bounded queues, fan-out)
- `GET /ws` — WebSocket endpoint: snapshot on connect, delta stream
- WebSocket message envelope schema (type: snapshot | reading | alert)
- Heartbeat ping/pong (30s interval)
- Integration test: mock publisher → backend → ws client receives update
**Requirements**: SPEC § Success Criteria (WebSocket <1s)

### Phase 5: Integration + Hardening
**Status**: ⬜ Not Started
**Objective**: Backend connects to real ESP32 hardware; thresholds calibrated; 24h stress test passes
**Deliverables**:
- End-to-end test with real gateway ESP32 publishing MQTT
- Alert back-publish verified (LED/buzzer fires on CRITICAL)
- Threshold tuning session with live sensor data → update `config.json`
- 24h continuous run log (no crash, no memory leak)
- `README.md` — how to start Mosquitto + backend for demo day
**Requirements**: SPEC § Success Criteria (all)
