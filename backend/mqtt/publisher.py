import json
import logging
import time
import paho.mqtt.client as mqtt

logger = logging.getLogger("urbanpulse.mqtt.publisher")

class MQTTPublisher:
    def __init__(self, config: dict):
        self._config = config
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def connect(self):
        broker = self._config["broker"]
        self._client.connect(broker["host"], broker["port"], broker["keepalive"])
        self._client.loop_start()
        logger.info("✓ MQTT publisher connected")

    def publish_alert(self, node_id: str, severity: str, reason: str):
        payload = json.dumps({
            "node_id": node_id,
            "severity": severity,
            "ts": int(time.time() * 1000),
            "reason": reason,
        })
        topic = self._config["topics"]["alert_publish"]
        self._client.publish(topic, payload, qos=1)
        logger.info("Alert published → %s: %s [%s]", topic, node_id, severity)

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()
