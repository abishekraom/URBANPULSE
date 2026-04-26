# RESEARCH.md — Backend Technology Research

> **Scope**: Backend only. AI/ML components discarded per project scope change.
> **Date**: 2026-04-26

---

## 1. Technology Stack Decision

### Language: Python (FastAPI)

**Why FastAPI over Flask/Node.js:**
- Flask is synchronous by default — bad for concurrent MQTT + WebSocket handling
- Node.js is viable but adds JS complexity; team is CSE-AIML so Python is natural
- **FastAPI** is async-native (asyncio), has built-in WebSocket support, auto-generates OpenAPI docs, and is production-grade fast
- FastAPI + `uvicorn` handles thousands of WS connections; for 3 nodes + a few dashboard clients, it's dramatically overkill — which means rock-solid reliability

**Decision: Python 3.11+ + FastAPI + Uvicorn**

---

## 2. MQTT Broker: Mosquitto

**What it is**: Eclipse Mosquitto — the de-facto standard lightweight MQTT broker.

**Why it fits:**
- Runs locally on Windows/Linux as a service or subprocess
- Zero configuration for local use — default port 1883, no auth needed for demo
- Sub-millisecond message routing locally
- Free, open source, battle-tested

**Configuration needed** (`mosquitto.conf`):
```
listener 1883 0.0.0.0
allow_anonymous true
```

**Alternative considered**: EMQX (more features, heavier). Overkill.

**Decision: Mosquitto v2.x**

---

## 3. Python MQTT Client: paho-mqtt

**Library**: `paho-mqtt` — the official Eclipse MQTT Python client.

**Pattern for async FastAPI integration:**

```python
# The key problem: paho-mqtt uses blocking loop_forever()
# Solution: run paho in a background thread, post to asyncio queue

import asyncio
import threading
import paho.mqtt.client as mqtt

class MQTTIngester:
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop = loop
        self.client = mqtt.Client()
        self.client.on_message = self._on_message

    def _on_message(self, client, userdata, msg):
        # Bridge from paho thread → asyncio event loop
        asyncio.run_coroutine_threadsafe(
            self.queue.put({"topic": msg.topic, "payload": msg.payload.decode()}),
            self.loop
        )

    def start(self, host="localhost", port=1883):
        self.client.connect(host, port, 60)
        self.client.subscribe("urbanpulse/node/+/data")
        threading.Thread(target=self.client.loop_forever, daemon=True).start()
```

**Key insight**: paho is not async-native. The pattern above bridges paho's thread into FastAPI's asyncio loop via `run_coroutine_threadsafe`. This is the correct, non-blocking pattern.

**Alternative**: `aiomqtt` (async-native wrapper over paho). Cleaner but adds dependency.

**Decision: paho-mqtt with thread-bridge pattern** (simpler, fewer deps)

---

## 4. Time-Series Storage: SQLite

**Why SQLite over InfluxDB:**
- InfluxDB has a 1GB+ install footprint and requires Docker or system install
- SQLite is a single `.db` file, zero install, runs on any OS
- For 12 packets/sec × 12 weeks, total data is ~7M rows — easily within SQLite's capability
- SQLite with WAL mode handles concurrent reads (REST API) and writes (ingester) without locking

**Schema design:**

```sql
-- Sensor readings (raw FFT features per node per sensor)
CREATE TABLE readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id     TEXT NOT NULL,          -- 'A', 'B', 'C'
    ts          INTEGER NOT NULL,       -- Unix ms timestamp from device
    ingested_at INTEGER NOT NULL,       -- Server-side ingestion time
    sensor      TEXT NOT NULL,          -- 'mpu' or 'piezo'
    dom_freq    REAL,
    peak_amp    REAL,
    spectral_centroid REAL
);

CREATE INDEX idx_readings_node_ts ON readings(node_id, ts DESC);

-- Alert events
CREATE TABLE alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id     TEXT NOT NULL,
    ts          INTEGER NOT NULL,
    severity    TEXT NOT NULL,          -- 'WARNING' or 'CRITICAL'
    reason      TEXT,                   -- e.g. 'piezo_peak_amp_exceeded'
    dom_freq    REAL,
    peak_amp    REAL
);

CREATE INDEX idx_alerts_ts ON alerts(ts DESC);

-- Node registry (auto-created when first packet arrives)
CREATE TABLE nodes (
    node_id     TEXT PRIMARY KEY,
    first_seen  INTEGER,
    last_seen   INTEGER,
    packet_count INTEGER DEFAULT 0,
    current_state TEXT DEFAULT 'NORMAL'  -- 'NORMAL', 'WARNING', 'CRITICAL'
);
```

**WAL mode** (run at startup):
```python
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
```

**Decision: SQLite 3 with WAL mode**

---

## 5. WebSocket Pattern: FastAPI Hub + Fan-Out

**Pattern chosen**: Broadcast Hub with per-client bounded queues (Pattern #1 from research).

**Why this pattern:**
- MQTT ingester puts events into a central `asyncio.Queue` (the "Hub")
- Hub broadcaster fans out to all connected WebSocket clients
- Per-client bounded queues (maxsize=100) prevent slow browsers from blocking the hub
- Snapshot-on-connect (Pattern #4) means judges never see an empty dashboard

**Implementation sketch:**

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio, json

app = FastAPI()

class BroadcastHub:
    def __init__(self):
        self.clients: set[tuple] = set()  # (ws, queue) pairs

    async def connect(self, ws: WebSocket) -> asyncio.Queue:
        await ws.accept()
        q = asyncio.Queue(maxsize=100)
        self.clients.add((ws, q))
        # Send snapshot immediately
        snapshot = await get_current_state()
        await ws.send_json({"type": "snapshot", "data": snapshot})
        return q

    async def disconnect(self, ws: WebSocket, q: asyncio.Queue):
        self.clients.discard((ws, q))

    async def broadcast(self, event: dict):
        for ws, q in list(self.clients):
            if q.full():
                try: q.get_nowait()  # drop oldest
                except: pass
            await q.put(event)

hub = BroadcastHub()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    q = await hub.connect(ws)
    try:
        while True:
            event = await q.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(ws, q)
```

---

## 6. Rule-Based Severity Classification

Since ML is discarded, severity is determined by **configurable thresholds** on FFT features.

**Threshold logic:**

```python
THRESHOLDS = {
    "mpu": {
        "WARNING":  {"peak_amp": 0.05},   # g
        "CRITICAL": {"peak_amp": 0.15},
    },
    "piezo": {
        "WARNING":  {"peak_amp": 2.0},    # V (ADC scaled)
        "CRITICAL": {"peak_amp": 5.0},
    }
}

def classify_severity(sensor: str, data: dict) -> str:
    t = THRESHOLDS.get(sensor, {})
    amp = data.get("peak_amp", 0)
    if amp >= t.get("CRITICAL", {}).get("peak_amp", float('inf')):
        return "CRITICAL"
    elif amp >= t.get("WARNING", {}).get("peak_amp", float('inf')):
        return "WARNING"
    return "NORMAL"
```

**Thresholds are tunable via a config file** (`config.json`) so the team can calibrate during demo week without code changes.

---

## 7. Alert Back-Publishing to MQTT

When a CRITICAL event is classified, the backend must publish back to `urbanpulse/alerts` so the ESP32 gateway can trigger LEDs/buzzer.

```python
def publish_alert(node_id: str, severity: str, reason: str):
    payload = json.dumps({
        "node_id": node_id,
        "severity": severity,
        "ts": int(time.time() * 1000),
        "reason": reason
    })
    mqtt_client.publish("urbanpulse/alerts", payload, qos=1)
```

This closes the physical feedback loop: sensor → backend → MQTT → ESP32 → LED/buzzer.

---

## 8. Data Flow Architecture (No AI/ML)

```
ESP32 Node A ──┐
ESP32 Node B ──┤──(ESP-NOW)──► Gateway ESP32 ──(MQTT)──► Mosquitto Broker
ESP32 Node C ──┘                                                │
                                                                │ paho-mqtt subscriber
                                                                ▼
                                                    FastAPI Backend (Python)
                                                    ├── MQTT Ingester (thread)
                                                    ├── Rule-Based Classifier
                                                    ├── SQLite Writer
                                                    ├── BroadcastHub (asyncio)
                                                    ├── REST API (/api/*)
                                                    ├── WebSocket (/ws)
                                                    └── MQTT Publisher (alerts back)
                                                                │
                                                    ┌───────────┴───────────┐
                                                    ▼                       ▼
                                              React Dashboard         Gateway ESP32
                                              (WebSocket client)      (LED/buzzer trigger)
```

---

## 9. Project Structure (Backend)

```
backend/
├── main.py              # FastAPI app, startup, lifespan
├── config.json          # Tunable thresholds + MQTT settings
├── mqtt/
│   ├── __init__.py
│   ├── ingester.py      # paho subscriber, thread-bridge to asyncio queue
│   └── publisher.py     # paho publisher for alert back-channel
├── db/
│   ├── __init__.py
│   ├── connection.py    # SQLite connection, WAL mode, migrations
│   └── queries.py       # All SQL query functions
├── api/
│   ├── __init__.py
│   ├── nodes.py         # /api/nodes endpoints
│   ├── alerts.py        # /api/alerts endpoints
│   └── health.py        # /api/health endpoint
├── ws/
│   ├── __init__.py
│   └── hub.py           # BroadcastHub, /ws endpoint
├── core/
│   ├── __init__.py
│   ├── classifier.py    # Rule-based severity classification
│   └── pipeline.py      # Main processing loop (dequeue → classify → store → broadcast)
├── requirements.txt
└── README.md
```

---

## 10. Dependencies

```
fastapi==0.115.x
uvicorn[standard]==0.32.x
paho-mqtt==2.1.x
websockets==13.x      # uvicorn dep, handles WS upgrade
aiofiles==24.x        # async file ops if needed
```

**No extra heavy dependencies.** All stdlib SQLite. No InfluxDB, no Redis, no Docker required.

---

## 11. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| paho-mqtt thread blocking asyncio | Medium | Thread-bridge pattern (researched) |
| SQLite lock contention (write + read simultaneously) | Low | WAL mode eliminates writer-reader blocking |
| WebSocket message drop on browser disconnect | Low | Per-client bounded queue + try/except disconnect |
| MQTT broker not running at demo | Medium | Startup script checks broker; auto-restart if missing |
| Threshold miscalibration → false CRITICAL alerts | High | `config.json` tunable without code deploy; 10x rehearsals |
| Gateway ESP32 not publishing (hardware issue) | Medium | Mock MQTT publisher script for backend testing independent of hardware |

---

## 12. Development Strategy

**Week 1-2 (Backend Phase 1):**
- Stand up FastAPI skeleton + Mosquitto
- Write mock MQTT publisher (simulates 3 ESP32 nodes) for testing without hardware
- MQTT ingester thread-bridge working

**Week 3-4 (Backend Phase 2):**
- SQLite schema + WAL mode
- Full ingestion pipeline (MQTT → classify → store)
- REST API endpoints
- WebSocket hub + broadcast

**Week 5+ (Integration):**
- Connect to real ESP32 hardware
- Tune thresholds with real sensor data
- Alert back-publish to MQTT for LED/buzzer
