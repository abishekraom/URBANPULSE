---
phase: 1
plan: 03
wave: 3
depends_on: [1.01, 1.02]
files_modified:
  - backend/mock_publisher.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "mock_publisher.py --mode normal sends valid JSON packets for all 3 nodes every 500ms"
    - "mock_publisher.py --mode fault --node B sends a 10s CRITICAL burst then returns to normal"
    - "Running backend + mock_publisher together shows received messages in uvicorn logs"
    - "Packet structure exactly matches SPEC MQTT Contract (including raw_x/y/z and raw_adc)"
  artifacts:
    - "backend/mock_publisher.py with CLI args --mode and --node"
---

# Plan 1.03: Mock Publisher + Integration Smoke Test

<objective>
Build the mock MQTT publisher that simulates 3 ESP32 sensor nodes. This is the hardware replacement during development — everything in the pipeline can be tested without any physical device.

Purpose: Enables full end-to-end testing of backend (Phases 2–4) without waiting for ECE team's firmware.
Output: mock_publisher.py with two operational modes; smoke test confirms the full ingestion path works.
</objective>

<context>
Load for context:
- .gsd/SPEC.md (§ MQTT Contract — exact JSON payload structure including raw_x/y/z/raw_adc)
- backend/config.json (mock section: nodes, publish_interval_s, fault values)
- backend/mqtt/ingester.py (to understand what format the ingester expects)
</context>

<tasks>

<task type="auto">
  <name>Create mock_publisher.py with normal + fault simulation modes</name>
  <files>
    backend/mock_publisher.py
  </files>
  <action>
    Create backend/mock_publisher.py. This is a standalone script (not imported by main.py).

    CLI interface:
      python mock_publisher.py                        # normal mode, all 3 nodes
      python mock_publisher.py --mode fault --node B  # fault on node B for 10s then normal

    Implementation requirements:

    1. Parse args with argparse: --mode [normal|fault], --node [A|B|C], --host localhost, --port 1883

    2. Load config.json for mock settings (publish_interval_s, fault values, node list)

    3. Normal packet generator function — generates realistic but slightly randomized healthy data:
       - mpu: dom_freq between 8.0–15.0 Hz (random), peak_amp 0.01–0.08 g, spectral_centroid dom_freq * 1.4
       - mpu raw: raw_x 0.001–0.02 g, raw_y -0.01–0.01 g, raw_z 0.98–1.02 g (gravity component)
       - piezo: dom_freq 200–500 Hz (random), peak_amp 100–600 ADC, spectral_centroid dom_freq * 1.2
       - piezo raw_adc: 100–600 (12-bit, healthy range)
       Use random.uniform() for all ranges. Add small random jitter each packet.

    4. Fault packet generator — sends CRITICAL-level data:
       - mpu peak_amp: config["mock"]["fault_mpu_peak_amp_g"] = 1.2 g
       - piezo raw_adc: config["mock"]["fault_piezo_adc"] = 2500
       - dom_freq shifted 40% higher than normal (simulates resonance shift from loose joint)
       - raw_x: 0.8 g (strong lateral acceleration)

    5. Main publish loop:
       - Connect paho client (CallbackAPIVersion.VERSION2), loop_start()
       - For each node in config["mock"]["nodes"]:
         - Track whether node is in "fault" mode and fault timer
       - Every publish_interval_s:
         - For each node: determine if fault active, generate appropriate packet
         - Publish to "urbanpulse/node/{node_id}/data" with json.dumps(packet)
         - Also publish heartbeat to "urbanpulse/node/{node_id}/heartbeat" every 5s
         - Print to console: "→ Node {id} [{severity_hint}] piezo={adc} mpu={amp}g"
       - Fault mode: after fault_duration_s seconds, return node to normal, print "← Node B fault cleared"

    6. Graceful Ctrl+C handling (try/except KeyboardInterrupt, disconnect on exit)

    AVOID: using threading.sleep in the paho callback thread. Use time.sleep() in the main loop only.
    AVOID: importing anything from the backend package — this is a standalone script.
    AVOID: hardcoding any values — read everything from config.json.
    AVOID: sending fault data to all nodes simultaneously — only the --node argument gets faulted.
  </action>
  <verify>
    Terminal 1: uvicorn main:app --reload --port 8000  (from backend/)
    Terminal 2: python mock_publisher.py  (from backend/)

    Expected in Terminal 1 (uvicorn):
    - Messages appearing every ~500ms: "Received MQTT message on urbanpulse/node/A/data" (or similar log)

    Expected in Terminal 2 (mock_publisher):
    - "→ Node A [NORMAL] piezo=342 mpu=0.034g" lines appearing continuously

    Fault test:
    Terminal 2: python mock_publisher.py --mode fault --node B
    Expected: Normal for A and C, CRITICAL burst for B for 10s then back to normal
  </verify>
  <done>
    - mock_publisher.py runs with no args (normal mode, all nodes)
    - mock_publisher.py --mode fault --node B triggers 10s fault burst then auto-recovers
    - uvicorn logs show incoming MQTT messages from mock publisher
    - Packet structure matches SPEC exactly (all fields present including raw_x/y/z, raw_adc)
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Integration smoke test — confirm full message flow end-to-end</name>
  <files>
    (no files modified — verification only)
  </files>
  <action>
    Run this sequence and visually confirm each step:

    Step 1: Start Mosquitto
      mosquitto.exe -c mosquitto.conf -v
      (from backend/ directory or full path)

    Step 2: Start backend
      uvicorn main:app --reload --port 8000
      Confirm: "✓ MQTT ingester connected" in logs

    Step 3: Start mock publisher (normal mode)
      python mock_publisher.py
      Confirm: Console shows Node A/B/C packets every 500ms

    Step 4: Watch uvicorn logs
      Confirm: Messages from mock publisher appear in backend logs

    Step 5: Test fault simulation
      Ctrl+C mock_publisher, restart with: python mock_publisher.py --mode fault --node B
      Confirm: Node B shows CRITICAL values for ~10s, then returns to normal in console

    Step 6: Verify API endpoint
      curl http://localhost:8000/
      Confirm: {"service":"UrbanPulse","status":"running","version":"1.0.0"}
  </action>
  <verify>
    All 6 steps complete without errors.
    Phase 1 is DONE when mock publisher packets visibly flow through to backend logs.
  </verify>
  <done>
    - Mosquitto running with 2 connections (ingester + publisher) + mock publisher = 3 connections total
    - uvicorn logs confirm message receipt from all 3 nodes
    - Fault simulation visually confirmed in mock_publisher console
    - GET / returns 200
  </done>
</task>

</tasks>

<verification>
After all tasks:
- [ ] python mock_publisher.py runs without errors and prints packets for A, B, C
- [ ] uvicorn logs show MQTT messages being received when mock_publisher runs
- [ ] python mock_publisher.py --mode fault --node B shows CRITICAL burst for 10s
- [ ] GET http://localhost:8000/ returns 200 with correct JSON
- [ ] Ctrl+C on all processes produces clean shutdown (no tracebacks)
</verification>

<success_criteria>
- [ ] All verification checks pass
- [ ] Phase 1 objective met: backend + mock publisher work together without any ESP32 hardware
- [ ] Ready for Phase 2 (storage + processing pipeline)
</success_criteria>
