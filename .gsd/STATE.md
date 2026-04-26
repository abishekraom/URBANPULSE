# STATE.md — UrbanPulse Project State

> **Last Updated**: 2026-04-26
> **Current Phase**: Pre-execution (project initialized)
> **Session**: #1

---

## Current Status

- [x] Project Bible read and understood (`urbanpulse_project_bible.html`)
- [x] AI/ML scope discarded per user decision
- [x] Backend research completed (see `RESEARCH.md`)
- [x] SPEC.md finalized
- [x] ROADMAP.md created (5 phases)
- [ ] Phase 1 execution not started

## Active Decisions

- **Language**: Python + FastAPI (async)
- **MQTT**: paho-mqtt in background thread, bridge to asyncio queue
- **Storage**: SQLite with WAL mode (no InfluxDB)
- **WebSocket**: BroadcastHub pattern (bounded per-client queues)
- **Severity**: Rule-based thresholds (no ML)
- **All offline**: No internet, no cloud

## Pending Discussion

- Confirm severity thresholds (MPU peak_amp and piezo peak_amp values)
- Confirm backend runs on Windows laptop (assumed yes)
- Confirm React dev server port (assumed 5173 for CORS config)

## Blockers

None currently.
