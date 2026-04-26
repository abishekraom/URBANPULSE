---
phase: 2
plan: 01
wave: 1
depends_on: []
files_modified:
  - backend/db/connection.py
  - backend/db/queries.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "SQLite is configured with WAL mode and synchronous=NORMAL"
    - "Schema includes readings, alerts, and nodes tables"
    - "Query functions use context managers or clean transaction boundaries"
  artifacts:
    - "backend/db/connection.py"
    - "backend/db/queries.py"
---

# Plan 2.01: Database Layer (SQLite)

<objective>
Implement the storage layer using SQLite. Must be fast enough for high-frequency inserts without locking the async loop. WAL mode is required.
Output: DB connection manager and query functions for inserting readings, alerts, and upserting node state.
</objective>

<context>
- .gsd/SPEC.md
- backend/config.json
</context>

<tasks>

<task type="auto">
  <name>Create db/connection.py with WAL mode</name>
  <files>
    backend/db/connection.py
  </files>
  <action>
    Create backend/db/connection.py.
    1. Import sqlite3, logging, contextlib.
    2. Define DB path (backend/urbanpulse.db).
    3. Define setup_db(): creates tables if not exist.
       - nodes: node_id (PK), state (TEXT), last_seen (INTEGER), last_health_score (INTEGER)
       - readings: id (INTEGER PK), node_id (TEXT), ts (INTEGER), health_score (INTEGER), severity (TEXT), payload_json (TEXT)
       - alerts: id (INTEGER PK), node_id (TEXT), severity (TEXT), reason (TEXT), ts (INTEGER)
    4. Provide get_db() contextmanager that yields a connection, sets PRAGMA journal_mode=WAL and PRAGMA synchronous=NORMAL, and commits on exit.
    
    AVOID: Async sqlite wrapper for now; standard sqlite3 is fine if we offload queries or use fast WAL inserts.
  </action>
  <verify>
    python -c "from db.connection import setup_db; setup_db(); print('OK')"
  </verify>
  <done>
    - DB file created successfully.
    - WAL mode is active.
    - Tables exist.
  </done>
</task>

<task type="auto">
  <name>Create db/queries.py</name>
  <files>
    backend/db/queries.py
  </files>
  <action>
    Create backend/db/queries.py.
    Implement these functions using get_db():
    1. upsert_node(node_id: str, state: str, last_seen: int, health_score: int)
    2. insert_reading(node_id: str, ts: int, health_score: int, severity: str, payload: dict) -> saves json.dumps(payload)
    3. insert_alert(node_id: str, severity: str, reason: str, ts: int)
    4. get_nodes() -> list of dicts
    5. get_history(node_id: str, minutes: int) -> list of (ts, health_score)

    AVOID: Keeping connections open globally. Use the get_db() contextmanager per operation.
  </action>
  <verify>
    python -c "from db.queries import upsert_node; upsert_node('A', 'NORMAL', 123, 100); print('OK')"
  </verify>
  <done>
    - All 5 functions implemented.
    - Queries execute without syntax errors.
  </done>
</task>

</tasks>

<success_criteria>
- [ ] urbanpulse.db is created with 3 tables
- [ ] WAL mode is active
- [ ] CRUD functions work correctly
</success_criteria>