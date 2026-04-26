# SPEC.md — UrbanPulse Project Specification

> **Status**: `FINALIZED`
> **Version**: 1.0
> **Date**: 2026-04-26
> **Source**: Derived from `urbanpulse_project_bible.html`

---

## Vision

UrbanPulse is a low-cost, wireless, multi-node Structural Health Monitoring (SHM) system that continuously detects anomalous vibration signatures in urban infrastructure (bridges, flyovers, columns) using ESP32 sensor nodes with MPU-6050 + piezoelectric sensors, processes data on-device via FFT, transmits over an ESP-NOW mesh to an MQTT gateway, and presents real-time structural health data on a React web dashboard — all at a ₹500/node cost point vs ₹50,000+ for commercial systems.

---

## Goals

1. **Core backend pipeline** — MQTT ingestion → time-series storage → REST API → WebSocket broadcast — running locally without internet dependency
2. **Multi-node telemetry** — Handle 3 ESP32 sensor nodes simultaneously, each publishing FFT features (dominant frequency, peak amplitude, spectral centroid) every 500ms
3. **Real-time dashboard delivery** — Sub-1s data freshness on the React frontend via WebSocket with `<50ms` gateway-to-backend latency
4. **Alert system** — Severity classification (Normal / Warning / Critical) persisted as events, retrievable via REST, and published back to gateway MQTT for physical LED/buzzer trigger
5. **Demo reliability** — System must run 100% offline on a laptop for 24+ hours without internet

---

## Non-Goals (Out of Scope — AI/ML Discarded)

- ~~Isolation Forest anomaly detection model~~
- ~~LSTM autoencoder for research paper~~
- ~~ML training pipeline or model evaluation~~
- ~~Baseline data collection script for ML~~
- ~~Anomaly scoring system~~
- Cloud deployment / internet connectivity
- Mobile app
- Multi-tenant or auth system
- InfluxDB (out of scope for this demo phase; SQLite is sufficient)

> **Note**: All AI/ML features originally planned for the CSE-AIML Member 1 role have been explicitly discarded per user instruction. Severity classification will be **rule-based** (threshold on FFT features), not ML-based.

---

## Users

- **Demo operator** (team member): Runs the full system locally on a laptop during exhibition. Monitors dashboard, induces demo faults, observes alert pipeline.
- **Exhibition judges**: View the React dashboard on laptop/phone, observe real-time updates, alert timeline, and structural map responding to physical events.

---

## System Boundaries (What Backend Owns)

| Concern | Owner |
|---|---|
| MQTT broker (Mosquitto) | Local process on laptop |
| MQTT subscriber / message ingestion | **Backend (Python FastAPI)** |
| Time-series storage | **Backend (SQLite)** |
| Rule-based severity classification | **Backend** |
| REST API for dashboard data | **Backend** |
| WebSocket broadcast for real-time | **Backend** |
| MQTT publisher (back to gateway for alerts) | **Backend** |
| ESP-NOW mesh, ESP32 firmware, FFT | ECE members (firmware) |
| React dashboard UI | CSE-AIML Member 2 (frontend) |

---

## Constraints

- **Offline-only**: No cloud, no internet. Everything runs on a single laptop (`localhost`).
- **Low budget**: SQLite over InfluxDB. Mosquitto (free). Python + FastAPI (free).
- **Timeline**: 12-week project. Backend target: complete by Week 4 (Phase 2).
- **Hardware**: 3 ESP32 sensor nodes, each publishing to MQTT topic `urbanpulse/node/<id>`.
- **Data rate**: 3 nodes × 2 sensors × 1 FFT packet per 500ms = ~12 packets/second max.
- **Laptop host**: Windows or Linux. Backend must work on both (Python cross-platform).

---

## MQTT Contract (Interface with Firmware)

### Topics (Inbound — node → backend)

```
urbanpulse/node/<node_id>/data
```

**Payload (JSON)**:
```json
{
  "node_id": "A",
  "ts": 1714123456789,
  "mpu": {
    "dom_freq": 12.4,
    "peak_amp": 0.032,
    "spectral_centroid": 18.7
  },
  "piezo": {
    "dom_freq": 340.2,
    "peak_amp": 1.24,
    "spectral_centroid": 410.5
  }
}
```

### Topics (Outbound — backend → gateway)

```
urbanpulse/alerts
```

**Payload (JSON)**:
```json
{
  "node_id": "B",
  "severity": "CRITICAL",
  "ts": 1714123456789,
  "reason": "piezo_peak_amp_exceeded"
}
```

---

## REST API Surface

| Method | Path | Description |
|---|---|---|
| GET | `/api/nodes` | List all registered nodes + current health state |
| GET | `/api/nodes/{id}/data?limit=N` | Last N readings for a node |
| GET | `/api/alerts?limit=N` | Recent alert events across all nodes |
| GET | `/api/health` | System health check (uptime, packet count) |
| WS | `/ws` | Real-time event stream (snapshot on connect + deltas) |

---

## Success Criteria

- [ ] MQTT messages from simulated ESP32 (MQTT client script) are ingested and stored within 100ms
- [ ] WebSocket clients receive updates within 1s of data arrival
- [ ] REST API returns all 3 node states correctly
- [ ] Rule-based severity fires CRITICAL alert when piezo peak amplitude exceeds threshold
- [ ] Alert is published back to MQTT `urbanpulse/alerts` topic
- [ ] System runs 24h without crash or memory leak
- [ ] Backend works offline with zero internet calls
