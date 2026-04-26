import argparse
import json
import logging
import random
import time
from pathlib import Path
import paho.mqtt.client as mqtt

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

def generate_normal_packet(node_id: str) -> dict:
    mpu_dom_freq = random.uniform(8.0, 15.0)
    piezo_dom_freq = random.uniform(200.0, 500.0)
    return {
        "node_id": node_id,
        "timestamp": int(time.time() * 1000),
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

def generate_fault_packet(node_id: str, config: dict) -> dict:
    mpu_dom_freq = random.uniform(8.0, 15.0) * 1.4  # 40% higher
    piezo_dom_freq = random.uniform(200.0, 500.0) * 1.4
    return {
        "node_id": node_id,
        "timestamp": int(time.time() * 1000),
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

def main():
    parser = argparse.ArgumentParser(description="UrbanPulse Mock Publisher")
    parser.add_argument("--mode", choices=["normal", "fault"], default="normal", help="Simulation mode")
    parser.add_argument("--node", choices=["A", "B", "C"], default="B", help="Node to apply fault to (if mode=fault)")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    args = parser.parse_args()

    config = load_config()
    nodes = config["mock"]["nodes"]
    publish_interval = config["mock"]["publish_interval_s"]
    fault_duration = config["mock"]["fault_duration_s"]
    
    # Setup MQTT
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(args.host, args.port, 60)
    except ConnectionRefusedError:
        logger.error(f"Cannot connect to MQTT broker at {args.host}:{args.port}")
        return
        
    client.loop_start()
    logger.info(f"Connected to MQTT broker at {args.host}:{args.port}")
    
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
                is_node_faulted = fault_active and node_id == args.node
                
                if is_node_faulted:
                    packet = generate_fault_packet(node_id, config)
                    severity = "CRITICAL"
                else:
                    packet = generate_normal_packet(node_id)
                    severity = "NORMAL"
                    
                topic = f"urbanpulse/node/{node_id}/data"
                client.publish(topic, json.dumps(packet), qos=0)
                
                # Print log
                adc = int(packet["piezo"]["raw_adc"])
                amp = packet["mpu"]["peak_amp"]
                logger.info(f"→ Node {node_id} [{severity}] piezo={adc:4d} mpu={amp:.3f}g")
                
                # Heartbeat
                if current_time - last_heartbeat[node_id] >= heartbeat_interval:
                    hb_topic = f"urbanpulse/node/{node_id}/heartbeat"
                    client.publish(hb_topic, json.dumps({"node_id": node_id, "timestamp": int(current_time*1000)}), qos=0)
                    last_heartbeat[node_id] = current_time
                    
            time.sleep(publish_interval)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
