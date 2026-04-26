---
phase: 2
plan: 02
wave: 1
depends_on: []
files_modified:
  - backend/core/health_score.py
  - backend/core/classifier.py
autonomous: true
user_setup: []
must_haves:
  truths:
    - "health_score correctly maps MPU and Piezo readings to 0-100 according to config"
    - "classifier correctly maps readings to NORMAL, WARNING, CRITICAL"
    - "Config values are dynamically passed in, not hardcoded"
  artifacts:
    - "backend/core/health_score.py"
    - "backend/core/classifier.py"
---

# Plan 2.02: Core Health Scoring & Classification

<objective>
Implement the rule-based logic that computes the 0-100 health score and severity class (NORMAL, WARNING, CRITICAL) for incoming sensor packets based on configured thresholds.
Output: Pure functions evaluating MQTT payloads against thresholds.
</objective>

<context>
- .gsd/SPEC.md (§ Health Score Algorithm)
- backend/config.json
</context>

<tasks>

<task type="auto">
  <name>Create core/health_score.py</name>
  <files>
    backend/core/health_score.py
  </files>
  <action>
    Create backend/core/health_score.py.
    Implement compute_health_score(payload: dict, config: dict, baseline_freq: float = None) -> int.
    1. Start with score = 100
    2. Subtract penalty based on MPU peak_amp thresholds (config["thresholds"]["mpu"]) and penalty values (config["health_score"]).
    3. Subtract penalty based on Piezo raw_adc or peak_amp thresholds (config["thresholds"]["piezo"]) and penalties.
    4. If baseline_freq is provided, check if MPU dom_freq deviates by > config["thresholds"]["frequency_deviation_pct"] %. If so, subtract freq_deviation_penalty.
    5. Return max(0, score).

    AVOID: Hardcoding thresholds.
  </action>
  <verify>
    python -c "from core.health_score import compute_health_score; print('OK')"
  </verify>
  <done>
    - Logic returns integer 0-100.
    - All penalties applied appropriately.
  </done>
</task>

<task type="auto">
  <name>Create core/classifier.py</name>
  <files>
    backend/core/classifier.py
  </files>
  <action>
    Create backend/core/classifier.py.
    Implement classify_reading(payload: dict, config: dict) -> (str, str | None).
    Returns a tuple: (severity, reason). Severity is one of "NORMAL", "WARNING", "CRITICAL".
    Reason is a string explaining the trigger (e.g. "mpu_peak_amp_critical") or None if NORMAL.
    1. Check MPU and Piezo values against Critical thresholds first. If any exceed, return CRITICAL + reason.
    2. Check Warning thresholds next. If any exceed, return WARNING + reason.
    3. Otherwise return "NORMAL", None.
  </action>
  <verify>
    python -c "from core.classifier import classify_reading; print('OK')"
  </verify>
  <done>
    - Evaluates correctly in cascade (Critical > Warning > Normal).
    - Returns descriptive reason.
  </done>
</task>

</tasks>

<success_criteria>
- [ ] Both modules load and compile.
- [ ] Logic maps exactly to SPEC defaults without hardcoding them in Python.
</success_criteria>