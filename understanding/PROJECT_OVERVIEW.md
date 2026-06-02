# UrbanPulse Project Overview

## Problem being solved

Urban infrastructure degrades invisibly. Bridges, flyovers, columns, retaining walls, and elevated structures can develop fatigue, micro-cracks, and loose joints before visible cracks appear. UrbanPulse aims to detect these hidden changes through vibration/acoustic signatures.

## Product objective

Build a low-cost multi-node Structural Health Monitoring (SHM) system that:

1. Samples vibration/acoustic features using MPU-6050 + piezo discs.
2. Extracts FFT-domain features on ESP32 devices.
3. Sends telemetry wirelessly to a gateway/backend.
4. Scores structural health and flags Normal / Warning / Critical events.
5. Displays live state through a React dashboard.
6. Triggers physical buzzer/LED-style feedback for demo-critical alerts.

## Intended architecture from project bible

```text
Physical sensing
  MPU-6050 acceleration + piezo acoustic/stress signal
        ↓
Edge processing
  ESP32 computes FFT features: dominant frequency, peak amplitude, spectral centroid, RMS
        ↓
Wireless mesh
  Node 2/3 send ESP-NOW packets to gateway Node 1
        ↓
Backend + scoring
  FastAPI ingests HTTP/MQTT, stores SQLite, scores severity/health
        ↓
Dashboard
  React/Vite receives WebSocket readings, fetches REST history/config
        ↓
Physical alert
  Gateway buzzer responds to backend alert severity
```

## Actual current architecture in code

The implemented live path is:

```text
sensor_node/src/sensor_node.ino      pio_gateway/src/gateway_node.ino
Node 2 / Node 3  ─ ESP-NOW packet ─▶ Gateway Node 1
                                                   │
                                                   ▼
                                  HTTP POST /api/sensor-data
                                                   │
                                                   ▼
                                       backend/main.py FastAPI
                                  SQLite + scoring + WebSocket
                                                   │
                                                   ▼
                                      frontend/src/App.jsx dashboard
```

MQTT still exists in backend for mock/testing:

```text
mock_publisher.py or MQTT nodes
  └─▶ urbanpulse/node/+/data
      └─▶ MQTTIngester → process_queue → DB/alerts/WebSocket
```

## Key project-bible expectations vs current code

| Bible expectation | Current code state |
|---|---|
| 3 ESP32 nodes | Implemented pattern: gateway Node 1 + sensor sender Node 2/3. Sensor firmware currently hardcodes `NODE_ID 2`, so Node 3 needs source/build flag change. |
| ESP-NOW mesh | Implemented as direct ESP-NOW node-to-gateway, not a complex self-healing mesh. Good enough for demo. |
| On-device FFT | Implemented in firmware using `arduinoFFT@1.6.0`, 512 samples. |
| Backend ML anomaly detection | Current code is threshold/rule-based classifier + health scoring, not Isolation Forest/LSTM. |
| SQLite demo storage | Implemented. |
| React dashboard | Implemented with live WebSocket/REST integration. |
| Physical alert | Implemented as gateway buzzer behavior based on HTTP response alert. LED strip not observed as implemented in current firmware. |
| Research paper stretch | Not implemented in codebase. |

## Core product truth

UrbanPulse is no longer just a scaffold. It has backend, frontend, firmware, mock/test scripts, and integration glue. The remaining work is not “start building”; it is **stabilization, contract alignment, demo calibration, documentation cleanup, and test hardening**.
