---
phase: 1
plan: 02
wave: 2
depends_on: [1.01]
files_modified:
  - backend/mqtt/ingester.py
  - backend/mqtt/publisher.py
  - backend/main.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "paho-mqtt subscriber runs in a background daemon thread, never blocking asyncio"
    - "Messages arriving on urbanpulse/node/+/data are pushed into an asyncio.Queue"
    - "Messages arriving on urbanpulse/node/+/heartbeat are pushed into the same queue"
    - "Backend can publish to urbanpulse/alerts via publisher without blocking"
    - "main.py lifespan starts the ingester on startup and stops it on shutdown"
  artifacts:
    - "backend/mqtt/ingester.py with MQTTIngester class"
    - "backend/mqtt/publisher.py with MQTTPublisher class"
    - "backend/main.py updated: ingester started in lifespan, queue exposed on app.state"
---

# Plan 1.02: MQTT Ingester + Publisher

<objective>
Implement the two MQTT modules: ingester (paho subscriber bridged to asyncio queue) and publisher (paho client for sending alert back-channel). Wire both into main.py lifespan.

Purpose: This is the critical async-bridge that all data flow depends on. The paho-blocking-thread → asyncio.Queue pattern must be implemented correctly here or the entire pipeline breaks.
Output: backend can receive MQTT data and publish alerts. Queue is on app.state for pipeline to consume.
</objective>

<context>
Load for context:
- .gsd/RESEARCH.md (§3 paho-mqtt, §5 WebSocket Pattern — understand the queue pattern)
- .gsd/SPEC.md (§ MQTT Contract — exact topic strings and payload structure)
- backend/main.py (to understand lifespan and config structure)
- backend/config.json (for topic and broker values)
</context>

<tasks>

<task type="auto">
  <name>Create mqtt/ingester.py — paho subscriber with asyncio thread-bridge</name>
  <files>
    backend/mqtt/ingester.py
  </files>
  <action>
    Create MQTTIngester class with this exact pattern:

    ```python
    import asyncio, json, logging, threading
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
    ```

    AVOID: using asyncio.run() inside _on_message — it creates a new event loop. Use run_coroutine_threadsafe().
    AVOID: mqtt.CallbackAPIVersion.VERSION1 — VERSION2 is required for paho-mqtt >= 2.0.
    AVOID: storing the thread reference — daemon=True means it dies with the process automatically.
  </action>
  <verify>
    python -c "from mqtt.ingester import MQTTIngester; print('Import OK')"
    (Run from backend/ directory)
    Expected: Import OK (no errors)
  </verify>
  <done>
    - MQTTIngester importable without errors
    - Uses CallbackAPIVersion.VERSION2 (paho-mqtt 2.x compatible)
    - Thread is daemon=True
    - _on_message uses run_coroutine_threadsafe, not asyncio.run()
  </done>
</task>

<task type="auto">
  <name>Create mqtt/publisher.py + wire ingester into main.py lifespan</name>
  <files>
    backend/mqtt/publisher.py
    backend/main.py
  </files>
  <action>
    1. Create backend/mqtt/publisher.py:
       ```python
       import json, logging
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
               import time
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
       ```

    2. Update backend/main.py lifespan to:
       - Create asyncio.Queue(maxsize=1000) — store on app.state.queue
       - Create MQTTIngester(config, queue, asyncio.get_event_loop()) — store on app.state.ingester
       - Create MQTTPublisher(config) — store on app.state.publisher
       - On startup: call ingester.start() and publisher.connect() (only if broker is reachable)
       - On shutdown: call ingester.stop() and publisher.disconnect()
       - Keep existing broker check — if not reachable, log warning but skip ingester.start()

    AVOID: calling asyncio.get_event_loop() outside the async lifespan context — pass it from inside.
    AVOID: loop_start() on the ingester client — the ingester uses loop_forever() in a thread.
    USE: loop_start() only on the publisher client (it uses non-blocking mode).
  </action>
  <verify>
    With Mosquitto running (mosquitto.exe -c mosquitto.conf -v):
    uvicorn main:app --reload --port 8000

    Expected startup logs:
    - "✓ MQTT broker reachable at localhost:1883"
    - "✓ MQTT ingester connected and subscribed"
    - "✓ MQTT publisher connected"

    In Mosquitto terminal: should show client connections from urbanpulse-ingester and urbanpulse-publisher
  </verify>
  <done>
    - publisher.py imports without error
    - uvicorn starts with broker online showing both ✓ ingester and ✓ publisher connected
    - app.state.queue, app.state.ingester, app.state.publisher all set in lifespan
    - Clean shutdown logs when Ctrl+C pressed
  </done>
</task>

</tasks>

<verification>
After all tasks (Mosquitto must be running):
- [ ] python -c "from mqtt.ingester import MQTTIngester; from mqtt.publisher import MQTTPublisher; print('OK')" exits 0
- [ ] uvicorn main:app startup logs show ingester + publisher connected
- [ ] Mosquitto terminal shows 2 client connections on startup
- [ ] Ctrl+C produces clean shutdown log (no traceback)
</verification>

<success_criteria>
- [ ] All verification checks pass
- [ ] No asyncio.run() inside paho callbacks (would deadlock)
- [ ] MQTTIngester thread is daemon=True (auto-cleaned on process exit)
</success_criteria>
