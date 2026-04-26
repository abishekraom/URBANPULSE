import asyncio
import json
import logging
import threading
import paho.mqtt.client as mqtt

logger = logging.getLogger("urbanpulse.mqtt.ingester")

class MQTTIngester:
    def __init__(self, config: dict, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._config = config
        self._queue = queue
        self._loop = loop
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._connected = False

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("MQTT connect failed: %s", reason_code)
            return
        self._connected = True
        client.subscribe(self._config["topics"]["data_subscribe"])
        client.subscribe(self._config["topics"]["heartbeat_subscribe"])
        logger.info("✓ MQTT ingester connected and subscribed")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            event = {"topic": msg.topic, "payload": payload}
            asyncio.run_coroutine_threadsafe(self._queue.put(event), self._loop)
        except json.JSONDecodeError as e:
            logger.warning("Malformed MQTT payload on %s: %s", msg.topic, e)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        logger.warning("MQTT ingester disconnected (reason: %s)", reason_code)

    def start(self):
        broker = self._config["broker"]
        self._client.connect(broker["host"], broker["port"], broker["keepalive"])
        thread = threading.Thread(target=self._client.loop_forever, daemon=True, name="mqtt-ingester")
        thread.start()
        logger.info("MQTT ingester thread started")

    def stop(self):
        self._client.disconnect()
        logger.info("MQTT ingester stopped")
