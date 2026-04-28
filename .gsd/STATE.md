# STATE.md — UrbanPulse Project State

## Current Position
- **Phase**: Integration (Frontend ↔ Backend)
- **Task**: Complete — WebSocket + REST connection wired
- **Status**: Ready for manual verification

## What Was Done (this session)
- Fixed WebSocket URL: `ws://localhost:8080` → `ws://localhost:8000/ws`
- Rewrote `App.jsx` WS message handler to parse structured backend envelopes:
  - `type: "snapshot"` — initial node state + alert history on connect
  - `type: "reading"` — live sensor updates (health score + formatted readings)
  - `type: "alert"` — WARNING/CRITICAL events pushed to AlertTimeline
  - `type: "node_update"` — heartbeat-driven node score refresh
- Fixed node ID mapping: backend `"A"/"B"/"C"` → frontend `"Node A"/"Node B"/"Node C"`
- Fixed payload field parsing: `payload.mpu.raw_x/raw_y` → `accelX/accelY`; `payload.piezo.raw_adc / 410` → voltage string
- Added Vite dev-server proxy (`/api`, `/ws`) → `localhost:8000`
- Updated seed event URLs in `store.js` and `App.jsx` to `ws://localhost:8000/ws`
- RAF-based batch flusher retained; now keyed by node name (object, not array) for deduplication

## How to Run (Manual Verification)

### Terminal 1 — Start Mosquitto
```
mosquitto.exe -c backend\mosquitto.conf -v
```

### Terminal 2 — Start Backend
```
cd backend
uvicorn main:app --reload --port 8000
```

### Terminal 3 — Start Mock Publisher (simulate sensor data)
```
cd backend
python mock_publisher.py --mode normal
```
Or fault simulation:
```
python mock_publisher.py --mode fault --node B
```

### Terminal 4 — Start Frontend
```
cd frontend
npm run dev
```
Open: http://localhost:5173

## Next Steps
- Manual verification: confirm node cards update live from mock publisher
- Confirm alert timeline populates on `--mode fault`
- Phase 5 hardware integration when ESP32 available