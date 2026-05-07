"""
Audit trail database — logs every AI interaction for review and ROI tracking.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", "ceo_agent.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                skill_id TEXT,
                input_summary TEXT,
                output TEXT,
                tokens_used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_key TEXT UNIQUE,
                metric_value INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC)
        """)


def log_interaction(session_id: str, skill_id: str, user_input: str, output: str):
    input_summary = user_input[:300]
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (session_id, skill_id, input_summary, output) VALUES (?, ?, ?, ?)",
            (session_id, skill_id, input_summary, output),
        )
        conn.execute("""
            INSERT INTO metrics (metric_key, metric_value, updated_at)
            VALUES (?, 1, datetime('now'))
            ON CONFLICT(metric_key) DO UPDATE SET
                metric_value = metric_value + 1,
                updated_at = datetime('now')
        """, (f"count_{skill_id}",))
        conn.execute("""
            INSERT INTO metrics (metric_key, metric_value, updated_at)
            VALUES ('total_interactions', 1, datetime('now'))
            ON CONFLICT(metric_key) DO UPDATE SET
                metric_value = metric_value + 1,
                updated_at = datetime('now')
        """)


def get_audit_log(limit: int = 50, skill_id: str = None) -> list[dict]:
    with _conn() as conn:
        if skill_id:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE skill_id = ? ORDER BY created_at DESC LIMIT ?",
                (skill_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_metrics() -> dict:
    with _conn() as conn:
        rows = conn.execute("SELECT metric_key, metric_value FROM metrics").fetchall()
    return {r["metric_key"]: r["metric_value"] for r in rows}


def get_audit_entry(entry_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM audit_log WHERE id = ?", (entry_id,)).fetchone()
    return dict(row) if row else None
