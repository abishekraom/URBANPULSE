# UrbanPulse API and Payload Contracts

## Canonical identity decision

Canonical node IDs are stringified integers:

```text
"1", "2", "3"
```

Layer mapping:

| Layer | Canonical form |
|---|---|
| Firmware HTTP JSON | numeric `1`, `2`, `3` accepted |
| Backend DB/API/WS | string IDs `"1"`, `"2"`, `"3"` |
| Frontend store keys | `Node 1`, `Node 2`, `Node 3` |
| Legacy aliases | `A/B/C` accepted only through frontend adapter where seen |

Do not add new `A/B/C` contracts unless a clear adapter is introduced.

## Current primary live path

```text
Firmware flat JSON → POST /api/sensor-data → backend internal nested payload → DB/WebSocket/frontend
```

## Firmware HTTP endpoint

### Request

```http
POST /api/sensor-data
Content-Type: application/json
```

### Firmware JSON shape

```json
{
  "node_id": 1,
  "timestamp": 123456,
  "mpu_dominant_freq": 12.0,
  "mpu_peak_amplitude": 10.0,
  "mpu_spectral_centroid": 16.0,
  "mpu_rms": 5.0,
  "piezo_dominant_freq": 300.0,
  "piezo_peak_amplitude": 100.0,
  "piezo_spectral_centroid": 360.0,
  "piezo_rms": 50.0
}
```

### Backend adapter behavior

`backend/core/firmware_adapter.py`:

- converts `node_id` to string
- preserves ESP32 timestamp as `firmware_timestamp`
- replaces canonical `ts` with server epoch milliseconds
- converts flat firmware names into nested `mpu` / `piezo`
- divides `peak_amp` and `rms` by `138.24`

Internal shape:

```json
{
  "node_id": "1",
  "firmware_timestamp": 123456,
  "ts": 1710000000000,
  "mpu": {
    "dom_freq": 12.0,
    "peak_amp": 0.0723,
    "spectral_centroid": 16.0,
    "rms": 0.0361,
    "raw_x": 0.0,
    "raw_y": 0.0,
    "raw_z": 0.0
  },
  "piezo": {
    "dom_freq": 300.0,
    "peak_amp": 0.723,
    "spectral_centroid": 360.0,
    "rms": 0.361,
    "raw_adc": 0.0
  }
}
```

### Success response

```json
{
  "status": "ok",
  "alert": "NORMAL"
}
```

`alert` can be `NORMAL`, `WARNING`, or `CRITICAL`.

### Error responses

Invalid JSON now returns HTTP 400:

```json
{
  "status": "error",
  "message": "Invalid JSON"
}
```

Missing/invalid firmware fields now return HTTP 422:

```json
{
  "status": "error",
  "message": "Missing 'node_id'"
}
```

Tests: `backend/tests/test_sensor_data_contract.py`.

## REST endpoints

| Method | Path | Purpose | Notes |
|---|---|---|---|
| `GET` | `/` | Service root | Returns service/status/version. |
| `GET` | `/api/health` | Backend status | Uptime, packet count, last packet age. |
| `GET` | `/api/config/thresholds` | Threshold config | Used by frontend FFT thresholds. |
| `GET` | `/api/nodes` | Node states | State, last_seen, health score. |
| `GET` | `/api/nodes/{node_id}/data?limit=N` | Recent readings | Returns payload JSON decoded. |
| `GET` | `/api/nodes/{node_id}/history?minutes=N` | Health score history | Has fallback for firmware-millis/no epoch rows. |
| `GET` | `/api/alerts?limit=N` | Recent alerts | Newest alerts. |
| `GET` | `/api/alerts/export` | CSV alert export | Backend CSV stream. |
| `WS` | `/ws` | Real-time stream | Snapshot + readings + alerts + node updates. |

## WebSocket contracts

### Snapshot

```json
{
  "type": "snapshot",
  "nodes": [],
  "alerts": []
}
```

### Reading

```json
{
  "type": "reading",
  "data": {
    "node_id": "1",
    "ts": 1710000000000,
    "health_score": 100,
    "severity": "NORMAL",
    "payload": {
      "node_id": "1",
      "ts": 1710000000000,
      "mpu": { "dom_freq": 12, "peak_amp": 0.1, "spectral_centroid": 15, "rms": 0.03, "raw_x": 0, "raw_y": 0, "raw_z": 0 },
      "piezo": { "dom_freq": 300, "peak_amp": 0.7, "spectral_centroid": 360, "rms": 0.2, "raw_adc": 0 }
    }
  }
}
```

### Alert

```json
{
  "type": "alert",
  "data": {
    "node_id": "1",
    "severity": "CRITICAL",
    "reason": "mpu_peak_amp_critical",
    "ts": 1710000000000
  }
}
```

Alert events are deduped by `AlertGate` for `alerts.cooldown_ms` per `(node_id, severity, reason)`.

### Node update

```json
{
  "type": "node_update",
  "data": {
    "node_id": "1",
    "state": "OFFLINE",
    "last_seen": 1710000000000,
    "last_health_score": 80
  }
}
```

### Ping/pong

Client may send text `ping`; backend replies `pong`.

## MQTT contracts

MQTT remains available for mock/test path and alert publication.

### Data topic

```text
urbanpulse/node/+/data
```

Nested payload should use canonical node IDs:

```json
{
  "node_id": "1",
  "ts": 1710000000000,
  "mpu": {
    "dom_freq": 12.0,
    "peak_amp": 0.05,
    "spectral_centroid": 16.8,
    "raw_x": 0.01,
    "raw_y": 0.0,
    "raw_z": 1.0
  },
  "piezo": {
    "dom_freq": 300.0,
    "peak_amp": 500.0,
    "spectral_centroid": 360.0,
    "raw_adc": 500.0
  }
}
```

### Heartbeat topic

```text
urbanpulse/node/+/heartbeat
```

```json
{
  "node_id": "1",
  "ts": 1710000000000
}
```

### Alert publish topic

```text
urbanpulse/alerts
```

```json
{
  "node_id": "1",
  "severity": "CRITICAL",
  "ts": 1710000000000,
  "reason": "mpu_peak_amp_critical"
}
```
