import os
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("urbanpulse.db")

DB_PATH = Path(os.environ.get("URBANPULSE_DB_PATH", Path(__file__).parent.parent / "urbanpulse.db"))

def setup_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # Create nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                state TEXT,
                last_seen INTEGER,
                last_health_score INTEGER
            )
        """)

        # Create readings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                ts INTEGER,
                health_score INTEGER,
                severity TEXT,
                payload_json TEXT
            )
        """)

        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                severity TEXT,
                reason TEXT,
                ts INTEGER
            )
        """)

        # Indexes for fast time-range queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_node_ts ON readings (node_id, ts)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings (ts)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts (ts)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_node_ts ON alerts (node_id, ts)")

        logger.info("Database setup complete.")

        # Purge stale readings on startup
        try:
            from db.queries import purge_old_readings
            deleted = purge_old_readings()
            if deleted:
                logger.info("Purged %d stale readings from database", deleted)
        except Exception:
            pass

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    # Enable dict-like row access
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        # Increase cache size for better read performance
        conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

# Run setup when imported to ensure it's ready
setup_db()
