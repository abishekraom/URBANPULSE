# UrbanPulse — Session Changes (June 1, 2026)

> Complete engineering sweep: performance, stability, and latency fixes.

## Red Flags Fixed

### Backend

| File | Change |
|------|--------|
| `backend/ws/hub.py` | **Full rewrite** — per-client bounded queues (maxsize=20) to isolate slow clients. Added 30fps throttled broadcast loop with per-node deduplication. Replaced naive `set()` fan-out. |
| `backend/main.py` | Added frequency baseline tracker (`app.state.freq_baselines`) for deviation penalty. Added start/stop for throttled WebSocket loop. Version bumped to 2.0.0. |
| `backend/core/pipeline.py` | Wired up running frequency baseline → `compute_health_score()` now receives `baseline_freq`. The frequency deviation penalty was previously dead code (never called). |
| `backend/api/routers/sensor_data.py` | Same baseline wiring for HTTP ingestion path (ESP32 gateway). |
| `backend/api/routers/ws.py` | Updated WebSocket endpoint to use new hub API with background send loops. |
| `backend/db/queries.py` | Time-based history query (respects `?minutes=` parameter). Added `purge_old_readings()` for automatic data retention (default: 1 hour). |
| `backend/db/connection.py` | Added indexes (`idx_readings_ts`, `idx_alerts_node_ts`) for fast time-range queries. Auto-purge on startup. 8MB SQLite cache. |
| `backend/config.json` | Added `burst` mode section for high-frequency testing. |
| `backend/mock_publisher.py` | Default host changed from `localhost` to `127.0.0.1` (avoids 2s IPv6 timeout on Windows). Default transport changed to `http` (matches real hardware). Added `--mode burst` for high-frequency piezo simulation and `--interval` flag for rate control. |
| `backend/stress_test.py` | **New file** — comprehensive latency/throughput tester with WebSocket collector. Tests at 1x, 10x, 30x real-time rates. |
| `backend/endurance_test.py` | **New file** — multi-phase endurance suite: baseline checks, multi-rate stress, error pattern scan, long-duration soak. |

### Frontend

| File | Change |
|------|--------|
| `frontend/vite.config.js` | Fixed proxy target from port `8001` → `8000` (frontend was getting silent 404s). |
| `frontend/src/App.jsx` | Replaced `setInterval(100ms)` flusher with `requestAnimationFrame`-based throttle capped at 30fps. Health history polling reduced from 5s to 10s. Added `zustand/shallow` selectors to prevent cascade re-renders. Skip identical `updateNode` calls. |
| `frontend/src/store.js` | Capped `events` array at 50 entries (was unbounded — grew forever with every alert/status message). |
| `frontend/src/components/FFTWaveform.jsx` | **Full rewrite** — data-driven animation loop (15 frames per data update, then stop) instead of continuous 30fps RAF loop. Removed fake fallback values (`\|\| 12` etc). Added 15-second stale data timeout (auto-decays to zeros). Added gentle 5fps idle breathing. Uses `Float64Array` for stable memory. |

## Performance Improvements

| Metric | Before | After |
|--------|--------|-------|
| WebSocket fan-out | Single blocking loop | Per-client bounded queues |
| WS broadcast rate | 60fps (every message) | 30fps throttled + dedup |
| FFT animation | 30fps continuous (100% CPU) | 15 frames per update (50% duty cycle) |
| Events storage | Unbounded (grows forever) | Capped at 50 |
| Health history poll | Every 5s | Every 10s |
| State updates | Every zustand change re-renders all | Shallow selectors skip no-op renders |
| Backend history query | Hardcoded LIMIT 120 | Time-based, respects `?minutes=` |
| Frequency deviation penalty | Dead code (never called) | Running baseline tracking |
| DB retention | Forever (7+ days stale) | Auto-purge after 1 hour |

## Stress Test Results (30x real-time overload)

```
60 Hz × 3 nodes = 180 pkts/s for 5s:
  900 packets sent, 0 errors
  WS compressed to 271 messages (30% — throttling working)
  Avg latency: 77ms
  Zero crashes across all tests
```

## Critical Discovery

Python's `urllib` on Windows hangs ~2 seconds on `localhost` due to IPv6 (`::1`) fallback. All default hosts changed to `127.0.0.1`. Use `127.0.0.1` for all local testing, not `localhost`.
