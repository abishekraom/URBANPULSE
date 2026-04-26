---
phase: 1
plan: 01
wave: 1
depends_on: []
files_modified:
  - backend/requirements.txt
  - backend/config.json
  - backend/mosquitto.conf
  - backend/mqtt/__init__.py
  - backend/core/__init__.py
  - backend/api/__init__.py
  - backend/ws/__init__.py
  - backend/db/__init__.py
  - backend/main.py
autonomous: true
user_setup:
  - service: mosquitto
    why: "MQTT broker — must be installed before backend starts"
    steps:
      - "Download: https://mosquitto.org/download/ (Windows installer)"
      - "Install to default path. Do NOT register as a Windows service."
      - "Launch manually: 'C:\\Program Files\\mosquitto\\mosquitto.exe' -c mosquitto.conf -v"
must_haves:
  truths:
    - "FastAPI server starts on http://localhost:8000 without errors"
    - "Startup checks Mosquitto reachability and prints clear error if broker is down"
    - "config.json is the single source of truth for all tunable values"
  artifacts:
    - "backend/main.py with FastAPI app + lifespan hook"
    - "backend/config.json with broker, topics, thresholds, health_score, heartbeat, api, mock keys"
    - "backend/mosquitto.conf with allow_anonymous true on port 1883"
    - "backend/requirements.txt with 4 pinned dependencies"
---

# Plan 1.01: Project Scaffold + Config + FastAPI Skeleton

<objective>
Create the complete backend directory structure, config files, and a runnable FastAPI app entry point.

Purpose: Foundation for every subsequent plan. Nothing can be built without this scaffold.
Output: backend/ directory, pip-installable, runnable with `uvicorn main:app`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md (MQTT Contract, Constraints)
- .gsd/RESEARCH.md (Dependencies section)
- .gsd/DECISIONS.md (ADR-001, Q1, Q4)
</context>

<tasks>

<task type="auto">
  <name>Create directory structure, requirements.txt, config.json, mosquitto.conf, __init__ stubs</name>
  <files>
    backend/requirements.txt
    backend/config.json
    backend/mosquitto.conf
    backend/mqtt/__init__.py
    backend/core/__init__.py
    backend/api/__init__.py
    backend/ws/__init__.py
    backend/db/__init__.py
  </files>
  <action>
    1. Create directory tree: backend/ with subdirs mqtt/, core/, api/, ws/, db/

    2. backend/requirements.txt (pinned — demo must be reproducible):
       fastapi==0.115.6
       uvicorn[standard]==0.32.1
       paho-mqtt==2.1.0
       aiofiles==24.1.0

    3. backend/config.json — full config with these top-level keys:
       broker: { host, port: 1883, keepalive: 60 }
       topics: { data_subscribe: "urbanpulse/node/+/data", heartbeat_subscribe: "urbanpulse/node/+/heartbeat", alert_publish: "urbanpulse/alerts" }
       thresholds: { mpu: { warning_peak_amp_g: 0.3, critical_peak_amp_g: 0.8 }, piezo: { warning_adc: 800, critical_adc: 2000 }, frequency_deviation_pct: 20 }
       health_score: { green_min: 70, amber_min: 40, mpu_warning_penalty: 30, mpu_critical_penalty: 60, piezo_warning_penalty: 30, piezo_critical_penalty: 60, freq_deviation_penalty: 10 }
       heartbeat: { publish_interval_s: 5, offline_timeout_s: 10 }
       api: { cors_origins: ["http://localhost:5173","http://localhost:3000"], default_data_limit: 50, default_history_minutes: 10, default_alert_limit: 20 }
       mock: { nodes: ["A","B","C"], publish_interval_s: 0.5, fault_duration_s: 10, fault_piezo_adc: 2500, fault_mpu_peak_amp_g: 1.2 }

    4. backend/mosquitto.conf:
       listener 1883 0.0.0.0
       allow_anonymous true
       log_type all
       connection_messages true

    5. Each __init__.py: single-line module docstring only. No logic.

    AVOID: any business logic in __init__.py files — stubs only.
    AVOID: unpinned requirements (demo must be reproducible).
  </action>
  <verify>
    From backend/: python -c "import json; c=json.load(open('config.json')); print(list(c.keys()))"
    Expected: ['broker', 'topics', 'thresholds', 'health_score', 'heartbeat', 'api', 'mock']
  </verify>
  <done>
    - 5 subdirs each with __init__.py
    - requirements.txt has 4 pinned deps
    - config.json is valid JSON with all 7 top-level keys
    - mosquitto.conf allows anonymous on 1883
  </done>
</task>

<task type="auto">
  <name>Create main.py — FastAPI app with lifespan broker check</name>
  <files>
    backend/main.py
  </files>
  <action>
    Create backend/main.py with:

    1. Config loader: reads config.json from same directory using pathlib.Path(__file__).parent

    2. Broker check function using socket.create_connection((host, port), timeout=2) — returns bool

    3. Lifespan context manager (@asynccontextmanager) that:
       - On startup: calls check_broker(), logs ✓ if reachable OR logs ✗ + exact launch command if not
       - Does NOT raise or exit on broker failure — backend starts regardless (graceful degradation)
       - On shutdown: logs "shutting down..."

    4. FastAPI app = FastAPI(title="UrbanPulse API", version="1.0.0", lifespan=lifespan)

    5. CORSMiddleware with allow_origins from config["api"]["cors_origins"], allow_methods=["*"]

    6. GET / endpoint returning: {"service": "UrbanPulse", "status": "running", "version": "1.0.0"}

    AVOID: @app.on_event("startup") — deprecated since FastAPI 0.93. Use lifespan= parameter.
    AVOID: importing mqtt/, db/, core/ modules — they don't exist yet.
    AVOID: hardcoded strings — read all values from config dict.
  </action>
  <verify>
    From backend/ (with or without Mosquitto running):
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
    curl http://localhost:8000/
    Expected: {"service":"UrbanPulse","status":"running","version":"1.0.0"}
    Also: http://localhost:8000/docs shows Swagger UI
  </verify>
  <done>
    - uvicorn starts without Python errors
    - GET / returns correct JSON
    - Swagger UI at /docs shows 1 endpoint
    - Startup log shows broker check (✓ or ✗ with instructions)
    - Broker being offline does NOT crash the server
  </done>
</task>

</tasks>

<verification>
After all tasks:
- [ ] python -c "import json; json.load(open('backend/config.json'))" exits 0
- [ ] uvicorn main:app starts without errors from backend/
- [ ] curl http://localhost:8000/ returns {"service":"UrbanPulse",...}
- [ ] /docs Swagger UI loads with 1 endpoint
- [ ] All 5 subdirs have __init__.py
</verification>

<success_criteria>
- [ ] All verification checks pass
- [ ] Backend starts even when Mosquitto is offline
- [ ] No hardcoded values in main.py — all from config.json
</success_criteria>
