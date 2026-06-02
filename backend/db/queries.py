import json
import time
from typing import List, Tuple, Dict
from db.connection import get_db

RETENTION_HOURS = 1  # readings older than this are purged on startup

def upsert_node(node_id: str, state: str, last_seen: int, health_score: int):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO nodes (node_id, state, last_seen, last_health_score)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                state=excluded.state,
                last_seen=excluded.last_seen,
                last_health_score=excluded.last_health_score
        """, (node_id, state, last_seen, health_score))

def insert_reading(node_id: str, ts: int, health_score: int, severity: str, payload: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO readings (node_id, ts, health_score, severity, payload_json)
            VALUES (?, ?, ?, ?, ?)
        """, (node_id, ts, health_score, severity, json.dumps(payload)))

def insert_alert(node_id: str, severity: str, reason: str, ts: int):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO alerts (node_id, severity, reason, ts)
            VALUES (?, ?, ?, ?)
        """, (node_id, severity, reason, ts))

def get_nodes() -> List[dict]:
    with get_db() as conn:
        cursor = conn.execute("SELECT node_id, state, last_seen, last_health_score FROM nodes")
        return [dict(row) for row in cursor.fetchall()]

def get_history(node_id: str, minutes: int = 10, max_points: int = 200) -> List[Tuple[int, int]]:
    """Return health score history for a node.

    Uses time-based filtering when ts stores epoch ms (HTTP path / mock publisher).
    Falls back to count-based (latest N readings) when time-based returns nothing
    (e.g. firmware millis() values that don't overlap with real time).

    The returned list is sorted chronologically (oldest first).
    """
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - (minutes * 60 * 1000)

    with get_db() as conn:
        # Try time-based filter first (epoch-millis path)
        cursor = conn.execute("""
            SELECT ts, health_score
            FROM readings
            WHERE node_id = ? AND ts >= ?
            ORDER BY ts DESC
            LIMIT ?
        """, (node_id, cutoff_ms, max_points))

        rows = [dict(row) for row in cursor.fetchall()]

        # If time-based returned nothing, the ts values might be firmware millis()
        # that are small and unrelated to epoch. Fall back to count-based.
        if not rows:
            cursor = conn.execute("""
                SELECT ts, health_score
                FROM readings
                WHERE node_id = ?
                ORDER BY ts DESC
                LIMIT ?
            """, (node_id, max_points))
            rows = [dict(row) for row in cursor.fetchall()]

        result = [(row["ts"], row["health_score"]) for row in rows]
        result.reverse()  # oldest first
        return result

def get_recent_readings(node_id: str, limit: int) -> List[dict]:
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, node_id, ts, health_score, severity, payload_json
            FROM readings
            WHERE node_id = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (node_id, limit))

        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            try:
                row_dict["payload"] = json.loads(row_dict.pop("payload_json"))
            except (json.JSONDecodeError, TypeError):
                row_dict["payload"] = {}
            results.append(row_dict)
        return results

def get_alerts(limit: int) -> List[dict]:
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, node_id, severity, reason, ts
            FROM alerts
            ORDER BY ts DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_all_alerts() -> List[dict]:
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, node_id, severity, reason, ts
            FROM alerts
            ORDER BY ts DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def purge_old_readings(hours: int = RETENTION_HOURS):
    """Delete readings older than `hours` hours to prevent unbounded SQLite growth."""
    cutoff_ms = int(time.time() * 1000) - (hours * 3600 * 1000)
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM readings WHERE ts < ? AND ts > 1000000000000", (cutoff_ms,))
        # The ts > 1e12 guard prevents deleting firmware-millis rows (which are small numbers)
        deleted = cursor.rowcount
        if deleted:
            conn.execute("PRAGMA optimize")
        return deleted
