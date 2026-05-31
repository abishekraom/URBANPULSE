# STATE.md — UrbanPulse Project State

## Current Position
- **Phase**: Integration Complete — All systems wired
- **Status**: Ready for hardware integration testing

## What Has Been Done

### Backend Pipeline (FastAPI)
- MQTT ingestion via `mqtt/ingester.py` (paho subscriber → asyncio queue)
- HTTP POST ingestion via `api/routers/sensor_data.py` (firmware-compatible flat JSON → adapter → pipeline)
- Rule-based severity classification (`core/classifier.py`) — NORMAL/WARNING/CRITICAL
- Health score 0–100 (`core/health_score.py`) with configurable penalties
- SQLite time-series storage (`db/connection.py` — WAL mode, 3 tables)
- Node heartbeat monitor (`core/heartbeat.py` — 10s timeout → OFFLINE)
- Alert back-publish to MQTT (`mqtt/publisher.py`)
- REST API (7 endpoints): nodes, data, history, alerts, CSV export, health, thresholds
- WebSocket broadcast hub (`ws/hub.py`) — snapshot on connect + delta stream
- Packet statistics tracking (total_packets, last_packet_age_ms)
- MQTT contract validation (`core/contract.py`) — catches firmware format issues
- Firmware format adapter (`core/firmware_adapter.py`) — converts flat JSON to nested

### Frontend (React + Vite + Tailwind v4)
- **StatusBanner** — system-wide status with fullscreen toggle + live clock
- **NodeCard** (×3) — circular SVG health gauges with online/offline state
- **FFTWaveform** — Canvas-based live FFT using real backend dom_freq/peak_amp data
- **HistoricalChart** — Recharts line graph fetched from REST API `/api/nodes/{id}/history`
- **StructuralMap** — SVG structural frame with color-coded node status
- **AlertTimeline** — event log with auto-scroll + CSV export
- **RawDataGrid** — tabular raw sensor values
- **Footer** — real backend metrics (uptime, packets, packet age from `/api/health`)
- Threshold lines fetched from `/api/config/thresholds` on mount
- WebSocket auto-reconnect (3s retry) with RAF-based batch flusher
- Vite dev-server proxies REST (`/api`) and WebSocket (`/ws`)

### Mock Publisher (`mock_publisher.py`)
- **MQTT mode** (`--transport mqtt`): sends nested JSON to Mosquitto broker (testing)
- **HTTP mode** (`--transport http`): sends flat JSON matching firmware format to FastAPI directly
- Both modes support `--mode normal` and `--mode fault --node B`

### Firmware (Arduino, 2 files at project root)
- `sensor_node.ino` — runs on Node 2, Node 3: MPU-6050 + piezo FFT → ESP-NOW
- `gateway_node.ino` — runs on Node 1: reads own sensors + receives ESP-NOW → HTTP POST to FastAPI

## Key Architecture Note
The ESP32 gateway uses **HTTP POST** (not MQTT) to send data to the backend.
The MQTT pipeline is retained for testing purposes only.

## How to Run

### Terminal 1 — Start Backend
```
cd backend
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```
Note: `--host 0.0.0.0` needed for ESP32 to reach the server on the laptop's IP.

### Terminal 2 — Start Mock Publisher (HTTP mode, no MQTT needed)
```
cd backend
python mock_publisher.py --transport http --mode normal
```
Or fault simulation:
```
python mock_publisher.py --transport http --mode fault --node B
```

### Terminal 3 — Start Frontend
```
cd frontend
npm run dev
```
Open: http://localhost:5173

### For ESP32 Hardware
1. Update `gateway_node.ino` with your laptop's local IP
2. Flash gateway + sensor nodes
3. Backend and frontend running as above — hardware POSTs to `/api/sensor-data`

## Data Flow
```
ESP32 Sensor Nodes (Node 2, 3)
  → ESP-NOW mesh
    → ESP32 Gateway (Node 1, reads own sensors too)
      → HTTP POST /api/sensor-data (flat JSON)
        → firmware_adapter.py (converts to internal format)
          → classifier.py + health_score.py
            → SQLite storage
              → WebSocket broadcast → React dashboard
              ← HTTP response { "alert": "NORMAL|WARNING|CRITICAL" }
                 → gateway checks alert field → buzzer trigger
```

Or for testing (no hardware):
```
mock_publisher.py --transport http
  → HTTP POST /api/sensor-data
    → same pipeline as above
```
