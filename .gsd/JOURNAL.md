# JOURNAL.md — Project Journal

---

## 2026-04-26 — Session 1: Project Initialization

- Read and parsed full `urbanpulse_project_bible.html`
- Key scope change: ALL AI/ML features (Isolation Forest, LSTM autoencoder, anomaly scoring, baseline collection) discarded per user decision
- Severity classification replaced with rule-based thresholds
- Backend research conducted:
  - FastAPI selected over Flask/Node.js
  - Mosquitto for MQTT broker
  - SQLite WAL for storage
  - paho-mqtt thread-bridge for async integration
  - BroadcastHub pattern for WebSocket
- SPEC.md, RESEARCH.md, ROADMAP.md, STATE.md, DECISIONS.md all initialized
- Awaiting user discussion before Phase 1 execution begins
