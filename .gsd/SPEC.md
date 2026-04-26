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

**Payload (JSON)** — firmware must send this exact structure:
```json
{
  "node_id": "A",
  "ts": 1714123456789,
  "mpu": {
    "dom_freq": 12.4,
    "peak_amp": 0.032,
    "spectral_centroid": 18.7,
    "raw_x": 0.012,
    "raw_y": -0.004,
    "raw_z": 1.001
  },
  "piezo": {
    "dom_freq": 340.2,
    "peak_amp": 1.24,
    "spectral_centroid": 410.5,
    "raw_adc": 2048
  }
}
```

> **Note on raw values**: `mpu.raw_x/y/z` are in g-force. `piezo.raw_adc` is the 12-bit ADC value (0–4095). These are needed for the frontend "Raw Sensor Readings" panel and the latency indicator.

### Heartbeat (Inbound)
```
urbanpulse/node/<node_id>/heartbeat
```
Payload: `{"node_id": "A", "ts": 1714123456789}` — published every 5s by firmware. Backend uses this to detect node disconnect (no heartbeat for 10s → OFFLINE).
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

## Health Score Algorithm

Health score (0–100) is **computed by the backend** from FFT features using literature-backed thresholds. The score maps to color: ≥70 = green, 40–69 = amber, <40 = red.

```
health_score = 100

MPU peak_amp thresholds (g-force, from IIETA bridge SHM study):
  NORMAL   < 0.3 g   → no penalty
  WARNING  0.3–0.8 g → score -= 30
  CRITICAL > 0.8 g   → score -= 60

Piezo peak_amp thresholds (ADC units, scaled 0–4095):
  NORMAL   ADC < 800    → no penalty
  WARNING  ADC 800–2000 → score -= 30
  CRITICAL ADC > 2000   → score -= 60

Frequency deviation penalty:
  If dom_freq deviates >20% from node's established baseline → score -= 10

Final: clamp(health_score, 0, 100)
```

> **Calibration note**: These defaults are derived from published SHM literature (bridge/pole monitoring with MEMS sensors). After first hardware test, values in `config.json` will be adjusted to match the actual tabletop steel frame's response characteristics.

---

## REST API Surface

| Method | Path | Description |
|---|---|---|
| GET | `/api/nodes` | All nodes: state, health_score, last_seen, online status |
| GET | `/api/nodes/{id}/data?limit=N` | Last N readings (FFT features + raw values + health_score) |
| GET | `/api/nodes/{id}/history?minutes=10` | Health score trend for last N minutes (for trend chart) |
| GET | `/api/alerts?limit=N` | Timestamped alert events across all nodes |
| GET | `/api/alerts/export` | CSV download of full alert log |
| GET | `/api/health` | System: uptime, total packets, last packet age (latency indicator) |
| GET | `/api/config/thresholds` | Current threshold values (for FFT chart reference lines) |
| WS  | `/ws` | Real-time stream: snapshot on connect, then deltas |

---

## Frontend Data Contract

Complete map of what the backend must serve to each frontend widget:

| Dashboard Widget | Data Source | Update Mechanism |
|---|---|---|
| Per-Node Health Gauges (×3) | health_score 0–100 per node | WebSocket delta every ~500ms |
| Live FFT Waveform | dom_freq + peak_amp spectrum per node | WebSocket delta |
| SVG Structural Map | node state (NORMAL/WARNING/CRITICAL/OFFLINE) | WebSocket delta |
| Alert Timeline | alerts table (ts, node_id, severity, reason) | WebSocket alert event + REST |
| System State Banner | worst severity across all nodes | WebSocket delta |
| Raw Sensor Panel | mpu.raw_x/y/z, piezo.raw_adc | WebSocket delta |
| Node Connection Status | online/offline per node (heartbeat timeout) | WebSocket delta |
| FFT Threshold Lines | config thresholds | REST `/api/config/thresholds` (once on load) |
| Historical Trend Chart | health_score over last 5–10 min | REST `/api/nodes/{id}/history?minutes=10` |
| Latency Indicator | last_packet_age_ms + packet_count | REST `/api/health` (polled every 5s) |
| CSV Export | full alert log | REST `/api/alerts/export` |

---

## WebSocket Message Envelope

All WS messages follow this envelope:

```json
{ "type": "snapshot" | "reading" | "alert" | "node_status", "ts": 1714123456789, "data": { ... } }
```

**snapshot** (sent once on connect):
```json
{ "type": "snapshot", "data": { "nodes": [...], "recent_alerts": [...], "thresholds": {...} } }
```

**reading** (every ~500ms per node):
```json
{ "type": "reading", "data": { "node_id": "B", "health_score": 72, "severity": "NORMAL", "mpu": {...}, "piezo": {...} } }
```

**alert** (on WARNING/CRITICAL trigger):
```json
{ "type": "alert", "data": { "node_id": "B", "severity": "CRITICAL", "reason": "piezo_peak_amp_exceeded", "ts": ... } }
```

**node_status** (on heartbeat timeout):
```json
{ "type": "node_status", "data": { "node_id": "C", "online": false } }
```

---

## Success Criteria

- [ ] MQTT messages from mock publisher are ingested and stored within 100ms
- [ ] WebSocket clients receive updates within 1s of data arrival
- [ ] Health score computed correctly for all 3 nodes
- [ ] Rule-based severity fires CRITICAL alert when piezo peak_amp exceeds threshold
- [ ] Alert published back to MQTT `urbanpulse/alerts` (LED/buzzer)
- [ ] Node shows OFFLINE within 10s of heartbeat stopping
- [ ] `/api/nodes/{id}/history` returns 10 min of health score trend
- [ ] `/api/alerts/export` returns valid CSV
- [ ] `/api/config/thresholds` returns current Warning/Critical values
- [ ] Mock publisher includes fault simulation mode (high amplitude burst)
- [ ] System runs 24h without crash or memory leak
- [ ] Backend works offline with zero internet calls
