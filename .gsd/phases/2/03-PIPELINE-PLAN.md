---
phase: 2
plan: 03
wave: 2
depends_on: [2.01, 2.02]
files_modified:
  - backend/core/heartbeat.py
  - backend/core/pipeline.py
  - backend/main.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "Pipeline pulls from queue and processes MQTT messages"
    - "Heartbeat task detects offline nodes and updates DB"
    - "Alerts are published back to MQTT if WARNING/CRITICAL"
  artifacts:
    - "backend/core/heartbeat.py"
    - "backend/core/pipeline.py"
    - "backend/main.py updated to start pipeline and heartbeat"
---

# Plan 2.03: Processing Pipeline & Heartbeat Monitor

<objective>
Wire up the central processing loop that consumes the MQTT asyncio.Queue, evaluates packets, stores data, and publishes alerts. Implement the background heartbeat monitor to flag offline nodes.
Output: Fully operational backend data path, observable via DB entries and alert publications.
</objective>

<context>
- .gsd/SPEC.md
- backend/main.py (lifespan manager)
</context>

<tasks>

<task type="auto">
  <name>Create core/heartbeat.py</name>
  <files>
    backend/core/heartbeat.py
  </files>
  <action>
    Create backend/core/heartbeat.py.
    Implement async heartbeat_monitor(app_state):
    1. Loop continuously using asyncio.sleep(5)
    2. Check DB nodes table (get_nodes()).
    3. If current_time - last_seen > config["heartbeat"]["offline_timeout_s"] AND state is not OFFLINE:
       - Update state to OFFLINE in DB
       - (Later phases will broadcast this to WebSocket)
  </action>
  <verify>
    python -c "import core.heartbeat; print('OK')"
  </verify>
  <done>
    - Loop logic is correct.
    - Sleep prevents CPU spin.
  </done>
</task>

<task type="auto">
  <name>Create core/pipeline.py and wire up main.py</name>
  <files>
    backend/core/pipeline.py
    backend/main.py
  </files>
  <action>
    1. Create backend/core/pipeline.py:
       Implement async process_queue(app_state).
       - In a while True loop, get event from app_state.queue.
       - If topic ends with '/data':
           - Classify payload using classify_reading
           - Compute health_score using compute_health_score
           - Store reading using insert_reading
           - Upsert node state
           - If severity is WARNING or CRITICAL, store alert (insert_alert) AND publish alert using app_state.publisher.publish_alert()
       - If topic ends with '/heartbeat':
           - Upsert node state (mark as ONLINE, update last_seen)
    
    2. Update backend/main.py lifespan to use asyncio.create_task() for both process_queue and heartbeat_monitor at startup (only if broker_ok is True). Cancel tasks on shutdown.
  </action>
  <verify>
    uvicorn main:app --reload --port 8000
    (With Mosquitto and mock_publisher.py running)
  </verify>
  <done>
    - No queue deadlocks.
    - DB populates with data from mock_publisher.
    - Fault mode in mock_publisher triggers DB alert and MQTT alert publish.
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Verify Data Flow</name>
  <files></files>
  <action>
    Start mosquitto, backend (uvicorn), and mock_publisher in fault mode.
    Confirm urbanpulse.db is populated with readings and alerts.
    Check uvicorn console to see if "Alert published" log appears when fault occurs.
  </action>
  <verify>
    SQL inspection shows data in readings and alerts tables.
  </verify>
  <done>
    - SQLite DB correctly contains processed data.
  </done>
</task>

</tasks>

<success_criteria>
- [ ] Database contains real time-series data from mock publisher.
- [ ] Alerts trigger correctly and are stored and broadcast.
- [ ] Heartbeat system properly marks dead nodes offline.
</success_criteria>