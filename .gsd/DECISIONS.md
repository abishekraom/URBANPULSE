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
