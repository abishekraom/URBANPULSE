# DECISIONS.md — Architecture Decision Records

> Format: ADR-NNN | Date | Decision | Rationale | Status

---

## ADR-001 | 2026-04-26 | Python + FastAPI over Flask / Node.js

**Decision**: Use Python 3.11+ with FastAPI as the backend framework.

**Rationale**:
- Flask is synchronous — cannot natively handle concurrent MQTT subscriber + WebSocket server without threading hacks
- FastAPI is async-native (asyncio), handles WS natively, generates API docs automatically
- Team background is CSE-AIML — Python is the natural fit
- FastAPI + uvicorn handles thousands of connections; 3 nodes + N dashboard clients is trivially within budget

**Status**: ACCEPTED

---

## ADR-002 | 2026-04-26 | Mosquitto as MQTT broker

**Decision**: Use Eclipse Mosquitto v2.x as the local MQTT broker.

**Rationale**:
- Zero-weight, single binary, runs on Windows and Linux
- No authentication needed for local demo network
- Latency <1ms local routing
- EMQX is heavier with no additional benefit for this scale

**Status**: ACCEPTED

---

## ADR-003 | 2026-04-26 | SQLite with WAL mode over InfluxDB

**Decision**: Store all sensor readings and alerts in SQLite (WAL mode).

**Rationale**:
- InfluxDB requires Docker or a system service; unsuitable for a portable demo laptop setup
- SQLite is a single file, zero install, works everywhere Python runs
- 12 packets/sec × 12 weeks ≈ 7M rows — easily within SQLite performance envelope
- WAL mode eliminates reader-writer locking (concurrent REST reads + ingester writes)

**Status**: ACCEPTED

---

## ADR-004 | 2026-04-26 | Rule-based severity classification (no ML)

**Decision**: Replace Isolation Forest + LSTM anomaly detection with configurable threshold-based rules.

**Rationale**:
- User explicitly requested removal of all AI/ML components
- Threshold rules on FFT features (peak_amp for MPU and piezo) are transparent, debuggable, and tunable without retraining
- Config-file-based thresholds allow calibration on demo day without code changes

**Status**: ACCEPTED

---

## ADR-005 | 2026-04-26 | paho-mqtt with thread-bridge over aiomqtt

**Decision**: Use `paho-mqtt` in a background daemon thread, bridging events to the asyncio event loop via `run_coroutine_threadsafe`.

**Rationale**:
- paho-mqtt is the most mature, well-documented MQTT Python library
- aiomqtt is a thin async wrapper — adds a dependency for marginal benefit at this scale
- Thread-bridge pattern is well-understood, deterministic, and testable
- Keeps the dependency list minimal

**Status**: ACCEPTED

---

## ADR-006 | 2026-04-26 | BroadcastHub WebSocket pattern

**Decision**: Implement a central BroadcastHub with per-client bounded asyncio queues.

**Rationale**:
- Decouples MQTT ingester (producer) from WebSocket clients (consumers)
- Bounded queues (maxsize=100) prevent slow browsers from blocking the hub
- Snapshot-on-connect pattern eliminates "empty dashboard" problem for judges
- Pattern is proven at production scale (researched from FastAPI WebSocket patterns guide)

**Status**: ACCEPTED

---

## Phase 1 Discussion Decisions | 2026-04-26

### Q1 — Severity Thresholds
**Decision**: Use literature-backed defaults from published SHM studies (IIETA bridge sensor study + PMC smart city pole monitoring paper).

| Sensor | Normal | Warning | Critical |
|---|---|---|---|
| MPU peak_amp (g) | < 0.3g | 0.3 – 0.8g | > 0.8g |
| Piezo ADC (12-bit) | < 800 | 800 – 2000 | > 2000 |
| Health score | ≥ 70 (green) | 40 – 69 (amber) | < 40 (red) |

Thresholds stored in `config.json` — tunable after first hardware test without code changes.

**Status**: ACCEPTED (pending calibration in Phase 5)

---

### Q2 — Repository Layout
**Decision**: Single repo (`d:\URBANPULSE\`). Backend in `backend/` subdirectory. Frontend in `frontend/` (separate session).

**Status**: ACCEPTED

---

### Q3 — Mock Publisher Fault Simulation
**Decision**: `mock_publisher.py` supports two modes:
- `--mode normal` — continuous healthy packets (default)
- `--mode fault --node B` — 10-second CRITICAL burst on specified node (piezo ADC > 2000), then returns to normal

This simulates the loose-bolt demo scenario without any hardware.

**Status**: ACCEPTED

---

### Q4 — Mosquitto Deployment
**Decision**: Mosquitto runs as a standalone `.exe` launched manually (not a Windows service). Backend startup checks port 1883 and prints a clear error + launch instructions if broker is unreachable.

**Status**: ACCEPTED

---

## ADR-007 | 2026-04-26 | Health Score computed in backend

**Decision**: Backend computes a 0–100 health score from FFT features per node. Firmware sends raw FFT features only.

**Rationale**: Frontend gauge widgets need a single normalized number. Computing in backend keeps firmware simple and makes the score algorithm centrally configurable via `config.json`.

**Status**: ACCEPTED

---

## ADR-008 | 2026-04-26 | Node heartbeat + OFFLINE detection

**Decision**: Firmware publishes `urbanpulse/node/<id>/heartbeat` every 5s. Backend marks node OFFLINE if no heartbeat for 10s and broadcasts a `node_status` WebSocket event.

**Rationale**: Frontend has an explicit "Node Connection Status" widget. Silent freeze during demo = catastrophic UX. 10s timeout gives 2 missed heartbeats before flagging — tolerant of one dropped packet.

**Status**: ACCEPTED

---

## ADR-009 | 2026-04-26 | Extended REST API surface

**Decision**: Add 3 endpoints beyond original SPEC:
- `GET /api/nodes/{id}/history?minutes=10` — health score trend for historical chart
- `GET /api/alerts/export` — CSV download for paper results
- `GET /api/config/thresholds` — serves Warning/Critical values for FFT threshold reference lines

**Status**: ACCEPTED

---

## ADR-010 | 2026-04-26 | Raw sensor values in MQTT payload

**Decision**: Firmware must include `mpu.raw_x/y/z` (g-force) and `piezo.raw_adc` (12-bit int) in the MQTT payload. Backend stores and serves these.

**Rationale**: Frontend "Raw Sensor Readings" panel proves real data is flowing — important for judge credibility. Cannot be populated without raw values in the payload.

**Action**: ECE team must be informed of updated payload schema before firmware is written.

**Status**: ACCEPTED
