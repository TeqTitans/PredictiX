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
