import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "tech_titans.db")

def get_db():
    """Generator dependency for FastAPI Depends()."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

@contextmanager
def db_conn():
    """Context manager for non-FastAPI usage (init_db, seeding, etc)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                victim_name TEXT NOT NULL,
                victim_phone TEXT DEFAULT '+91 98765 43210',
                victim_age INTEGER DEFAULT 45,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                location TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                complaint_type TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                predicted_lat REAL NOT NULL,
                predicted_lon REAL NOT NULL,
                probability REAL NOT NULL,
                risk_level TEXT NOT NULL,
                predicted_location TEXT NOT NULL,
                top3_json TEXT DEFAULT '[]',
                FOREIGN KEY (complaint_id) REFERENCES complaints(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                predicted_location TEXT NOT NULL,
                predicted_lat REAL NOT NULL,
                predicted_lon REAL NOT NULL,
                probability REAL NOT NULL,
                shap_explanation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                dispatch_status TEXT DEFAULT 'Pending',
                countdown_seconds INTEGER DEFAULT 1080,
                nearest_police_station TEXT DEFAULT 'Andheri Police Station',
                bank_notified INTEGER DEFAULT 1,
                assigned_constable TEXT DEFAULT 'Constable R. Shinde (PCR-14)',
                FOREIGN KEY (complaint_id) REFERENCES complaints(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hotspots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                intensity REAL NOT NULL,
                active_cases INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS retraining_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trained_at TEXT NOT NULL,
                dataset_size INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                precision_score REAL NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

        # Migrate missing columns if old DB exists
        def add_column_if_missing(table, col, col_def):
            cur.execute(f"PRAGMA table_info({table})")
            cols = [row["name"] for row in cur.fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                print(f"[DB MIGRATION] Added column {col} to table {table}")

        add_column_if_missing("complaints", "victim_phone", "TEXT DEFAULT '+91 98765 43210'")
        add_column_if_missing("complaints", "victim_age", "INTEGER DEFAULT 45")
        add_column_if_missing("predictions", "top3_json", "TEXT DEFAULT '[]'")
        add_column_if_missing("alerts", "dispatch_status", "TEXT DEFAULT 'Pending'")
        add_column_if_missing("alerts", "countdown_seconds", "INTEGER DEFAULT 1080")
        add_column_if_missing("alerts", "nearest_police_station", "TEXT DEFAULT 'Andheri Police Station'")
        add_column_if_missing("alerts", "bank_notified", "INTEGER DEFAULT 1")
        add_column_if_missing("alerts", "assigned_constable", "TEXT DEFAULT 'Constable R. Shinde (PCR-14)'")
