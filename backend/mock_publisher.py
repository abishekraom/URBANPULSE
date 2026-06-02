"""
UrbanPulse — Mock Sensor Data Publisher

Simulates 3 ESP32 sensor nodes. Supports two transports:
  --transport mqtt   (default)  Publish via MQTT to Mosquitto broker
  --transport http              POST flat JSON directly to FastAPI (firmware-compatible)

HTTP mode matches the format the ESP32 gateway firmware actually sends.
"""
import argparse
import json
import logging
import random
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mock_publisher")

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


# ── MQTT-mode packets (nested format for MQTT pipeline) ──────────────────────

def generate_normal_mqtt(node_id: str) -> dict:
    mpu_dom_freq = random.uniform(8.0, 15.0)
    piezo_dom_freq = random.uniform(200.0, 500.0)
    return {
        "node_id": node_id,
        "ts": int(time.time() * 1000),
        "mpu": {
            "dom_freq": mpu_dom_freq,
            "peak_amp": random.uniform(0.01, 0.08),
            "spectral_centroid": mpu_dom_freq * 1.4,
            "raw_x": random.uniform(0.001, 0.02),
            "raw_y": random.uniform(-0.01, 0.01),
            "raw_z": random.uniform(0.98, 1.02)
        },
        "piezo": {
            "dom_freq": piezo_dom_freq,
            "peak_amp": random.uniform(100.0, 600.0),
            "spectral_centroid": piezo_dom_freq * 1.2,
            "raw_adc": random.uniform(100.0, 600.0)
        }
    }


def generate_fault_mqtt(node_id: str, config: dict) -> dict:
    mpu_dom_freq = random.uniform(8.0, 15.0) * 1.4
    piezo_dom_freq = random.uniform(200.0, 500.0) * 1.4
    return {
        "node_id": node_id,
        "ts": int(time.time() * 1000),
        "mpu": {
            "dom_freq": mpu_dom_freq,
            "peak_amp": config["mock"]["fault_mpu_peak_amp_g"],
            "spectral_centroid": mpu_dom_freq * 1.4,
            "raw_x": 0.8,
            "raw_y": random.uniform(-0.01, 0.01),
            "raw_z": random.uniform(0.98, 1.02)
        },
        "piezo": {
            "dom_freq": piezo_dom_freq,
            "peak_amp": config["mock"]["fault_piezo_adc"],
            "spectral_centroid": piezo_dom_freq * 1.2,
            "raw_adc": config["mock"]["fault_piezo_adc"]
        }
    }


# ── HTTP-mode packets (flat JSON matching ESP32 firmware format) ──────────────
# Values start as physical units (g-force for MPU, volts for piezo), then
# converted to FFT magnitude to match what the ESP32 firmware actually sends.
# FFT magnitude = physical_amplitude * 138.24 (512 samples, Hamming window)
FFT_SCALE = 138.24


def generate_normal_http(node_id_int: int) -> dict:
    mpu_dom_freq = random.uniform(8.0, 15.0)
    piezo_dom_freq = random.uniform(200.0, 500.0)

    # Physical values
    mpu_peak_g = random.uniform(0.01, 0.08)   # Normal MPU: 0.01-0.08g
    piezo_peak_v = random.uniform(0.05, 0.4)   # Normal piezo: 0.05-0.4V FFT magnitude

    return {
        "node_id": node_id_int,
        "timestamp": int(time.time() * 1000),
        "mpu_dominant_freq": mpu_dom_freq,
        "mpu_peak_amplitude": round(mpu_peak_g * FFT_SCALE, 4),  # Convert to FFT magnitude
        "mpu_spectral_centroid": mpu_dom_freq * 1.4,
        "mpu_rms": round(mpu_peak_g * 0.6, 4),
        "piezo_dominant_freq": piezo_dom_freq,
        "piezo_peak_amplitude": round(piezo_peak_v * FFT_SCALE, 4),  # Convert to FFT magnitude
        "piezo_spectral_centroid": piezo_dom_freq * 1.2,
        "piezo_rms": round(piezo_peak_v * 0.5, 4),
    }


def generate_fault_http(node_id_int: int, config: dict) -> dict:
    mpu_dom_freq = random.uniform(10.0, 18.0) * 1.3
    piezo_dom_freq = random.uniform(300.0, 500.0) * 1.3

    # Fault: MPU > 0.8g, piezo > 2.0V
    mpu_peak_g = config["mock"]["fault_mpu_peak_amp_g"]  # 1.2g
    # Convert fault_piezo_adc (2500) to equivalent voltage
    # ADC 2500 → 2500 * 3.3/4095 ≈ 2.01V → exceeds 2.0V critical threshold
    piezo_peak_v = config["mock"]["fault_piezo_adc"] * 3.3 / 4095

    return {
        "node_id": node_id_int,
        "timestamp": int(time.time() * 1000),
        "mpu_dominant_freq": mpu_dom_freq,
        "mpu_peak_amplitude": round(mpu_peak_g * FFT_SCALE, 4),
        "mpu_spectral_centroid": mpu_dom_freq * 1.4,
        "mpu_rms": round(mpu_peak_g * 0.6, 4),
        "piezo_dominant_freq": piezo_dom_freq,
        "piezo_peak_amplitude": round(piezo_peak_v * FFT_SCALE, 4),
        "piezo_spectral_centroid": piezo_dom_freq * 1.2,
        "piezo_rms": round(piezo_peak_v * 0.5, 4),
    }


# ── High-frequency burst mode ─────────────────────────────────────────────────
# Simulates real piezo data arriving fast (up to 60Hz) to test the throttling

def generate_highfreq_http(node_id_int: int, burst: bool = False) -> dict:
    """Generate a reading at ~60Hz (every 16ms)."""
    mpu_dom_freq = random.uniform(8.0, 15.0)
    piezo_dom_freq = random.uniform(200.0, 500.0)

    if burst:
        # Piezo burst: high amplitude, simulates real sensor chatter
        mpu_peak_g = random.uniform(0.05, 0.15)
        piezo_peak_v = random.uniform(1.5, 3.0)  # spikes up to 3V
    else:
        mpu_peak_g = random.uniform(0.01, 0.08)
        piezo_peak_v = random.uniform(0.05, 0.4)

    return {
        "node_id": node_id_int,
        "timestamp": int(time.time() * 1000),
        "mpu_dominant_freq": mpu_dom_freq,
        "mpu_peak_amplitude": round(mpu_peak_g * FFT_SCALE, 4),
        "mpu_spectral_centroid": mpu_dom_freq * 1.4,
        "mpu_rms": round(mpu_peak_g * 0.6, 4),
        "piezo_dominant_freq": piezo_dom_freq,
        "piezo_peak_amplitude": round(piezo_peak_v * FFT_SCALE, 4),
        "piezo_spectral_centroid": piezo_dom_freq * 1.2,
        "piezo_rms": round(piezo_peak_v * 0.5, 4),
    }


# ── Transport implementations ────────────────────────────────────────────────

def run_mqtt(args, config):
    nodes = config["mock"]["nodes"]
    publish_interval = config["mock"]["publish_interval_s"]
    fault_duration = config["mock"]["fault_duration_s"]

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(args.host, args.port, 60)
    except ConnectionRefusedError:
        logger.error(f"Cannot connect to MQTT broker at {args.host}:{args.port}")
        return

    client.loop_start()
    logger.info(f"MQTT mode — connected to broker at {args.host}:{args.port}")

    fault_start_time = time.time() if args.mode == "fault" else 0
    fault_active = args.mode == "fault"

    last_heartbeat = {node: 0 for node in nodes}
    heartbeat_interval = 5.0

    try:
        while True:
            current_time = time.time()

            if fault_active and current_time - fault_start_time > fault_duration:
                fault_active = False
                logger.info(f"← Node {args.node} fault cleared")

            for node_id in nodes:
                is_faulted = fault_active and node_id == args.node
                packet = generate_fault_mqtt(node_id, config) if is_faulted else generate_normal_mqtt(node_id)
                severity = "CRITICAL" if is_faulted else "NORMAL"

                topic = f"urbanpulse/node/{node_id}/data"
                client.publish(topic, json.dumps(packet), qos=0)

                adc = int(packet["piezo"]["raw_adc"])
                amp = packet["mpu"]["peak_amp"]
                logger.info(f"→ MQTT Node {node_id} [{severity}] piezo={adc:4d} mpu={amp:.3f}g")

                # Heartbeat
                if current_time - last_heartbeat[node_id] >= heartbeat_interval:
                    hb_topic = f"urbanpulse/node/{node_id}/heartbeat"
                    client.publish(hb_topic, json.dumps({"node_id": node_id, "ts": int(current_time*1000)}), qos=0)
                    last_heartbeat[node_id] = current_time

            time.sleep(publish_interval)

    except KeyboardInterrupt:
        logger.info("Interrupted.")
    finally:
        client.loop_stop()
        client.disconnect()


def run_http(args, config):
    publish_interval = args.interval  # Use CLI argument
    fault_duration = config["mock"]["fault_duration_s"]
    server_url = f"http://{args.host}:{args.port}/api/sensor-data"

    # Hardware-compatible node IDs (integers 1, 2, 3 matching firmware)
    node_ids_int = [1, 2, 3]
    node_labels = {1: "Node 1", 2: "Node 2", 3: "Node 3"}

    fault_start_time = time.time() if args.mode == "fault" else 0
    fault_active = args.mode == "fault"

    # Map --node arg to integer
    fault_node_int = {"A": 1, "B": 2, "C": 3}.get(args.node, 2)

    # High-frequency mode: burst config
    burst_active = False
    burst_start_time = 0
    burst_duration = 10.0
    burst_interval = 0.016  # ~60Hz burst

    logger.info(f"HTTP mode — posting to {server_url} (interval={publish_interval}s)")

    # Track real packet timing for stats
    last_log_time = time.time()
    packet_count = 0

    try:
        while True:
            current_time = time.time()

            # Check fault mode
            if fault_active and current_time - fault_start_time > fault_duration:
                fault_active = False
                logger.info(f"← Node {fault_node_int} fault cleared")

            # Check burst mode (high-frequency piezo simulation)
            if args.mode == "burst":
                if not burst_active:
                    burst_active = True
                    burst_start_time = current_time
                    logger.info("🔥 BURST MODE — simulating high-frequency piezo data")
                elif current_time - burst_start_time > burst_duration:
                    burst_active = False
                    logger.info("← Burst ended, returning to normal rate")
                    # After burst, just sleep and exit
                    time.sleep(1)
                    break

            # Select interval based on mode
            current_interval = burst_interval if burst_active else publish_interval

            for node_id_int in node_ids_int:
                is_faulted = fault_active and node_id_int == fault_node_int

                if burst_active:
                    packet = generate_highfreq_http(node_id_int, burst=True)
                    severity = "BURST"
                elif is_faulted:
                    packet = generate_fault_http(node_id_int, config)
                    severity = "CRITICAL"
                else:
                    packet = generate_normal_http(node_id_int)
                    severity = "NORMAL"

                body = json.dumps(packet).encode("utf-8")
                req = urllib.request.Request(
                    server_url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        alert = resp_data.get("alert", "NORMAL")
                        packet_count += 1
                        if burst_active:
                            # Quiet logging in burst mode to avoid spam
                            if packet_count % 60 == 0:
                                logger.info(
                                    f"→ BURST [{packet_count} packets] "
                                    f"Node {node_labels[node_id_int]} "
                                    f"piezo_amp={packet['piezo_peak_amplitude']:.1f}"
                                )
                        else:
                            logger.info(
                                f"→ HTTP {node_labels[node_id_int]} [{severity}] "
                                f"mpu_amp={packet['mpu_peak_amplitude']:.3f}g "
                                f"alert={alert}"
                            )
                except Exception as e:
                    logger.warning(f"HTTP POST failed for {node_labels[node_id_int]}: {e}")

            # Log throughput periodically
            if time.time() - last_log_time >= 5.0:
                elapsed = time.time() - last_log_time
                rate = packet_count / max(elapsed, 0.001)
                logger.info(f"📊 Throughput: {packet_count} packets | {rate:.0f} pkts/s")
                packet_count = 0
                last_log_time = time.time()

            time.sleep(current_interval)

    except KeyboardInterrupt:
        logger.info("Interrupted.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="UrbanPulse Mock Publisher")
    parser.add_argument("--mode", choices=["normal", "fault", "burst"], default="normal",
                        help="Simulation mode (burst = high-frequency piezo stress test)")
    parser.add_argument("--node", choices=["A", "B", "C"], default="B", help="Node to fault")
    parser.add_argument("--transport", choices=["mqtt", "http"], default="http",
                        help="Transport protocol (default: http — matches real hardware)")
    parser.add_argument("--host", default="127.0.0.1", help="Broker host (mqtt) or server host (http)")
    parser.add_argument("--port", type=int, default=None, help="Broker port (mqtt) or server port (http)")
    parser.add_argument("--interval", type=float, default=None,
                        help="Publish interval in seconds (default: 0.5 for normal, 0.016 for burst)")
    args = parser.parse_args()

    config = load_config()

    # Default ports
    if args.port is None:
        if args.transport == "mqtt":
            args.port = 1883
        else:
            args.port = 8000

    # Default interval based on mode
    if args.interval is None:
        if args.mode == "burst":
            args.interval = 0.5  # Normal interval between cycles (each cycle sends 3 nodes)
        else:
            args.interval = config["mock"]["publish_interval_s"]

    if args.transport == "mqtt":
        run_mqtt(args, config)
    else:
        run_http(args, config)


if __name__ == "__main__":
    main()
