"""UrbanPulse software-only E2E smoke test.

Requires backend on 127.0.0.1:8001 and Vite frontend on 127.0.0.1:5173.
Verifies the Vite proxy, backend HTTP ingestion, WebSocket stream, and node IDs
without requiring physical ESP32 hardware.
"""
import asyncio
import json
import time
import urllib.request

import websockets

HTTP = "http://127.0.0.1:5173"
WS = "ws://127.0.0.1:5173/ws"


def post_packet(node_id: int, amp: float, piezo: float) -> dict:
    payload = {
        "node_id": node_id,
        "timestamp": int(time.time() * 1000),
        "mpu_dominant_freq": 12.0 + node_id,
        "mpu_peak_amplitude": amp,
        "mpu_spectral_centroid": 16.0 + node_id,
        "mpu_rms": amp / 2,
        "piezo_dominant_freq": 300.0 + node_id,
        "piezo_peak_amplitude": piezo,
        "piezo_spectral_centroid": 360.0 + node_id,
        "piezo_rms": piezo / 2,
    }
    req = urllib.request.Request(
        HTTP + "/api/sensor-data",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode())


async def main() -> None:
    health = json.loads(urllib.request.urlopen(HTTP + "/api/health", timeout=5).read().decode())
    print("vite_api_health_ok", health["status"])

    readings = []
    async with websockets.connect(WS, open_timeout=5) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        print("ws_snapshot_type", first.get("type"), "nodes", len(first.get("nodes", [])))

        for node_id, amp, piezo in [(1, 8.0, 80.0), (2, 12.0, 120.0), (3, 16.0, 160.0)]:
            print("post", node_id, post_packet(node_id, amp, piezo))

        deadline = time.time() + 8
        seen = set()
        while time.time() < deadline and len(seen) < 3:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            except asyncio.TimeoutError:
                continue
            if msg.get("type") == "reading":
                data = msg["data"]
                readings.append(data)
                seen.add(data["node_id"])
                print("reading", data["node_id"], data["health_score"], data["severity"])

    ids = sorted({r["node_id"] for r in readings})
    print("reading_ids", ids)
    assert ids == ["1", "2", "3"], ids

    nodes = json.loads(urllib.request.urlopen(HTTP + "/api/nodes", timeout=5).read().decode())
    api_node_ids = sorted(n["node_id"] for n in nodes)
    print("api_nodes", api_node_ids)
    assert set(["1", "2", "3"]).issubset(api_node_ids), api_node_ids


if __name__ == "__main__":
    asyncio.run(main())
