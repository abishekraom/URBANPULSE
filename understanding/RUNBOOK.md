# UrbanPulse Runbook

## Canonical assumptions

- Project root: `D:/URBANPULSE`
- Backend live port: `8001`
- Frontend dev port: `5173`
- Canonical node IDs: `1`, `2`, `3`
- Canonical frontend display names: `Node 1`, `Node 2`, `Node 3`
- Canonical gateway firmware: `pio_gateway/src/gateway_node.ino`

## Clean stale processes

If the dashboard/backend feels stale, first check ports:

```bash
netstat -ano 2>/dev/null | grep -E ':(8001|5173) .*LISTENING' || true
```

Kill stale PIDs only when you are sure they are old test/dev servers:

```bash
taskkill //PID <PID> //F
```

## Start backend

From `D:/URBANPULSE/backend`:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Verify:

```bash
curl http://localhost:8001/
curl http://localhost:8001/api/health
curl http://localhost:8001/api/config/thresholds
```

## Start frontend

From `D:/URBANPULSE/frontend`:

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Vite proxy defaults to backend port `8001`.

If you intentionally need backend `8000`, override:

```bash
VITE_BACKEND_HTTP=http://localhost:8000 VITE_BACKEND_WS=ws://localhost:8000 npm run dev -- --host 0.0.0.0 --port 5173
```

## Frontend checks

From `D:/URBANPULSE/frontend`:

```bash
npm test && npm run lint && npm run build
```

Current verified state: **passes**.

## Backend checks

From `D:/URBANPULSE/backend`:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v && python -m compileall -q .
```

Current verified state: **passes**.

## Software-only E2E smoke test

Start backend on `8001` and frontend on `5173`, then from `D:/URBANPULSE`:

```bash
python scripts/software_e2e_smoke.py
```

Expected key output:

```text
vite_api_health_ok healthy
ws_snapshot_type snapshot nodes 3
reading_ids ['1', '2', '3']
api_nodes ['1', '2', '3']
```

## Backend performance sanity

Start backend on `8001`, then:

```bash
cd backend
python stress_test.py --host 127.0.0.1 --port 8001 --rate 30 --duration 5 --all-nodes
```

Latest verified result:

```text
450 packets, 0 errors, avg latency 21.0ms, p99 46.2ms, verdict ALL CHECKS PASSED
```

## Firmware build checks

From `D:/URBANPULSE/sensor_node`:

```bash
pio run -e node2 && pio run -e node3
```

From `D:/URBANPULSE/pio_gateway`:

```bash
pio run
```

Current verified state: **all pass**.

## Flashing firmware

PlatformIO configs currently reference:

- gateway upload port: `COM10`
- sensor node2 upload port: `COM12`
- sensor node3 upload port: `COM11`

Memory says laptop has ESP32 ports COM10/11/12. Confirm before flashing.

Gateway:

```bash
cd D:/URBANPULSE/pio_gateway
pio run -t upload
```

Node 2:

```bash
cd D:/URBANPULSE/sensor_node
pio run -e node2 -t upload
```

Node 3:

```bash
cd D:/URBANPULSE/sensor_node
pio run -e node3 -t upload
```

## HTTP smoke packet

Post a synthetic firmware packet to backend:

```bash
curl -X POST http://localhost:8001/api/sensor-data -H 'Content-Type: application/json' -d '{"node_id":1,"timestamp":123456,"mpu_dominant_freq":12.0,"mpu_peak_amplitude":10.0,"mpu_spectral_centroid":16.0,"mpu_rms":5.0,"piezo_dominant_freq":300.0,"piezo_peak_amplitude":100.0,"piezo_spectral_centroid":360.0,"piezo_rms":50.0}'
```

Expected response shape:

```json
{"status":"ok","alert":"NORMAL"}
```

Then verify:

```bash
curl http://localhost:8001/api/nodes
curl http://localhost:8001/api/nodes/1/data?limit=5
curl http://localhost:8001/api/nodes/1/history?minutes=10
```

## Demo readiness checklist

Before a physical demo:

1. Confirm backend process is clean on `8001`.
2. Confirm laptop IP matches gateway `SERVER_URL` (`172.20.10.3` may change by network).
3. Confirm gateway MAC in sensor firmware: `C0:CD:D6:84:87:10`.
4. Flash gateway, node2, node3.
5. Open serial monitor for gateway and at least one sensor node.
6. Start backend and frontend from clean terminals.
7. Run HTTP smoke packet before physical sensors.
8. Verify dashboard updates without manual refresh.
9. Verify `/api/nodes` and `/api/alerts` reflect live state.
10. Trigger warning/critical and verify buzzer behavior.
11. Tune thresholds in `backend/config.json` based on real readings.
12. Rehearse full loose-joint/tap script repeatedly.

## Troubleshooting quick map

| Symptom | First check |
|---|---|
| Dashboard says disconnected | Is backend running on Vite proxy port? Check `/api/health`. |
| Gateway serial says HTTP failed | Backend IP/port in `SERVER_URL`, same WiFi, firewall. |
| Node cards update but map stale | Canonical node mapping; should be `Node 1/2/3`. |
| History chart empty | Check `/api/nodes/{id}/history`; use IDs `1/2/3`. |
| Alerts flood | Check `alerts.cooldown_ms` and thresholds. |
| Sensor node not reaching gateway | Gateway MAC, ESP-NOW channel, WiFi credentials/channel sync. |
| Port 8000 weird/stale | Use `8001`; check zombie process. |
