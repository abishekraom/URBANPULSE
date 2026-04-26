---
phase: 4
plan: 01
---

# Plan 4.01: WebSocket Hub Architecture

## Objective
Implement a high-performance WebSocket Hub to push live telemetrics and alerts to connected frontend clients within a sub-second latency envelope.

## Scope
1. Create `backend/ws/hub.py` implementing `BroadcastHub` for managing connected WebSocket clients.
2. The Hub should handle connecting, disconnecting, and fanning out messages.
3. Use bounded asyncio queues per client or direct `send_json` (FastAPI handles backpressure, but we should manage disconnection cleanly).
4. Implement `GET /ws` endpoint in `backend/api/routers/ws.py`.
5. Wire the WebSocket router into `main.py`.
6. Establish integration between `Pipeline` (when a new alert/reading is processed) and `BroadcastHub` to trigger live pushes.

## Execution Steps
1. Write `ws/hub.py`.
2. Write `api/routers/ws.py`.
3. Update `main.py` and `core/pipeline.py` to broadcast generated data.
4. Verify by running a simple websocket client script or mock.
