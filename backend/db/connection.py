import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("urbanpulse.db")

DB_PATH = Path(__file__).parent.parent / "urbanpulse.db"

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
        
        # Optional: Add indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_node_ts ON readings (node_id, ts)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts (ts)")
        
        logger.info("Database setup complete.")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    # Enable dict-like row access
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
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
