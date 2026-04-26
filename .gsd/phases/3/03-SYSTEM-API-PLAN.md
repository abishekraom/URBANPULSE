---
phase: 3
plan: 03
wave: 2
depends_on: [3.01, 3.02]
files_modified:
  - backend/api/routers/system.py
  - backend/main.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "/api/health returns uptime and packet metrics"
    - "/api/config/thresholds returns thresholds from config"
    - "main.py includes all routers"
  artifacts:
    - "backend/api/routers/system.py"
    - "backend/main.py"
---

# Plan 3.03: System API & App Wiring

<objective>
Implement system-level endpoints (health, config) and wire all REST API routers into the main FastAPI application.
</objective>

<context>
- .gsd/SPEC.md (§ REST API Surface)
- backend/main.py
</context>

<tasks>

<task type="auto">
  <name>Implement System Router</name>
  <files>
    backend/api/routers/system.py
  </files>
  <action>
    Create backend/api/routers/system.py.
    Implement APIRouter without prefix, but define the paths explicitly.
    1. GET `/api/health`: Return basic system metrics. (For now, just return uptime_s by calculating time since start, and maybe placeholders for packet metrics if not easily accessible).
    2. GET `/api/config/thresholds`: Read app.state.config["thresholds"] and return it. (You can access config via Request.app.state.config).
  </action>
  <verify>
    python -c "from api.routers.system import router; print('OK')"
  </verify>
  <done>
    - System endpoints map accurately to config state.
  </done>
</task>

<task type="auto">
  <name>Wire Routers to FastAPI</name>
  <files>
    backend/main.py
  </files>
  <action>
    Update backend/main.py to import the three routers (`nodes.router`, `alerts.router`, `system.router`).
    Use `app.include_router(...)` to attach them to the FastAPI app.
  </action>
  <verify>
    python -c "import main; print('OK')"
  </verify>
  <done>
    - App mounts all routers without errors.
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Verify REST Endpoints</name>
  <files></files>
  <action>
    Start uvicorn, run mock_publisher, and hit `http://localhost:8000/api/nodes` and `/api/alerts` using curl or a browser.
  </action>
  <verify>
    Endpoints return JSON matching the expected spec.
  </verify>
  <done>
    - Endpoints confirmed functional by human testing.
  </done>
</task>

</tasks>

<success_criteria>
- [ ] All three routers are active in `main.py`.
- [ ] The REST API surface matches `SPEC.md` exactly.
</success_criteria>
