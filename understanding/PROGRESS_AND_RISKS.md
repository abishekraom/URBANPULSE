# Progress and Risk Assessment

## Brutal progress estimate after optimization/hardening pass

These percentages are estimates from current code/docs/tool verification, not formal project-management truth.

| Area | Estimate | Reason |
|---|---:|---|
| Backend implementation | 88–92% | Core ingestion/scoring/storage/WS/API exists; HTTP errors, alert cooldown, unit tests, compile check, and stress test pass. |
| Frontend implementation | 85–90% | Dashboard, node identity adapter, throttled WS updates, lint/build/test, and software E2E pass. |
| Firmware implementation | 82–87% | Sensor `node2/node3` envs build; gateway ring buffer builds; hardware flash/serial still pending. |
| Hardware/demo readiness | 65–75% | Wiring/pin guide and firmware exist, but physical calibration and repeatability remain unverified. |
| Documentation/runbook | 82–88% | `understanding/` has updated references and runbook; root/public docs may still need polish later. |
| Research-paper/ML ambition | 25–35% | Rule-based classifier exists; Isolation Forest/LSTM/paper experiments not implemented in current code. |
| Overall project | **78–84%** | Software path is now coherent and verified without hardware; remaining risk is physical validation/calibration and final presentation polish. |

## Current milestone state

Using the project-bible 5-phase timeline:

- Phase 1 Foundation: complete.
- Phase 2 Core Build: complete.
- Phase 3 Integration: software integration complete; hardware repeat verification pending.
- Phase 4 Refinement: active and significantly improved.
- Phase 5 Presentation Prep: pending.

## Resolved in latest engineering pass

1. **Frontend optimization/correctness**
   - Fixed lint blockers.
   - Added `nodeIdentity.js` adapter and tests.
   - Normalized dashboard store/map/WebSocket handling to `Node 1/2/3`.
   - Guarded WebSocket reconnect cleanup.
   - Verified `npm test && npm run lint && npm run build`.

2. **Software E2E verification**
   - Added `scripts/software_e2e_smoke.py`.
   - Verified Vite proxy → backend REST → WS stream → node/API state for nodes `1/2/3`.

3. **Backend hardening**
   - HTTP invalid JSON now returns 400.
   - Missing/invalid firmware payloads now return 422.
   - Added alert cooldown/dedup via `core/alert_gate.py`.
   - Added unit tests.
   - Stress test passed: 450 packets, 0 errors, avg 21ms, p99 46.2ms.

4. **Contract alignment**
   - Canonical IDs are `"1"`, `"2"`, `"3"`.
   - Backend config/mock publisher aligned.
   - Frontend maps legacy IDs only through adapter.
   - Vite proxy defaults to backend `8001`, matching the live gateway path.

5. **Firmware hardening**
   - Sensor node PlatformIO envs: `node2`, `node3`.
   - Gateway ESP-NOW receive changed from single overwrite buffer to ring buffer.
   - `Wire.requestFrom` overload warnings fixed.
   - Sensor and gateway builds pass.

## Remaining highest-risk issues

### P0 — Physical hardware validation pending

No physical ESP32 flashing/serial/live sensor read was performed in this pass. Builds pass, but real demo confidence requires:

- flash gateway and node2/node3
- watch serial logs
- verify Node 2/3 reach gateway over ESP-NOW
- verify gateway HTTP posts to backend `8001`
- verify buzzer behavior on warning/critical

### P0 — Threshold calibration pending

Backend divides firmware FFT amplitudes/RMS by `138.24`. Real hardware output must be sampled and thresholds tuned. Current values are software-valid but not physically calibrated.

### P1 — Duplicate legacy gateway

`pio_gateway/` is canonical. Root `gateway_node/` remains divergent/legacy. Future changes should not accidentally target the root duplicate.

### P1 — Port/IP must be confirmed before flashing

Current canonical software port is `8001`. Gateway URL is:

```text
http://172.20.10.3:8001/api/sensor-data
```

Before flashing, confirm the laptop IP on the WiFi network and update `SERVER_URL` if it changed.

### P2 — Research/ML scope

The paper bible mentions Isolation Forest/LSTM. Current code is deterministic threshold/rule-based. If the submission requires ML claims, implement and evaluate an actual model or revise claims.

## Recommended next-task sequence

1. **Physical flashing loop**
   - flash gateway, node2, node3
   - monitor serial
   - fix ESP-NOW/channel/WiFi/IP issues

2. **Live hardware E2E loop**
   - backend/frontend clean start
   - gateway posts real data
   - dashboard updates without refresh
   - alerts/buzzer verified

3. **Calibration loop**
   - collect healthy baseline
   - tap/loose-joint scenarios
   - tune thresholds in `backend/config.json`
   - repeat until false positives are acceptable

4. **Presentation/demo polish**
   - run demo script repeatedly
   - prepare fallback mock mode
   - update public README/report with screenshots/results
