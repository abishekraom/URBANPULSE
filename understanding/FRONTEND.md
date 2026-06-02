# Frontend Reference

**Path:** `D:/URBANPULSE/frontend`  
**Stack:** React 19 + Vite 8 + Tailwind v4 + Zustand + Recharts + canvas visualization  
**Entrypoint:** `frontend/src/main.jsx` → `frontend/src/App.jsx`

## Current status after optimization pass

The frontend is now in a **verified optimized/connected state** for the software-only pipeline.

Verified commands:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Result: **all pass**.

Software E2E with backend + Vite proxy + WebSocket also passed via:

```bash
python scripts/software_e2e_smoke.py
```

Observed result:

```text
vite_api_health_ok healthy
ws_snapshot_type snapshot nodes 3
post 1 {'status': 'ok', 'alert': 'NORMAL'}
post 2 {'status': 'ok', 'alert': 'WARNING'}
post 3 {'status': 'ok', 'alert': 'WARNING'}
reading_ids ['1', '2', '3']
api_nodes ['1', '2', '3']
```

## Purpose

The frontend is the UrbanPulse live operations dashboard. It displays system state, per-node health cards, FFT visualization, historical score chart, structural map, raw readings, alerts, and backend connectivity.

## Vite/backend integration

`frontend/vite.config.js` now proxies to backend port `8001` by default, matching the live gateway/backend path:

```text
/api → http://localhost:8001
/ws  → ws://localhost:8001
```

Override if needed:

```bash
VITE_BACKEND_HTTP=http://localhost:8000 VITE_BACKEND_WS=ws://localhost:8000 npm run dev
```

## Canonical node identity

Canonical node IDs are stringified integers:

```text
"1", "2", "3"
```

Frontend display keys are:

```text
Node 1, Node 2, Node 3
```

`src/nodeIdentity.js` is the adapter layer. It accepts legacy `A/B/C`, bare integers, and `Node X`, then normalizes to canonical `Node 1/2/3` for store keys.

`src/nodeIdentity.test.mjs` covers this adapter and is wired into `npm test`.

## State model

`src/store.js` defines Zustand state:

- `nodes`
  - initial keys from `CANONICAL_NODE_NAMES`: `Node 1`, `Node 2`, `Node 3`
  - each has score, state, severity, readings, fft, lastUpdate
- `events`, capped at 50
- `activeNode`
- `wsConnected`
- `healthHistory`
- `expandedCard`
- `thresholds`

Store updates now avoid unnecessary writes when values are unchanged.

## Component map

| File | Purpose |
|---|---|
| `src/App.jsx` | Main orchestration: REST fetches, WebSocket handling, node/event mapping, throttled layout updates. |
| `src/nodeIdentity.js` | Canonical node-ID adapter. |
| `src/nodeIdentity.test.mjs` | Node identity unit tests. |
| `src/components/StatusBanner.jsx` | Top status/branding/clock/fullscreen bar. |
| `src/components/NodeCard.jsx` | Per-node health card with gauge and live readings. |
| `src/components/FFTWaveform.jsx` | Canvas FFT/spectrum visualization with threshold lines and tabs. |
| `src/components/HistoricalChart.jsx` | Recharts health-score history panel. |
| `src/components/StructuralMap.jsx` | SVG bridge/frame map with node status colors; now uses canonical node names. |
| `src/components/RawDataGrid.jsx` | Tabular raw accel/piezo readings. |
| `src/components/AlertTimeline.jsx` | Event/alert timeline and frontend-local CSV export. |
| `src/components/Footer.jsx` | Backend health, packet stats, node connectivity, WS status. |

## REST calls used by frontend

| Endpoint | Called by | Expected shape |
|---|---|---|
| `GET /api/config/thresholds` | `App.jsx`, passed to FFT | Backend threshold config JSON. |
| `GET /api/nodes/{id}/history?minutes=10` | `App.jsx` | `[{ ts, score }]` for IDs `1`, `2`, `3`. |
| `GET /api/health` | `Footer.jsx` | `{ uptime_s, total_packets, last_packet_age_ms, status }`. |

## WebSocket handling

`App.jsx` connects to `/ws` and handles:

- `snapshot`
- `reading`
- `alert`
- `node_update`

Optimization fixes applied:

1. Node IDs normalized through `toNodeName()`.
2. RAF-throttled pending node updates retained.
3. Reconnect timer is now cleanup-guarded, so React StrictMode/unmount does not spawn zombie reconnects.
4. Alert/node update equality checks prevent redundant store writes.
5. Lint/stale closure problems fixed.

## Frontend optimization verdict

Your teammate’s optimization idea was directionally right, but the frontend still had correctness hazards before this pass: stale lint issues, node-ID split risk, reconnect cleanup risk, and map naming mismatch. These are now fixed and verified.

## Remaining frontend caveats

- Browser visual QA with real hardware is still pending.
- Alert CSV export is frontend-local; backend also has `/api/alerts/export` but UI does not call it yet.
- `canvas-gauges` and `uplot` may still be unused dependencies and can be pruned later if desired.
