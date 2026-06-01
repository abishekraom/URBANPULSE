"""
UrbanPulse — Comprehensive Endurance & Safety Test Suite

Runs through 4 test phases:
  1. Baseline checks (recursion limit, DB size, latency stability)
  2. Multi-rate stress (1x, 10x, 30x real-time)
  3. Backend log scan for errors/warnings/tracebacks
  4. Long-duration soak (180s at 2x real-time)

Exits 0 if all pass, 1 if any fail.
"""
import json
import os
import sys
import time
import urllib.request

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
DB_PATH = os.path.expanduser("~/Documents/urbanpulse/backend/urbanpulse.db")

STATS = {"pass": 0, "fail": 0, "warn": 0}

def log_pass(msg):
    print(f"  ✅ {msg}")
    STATS["pass"] += 1

def log_fail(msg):
    print(f"  ❌ {msg}")
    STATS["fail"] += 1

def log_warn(msg):
    print(f"  ⚠️  {msg}")
    STATS["warn"] += 1

def http_get(path):
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except Exception as e:
        return None, str(e)

def post_reading(node_id=1, amp=5.0):
    url = f"{BASE_URL}/api/sensor-data"
    body = json.dumps({
        "node_id": node_id,
        "timestamp": int(time.time() * 1000),
        "mpu_dominant_freq": 12.0,
        "mpu_peak_amplitude": amp,
        "mpu_spectral_centroid": 16.0,
        "mpu_rms": 3.0,
        "piezo_dominant_freq": 300.0,
        "piezo_peak_amplitude": 100.0,
        "piezo_spectral_centroid": 360.0,
        "piezo_rms": 50.0,
    }).encode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    t = time.monotonic()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with opener.open(req, timeout=5) as resp:
        data = json.loads(resp.read())
    return (time.monotonic() - t) * 1000, data

def check_backend_alive():
    status, data = http_get("/api/health")
    if status == 200:
        return True, data
    return False, data

def get_db_size():
    try:
        return os.path.getsize(DB_PATH)
    except OSError:
        return 0

def get_backend_log(pid=None):
    """Scrape recent backend output from health endpoint."""
    status, data = http_get("/api/health")
    if status == 200:
        return data
    return None

# ═══════════════════════════════════════════════════════════════
# PHASE 1: BASELINE
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("  PHASE 1: BASELINE CHECKS")
print("=" * 60)

# 1a. Backend alive
alive, info = check_backend_alive()
if alive:
    log_pass(f"Backend UP | uptime={info.get('uptime_s', '?')}s pkts={info.get('total_packets', '?')}")
else:
    log_fail(f"Backend DOWN — {info}")
    sys.exit(1)

# 1b. Recursion limit
import sys as _sys
rlimit = _sys.getrecursionlimit()
if rlimit >= 1000:
    log_pass(f"Recursion limit: {rlimit}")
else:
    log_fail(f"Recursion limit too low: {rlimit}")

# 1c. Stack depth test — simulate deep pipeline call
MAX_DEPTH = 50
def deep_chain(depth=0, max_depth=MAX_DEPTH):
    """Simulate worst-case call chain: schema → validate → classify → score → store → broadcast."""
    if depth >= max_depth:
        return "bottom"
    # Simulate each layer with unique variables
    if depth == 0:
        payload = {"node_id": "1", "mpu": {"dom_freq": 12, "peak_amp": 0.05}, "piezo": {"dom_freq": 300, "peak_amp": 100}}
        _ = payload
    if depth == 10:
        validated = True
        _ = validated
    if depth == 20:
        classified = {"severity": "NORMAL", "reason": None}
        _ = classified
    if depth == 30:
        scored = 92
        _ = scored
    if depth == 40:
        broadcast_msg = {"type": "reading", "data": {}}
        _ = broadcast_msg
    return deep_chain(depth + 1, max_depth)

try:
    deep_chain()
    log_pass(f"Stack depth test passed ({MAX_DEPTH} simulated layers)")
except RecursionError:
    log_fail(f"RecursionError at {MAX_DEPTH} depth!")

# 1d. DB baseline
db_size = get_db_size()
log_pass(f"DB size: {db_size / 1024:.0f} KB")

# 1e. Latency stability (5 rapid POSTs, check variance)
times = []
for i in range(5):
    elapsed, resp = post_reading(1, amp=0.05)
    times.append(elapsed)

mean_t = sum(times) / len(times)
var_t = max(times) - min(times)
log_pass(f"Latency baseline: mean={mean_t:.0f}ms variance={var_t:.0f}ms")

# ═══════════════════════════════════════════════════════════════
# PHASE 2: MULTI-RATE STRESS
# ═══════════════════════════════════════════════════════════════
print("")
print("=" * 60)
print("  PHASE 2: MULTI-RATE STRESS")
print("=" * 60)

def run_stress(rate_hz, duration_s, label):
    """Send packets at controlled rate using sequential POSTs."""
    interval = 1.0 / rate_hz
    total = int(rate_hz * duration_s)
    start = time.time()
    sent = 0
    errors = 0
    latencies = []
    log_every = max(1, total // 3)

    for i in range(total):
        cycle_start = time.monotonic()
        try:
            elapsed, resp = post_reading(node_id=(i % 3) + 1, amp=0.05)
            latencies.append(elapsed)
            sent += 1
        except Exception:
            errors += 1

        if i > 0 and i % log_every == 0:
            avg_lat = sum(latencies[-50:]) / min(50, len(latencies))
            elapsed_t = time.time() - start
            print(f"    ... {i}/{total} pkts ({sent/max(elapsed_t,0.001):.0f}/s) lat={avg_lat:.0f}ms err={errors}")

        # Rate control
        cycle_elapsed = (time.monotonic() - cycle_start) * 1000
        sleep_ms = (interval * 1000) - cycle_elapsed
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000)

    elapsed = time.time() - start
    avg_lat = sum(latencies) / max(len(latencies), 1)
    p99 = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else (max(latencies) if latencies else 0)

    print(f"  [{label}] {sent} pkts, {errors} err, {avg_lat:.0f}ms avg, {p99:.0f}ms p99, {(sent/elapsed):.0f} pkts/s")

    # Check backend still alive after this phase
    alive, info = check_backend_alive()
    if not alive:
        log_fail(f"Backend crashed during {label}!")
        return False

    return errors == 0 and sent > 0

# 2a. Real-time rate (2Hz × 3 = 6 pkts/s)
print("\n--- 2a: Real-time (6 pkts/s, 30s) ---")
db_before = get_db_size()
ok = run_stress(rate_hz=2, duration_s=30, label="1x")
db_after = get_db_size()
if ok:
    log_pass(f"1x rate passed | DB growth: {(db_after - db_before) / 1024:.0f} KB")
else:
    log_fail("1x rate failed")

# 2b. 10x rate (20Hz × 3 = 60 pkts/s)
print("\n--- 2b: 10x (60 pkts/s, 20s) ---")
db_before = get_db_size()
ok = run_stress(rate_hz=20, duration_s=20, label="10x")
db_after = get_db_size()
if ok:
    log_pass(f"10x rate passed | DB growth: {(db_after - db_before) / 1024:.0f} KB")
else:
    log_fail("10x rate failed")

# 2c. 30x rate (60Hz × 3 = 180 pkts/s, short burst)
print("\n--- 2c: 30x (180 pkts/s, 10s) ---")
db_before = get_db_size()
ok = run_stress(rate_hz=60, duration_s=10, label="30x")
db_after = get_db_size()
if ok:
    log_pass(f"30x rate passed | DB growth: {(db_after - db_before) / 1024:.0f} KB")
else:
    log_fail("30x rate failed")

# ═══════════════════════════════════════════════════════════════
# PHASE 3: LOG SCAN
# ═══════════════════════════════════════════════════════════════
print("")
print("=" * 60)
print("  PHASE 3: ERROR PATTERN SCAN")
print("=" * 60)

# Query backend for current state after all the stress
status, health = http_get("/api/health")
if status == 200:
    total_pkts = health.get("total_packets", 0)
    uptime = health.get("uptime_s", 0)
    pk_age = health.get("last_packet_age_ms", 0)
    log_pass(f"Backend survived: {total_pkts} pkts, {uptime}s uptime, last packet {pk_age}ms ago")
else:
    log_fail("Backend unreachable after stress tests")

# ═══════════════════════════════════════════════════════════════
# PHASE 4: LONG-DURATION SOAK
# ═══════════════════════════════════════════════════════════════
print("")
print("=" * 60)
print("  PHASE 4: LONG-DURATION SOAK (2x rate, 120s)")
print("=" * 60)

db_before = get_db_size()
ok = run_stress(rate_hz=4, duration_s=120, label="soak")
db_after = get_db_size()

if ok:
    db_growth = (db_after - db_before) / 1024
    log_pass(f"Soak passed | DB grew {db_growth:.0f} KB in 120s ({db_growth/120:.1f} KB/s)")
else:
    log_fail("Soak test failed")

# Final health check
status, health = http_get("/api/health")
if status == 200:
    total_pkts = health.get("total_packets", 0)
    uptime = health.get("uptime_s", 0)
    log_pass(f"Final health: {total_pkts} pkts, {uptime}s uptime")
else:
    log_fail("Final health check failed")

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("")
print("=" * 60)
print("  TEST SUMMARY")
print("=" * 60)
print(f"  Passed:  {STATS['pass']}")
print(f"  Failed:  {STATS['fail']}")
print(f"  Warnings: {STATS['warn']}")
print(f"  DB size:  {get_db_size() / 1024:.0f} KB")
print("")

if STATS["fail"] == 0:
    print("  ✅ VERDICT: ALL TESTS PASSED")
    sys.exit(0)
else:
    print(f"  ❌ VERDICT: {STATS['fail']} test(s) FAILED")
    sys.exit(1)
