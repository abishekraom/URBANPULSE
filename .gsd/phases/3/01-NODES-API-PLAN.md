---
phase: 3
plan: 01
wave: 1
depends_on: []
files_modified:
  - backend/api/routers/nodes.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "/api/nodes returns array of node statuses"
    - "/api/nodes/{id}/data supports limit param and returns reading payloads"
    - "/api/nodes/{id}/history supports minutes param and returns time-series score trend"
  artifacts:
    - "backend/api/routers/nodes.py"
---

# Plan 3.01: Nodes REST API

<objective>
Implement the REST endpoints for retrieving node state, sensor data, and health history. These endpoints feed the frontend Node List and Chart widgets.
</objective>

<context>
- .gsd/SPEC.md (§ REST API Surface)
- backend/db/queries.py
</context>

<tasks>

<task type="auto">
  <name>Implement Nodes Router</name>
  <files>
    backend/api/routers/nodes.py
  </files>
  <action>
    Create backend/api/routers/nodes.py.
    Implement an APIRouter with prefix="/api/nodes".
    
    1. GET `/`: Return `get_nodes()` from DB.
    2. GET `/{id}/data`: Fetch last N readings from `readings` table where node_id=id. Limit defaults to config (or 50). Need to parse payload_json back to dict.
    3. GET `/{id}/history`: Fetch history using `get_history(node_id, minutes)` from DB. Return list of {"ts": ts, "score": score}.
    
    Note: You may need to add a `get_recent_readings(node_id, limit)` to `db/queries.py` if it doesn't exist.
  </action>
  <verify>
    python -c "from api.routers.nodes import router; print('OK')"
  </verify>
  <done>
    - Router module loads successfully.
    - Endpoints match SPEC.md.
  </done>
</task>

</tasks>

<success_criteria>
- [ ] Router module compiles.
- [ ] Endpoints fetch data appropriately from SQLite.
</success_criteria>
