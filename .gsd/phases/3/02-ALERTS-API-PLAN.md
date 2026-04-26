---
phase: 3
plan: 02
wave: 1
depends_on: []
files_modified:
  - backend/api/routers/alerts.py
  - backend/db/queries.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "/api/alerts returns recent alerts"
    - "/api/alerts/export returns StreamingResponse CSV"
  artifacts:
    - "backend/api/routers/alerts.py"
---

# Plan 3.02: Alerts REST API

<objective>
Implement the REST endpoints for fetching recent alerts and exporting the full alert log as a CSV file.
</objective>

<context>
- .gsd/SPEC.md (§ REST API Surface)
- backend/db/queries.py
</context>

<tasks>

<task type="auto">
  <name>Implement Alerts Router</name>
  <files>
    backend/api/routers/alerts.py
    backend/db/queries.py
  </files>
  <action>
    1. In `backend/db/queries.py`, add `get_alerts(limit: int = 20)` and `get_all_alerts()` if missing.
    2. Create `backend/api/routers/alerts.py` with APIRouter prefix="/api/alerts".
    3. GET `/`: Return `get_alerts(limit)` from DB.
    4. GET `/export`: Fetch all alerts, generate CSV rows using Python's `csv` module, and yield them via FastAPI `StreamingResponse` (media_type="text/csv"). Set Content-Disposition header to "attachment; filename=alerts.csv".
  </action>
  <verify>
    python -c "from api.routers.alerts import router; print('OK')"
  </verify>
  <done>
    - Router module loads successfully.
    - Export endpoint correctly yields CSV data.
  </done>
</task>

</tasks>

<success_criteria>
- [ ] Router module compiles.
- [ ] Export streams CSV appropriately.
</success_criteria>
