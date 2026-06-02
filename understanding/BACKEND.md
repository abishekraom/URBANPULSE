# Backend Reference

**Path:** `D:/URBANPULSE/backend`  
**Stack:** FastAPI + SQLite + Paho MQTT + WebSockets  
**Entrypoint:** `backend/main.py`

## Current status after hardening pass

Backend ingestion, WebSocket fanout, tests, and performance sanity have been verified.

Verified commands:

```bash
cd backend
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q .
python stress_test.py --host 127.0.0.1 --port 8001 --rate 30 --duration 5 --all-nodes
```

Results:

```text
Ran 4 tests ... OK
compileall: OK
Stress: 450 packets, 0 errors, avg latency 21.0ms, p99 46.2ms, max 49.2ms, verdict ALL CHECKS PASSED
```

## Purpose

The backend ingests structural sensor telemetry, normalizes firmware/mock payloads, classifies severity, computes health scores, stores readings/alerts in SQLite, and pushes live updates to the frontend through WebSocket.

## Runtime startup

`main.py` FastAPI lifespan:

1. Load `config.json`.
2. Check MQTT broker reachability.
3. Reset DB nodes to `OFFLINE` with `last_seen=0`.
4. Initialize:
   - `app.state.freq_baselines = {}`
   - `app.state.freq_baseline_lock`
   - `app.state.alert_gate = AlertGate(...)`
   - `app.state.queue = asyncio.Queue(maxsize=1000)`
5. If broker reachable:
   - start `MQTTIngester`
   - connect `MQTTPublisher`
   - start `process_queue(app.state)`
6. Always start:
   - `heartbeat_monitor(app.state)`
   - WebSocket throttle loop `hub.start_throttle(app.state)`

If MQTT is unavailable, the backend still runs in HTTP-only mode.

## Key files

| File | Purpose |
|---|---|
| `main.py` | App creation, lifespan startup/shutdown, router mounting, global app state. |
| `config.json` | Broker, topics, thresholds, heartbeat timeout, alert cooldown, API defaults, mock settings. |
| `api/routers/sensor_data.py` | HTTP firmware ingestion endpoint `/api/sensor-data`; now returns proper 400/422 for malformed payloads. |
| `core/alert_gate.py` | In-memory alert cooldown/dedup gate per node/severity/reason. |
| `core/firmware_adapter.py` | Converts flat ESP32 firmware JSON to nested backend payload; applies FFT scaling. |
| `core/contract.py` | Strict MQTT payload validators for nested data/heartbeat contracts. |
| `core/pipeline.py` | MQTT queue processor: validate → baseline → classify → score → DB → WS/MQTT alerts. |
| `core/classifier.py` | Threshold-based severity classifier. |
| `core/health_score.py` | Health score penalty logic and frequency-deviation penalty. |
| `core/heartbeat.py` | Offline monitor and node_update broadcasts. |
| `db/connection.py` | SQLite DB path/schema/indexes/WAL settings. |
| `db/queries.py` | Read/write helpers, history fallback, retention purge. |
| `ws/hub.py` | WebSocket client manager, throttled fanout, dedup/backpressure. |
| `mock_publisher.py` | Demo/test telemetry publisher over MQTT or HTTP; default node IDs now align to `1/2/3`. |
| `tests/test_sensor_data_contract.py` | HTTP error contract tests. |
| `tests/test_alert_gate.py` | Alert cooldown tests. |

## Data flows

### HTTP firmware path — current primary hardware path

```text
ESP32 gateway
  └─POST /api/sensor-data
      └─firmware_to_internal()
          └─classify_reading()
              └─compute_health_score()
                  └─insert_reading()/upsert_node()
                      └─WebSocket reading broadcast
                      └─if alert and cooldown permits: insert_alert() + publish_alert() + WS alert
```

### MQTT path — mock/testing path

```text
urbanpulse/node/+/data
  └─MQTTIngester._on_message()
      └─app.state.queue
          └─process_queue()
              └─validate_data_payload()
              └─classify/score/store/broadcast
              └─if alert and cooldown permits: DB/MQTT/WS alert
```

## SQLite model

Database path: `backend/urbanpulse.db`

Tables:

```sql
nodes(node_id TEXT PRIMARY KEY, state TEXT, last_seen INTEGER, last_health_score INTEGER)
readings(id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, ts INTEGER, health_score INTEGER, severity TEXT, payload_json TEXT)
alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, severity TEXT, reason TEXT, ts INTEGER)
```

## Canonical node IDs

The backend stores canonical node IDs as strings:

```text
"1", "2", "3"
```

`backend/config.json` and `mock_publisher.py` have been aligned to this scheme.

## Alert lifecycle

`core/alert_gate.py` suppresses duplicate alerts inside `config.json`:

```json
"alerts": {
  "cooldown_ms": 5000
}
```

Cooldown key:

```text
(node_id, severity, reason)
```

Different node/severity/reason combinations still emit immediately.

## Backend risks / caveats

1. MQTT broker is only checked at startup; no later reconnect path if it starts late.
2. Synchronous SQLite calls happen in async routes/tasks; stress test is healthy for current demo-scale rates, but production-scale deployments should move writes to a worker or async DB layer.
3. Frequency baselines reset on backend restart.
4. Security is minimal: no auth; `mosquitto.conf` allows anonymous clients.
5. `endurance_test.py` had a previously noted stale DB path risk and should be checked before long soak use.
