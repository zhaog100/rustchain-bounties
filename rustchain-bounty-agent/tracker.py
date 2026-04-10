"""SQLite-based earnings and task tracker."""

import json
import sqlite3
import time
import logging
from pathlib import Path

log = logging.getLogger("tracker")

RTC_TO_USD = 0.10


class Tracker:
    def __init__(self, cfg, db_path: str = "bounty_tracker.db"):
        self.cfg = cfg
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    issue_number INTEGER PRIMARY KEY,
                    title TEXT,
                    repo TEXT,
                    score REAL,
                    amount_rtc REAL DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    pr_url TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)

    def add_task(self, issue: dict, score: dict):
        """Add a new task to track."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (issue_number, title, repo, score, amount_rtc, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
                (issue["number"], issue["title"], self.cfg.target_repo, score["total"], score["amount"], time.time(), time.time())
            )
        log.info("Tracked task #%d", issue["number"])

    def get_pending_tasks(self) -> list[dict]:
        """Get pending tasks sorted by score."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = 'pending' ORDER BY score DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_status(self, issue_number: int, status: str, pr_url: str = None):
        """Update task status."""
        with sqlite3.connect(self.db_path) as conn:
            if pr_url:
                conn.execute(
                    "UPDATE tasks SET status = ?, pr_url = ?, updated_at = ? WHERE issue_number = ?",
                    (status, pr_url, time.time(), issue_number)
                )
            else:
                conn.execute(
                    "UPDATE tasks SET status = ?, updated_at = ? WHERE issue_number = ?",
                    (status, time.time(), issue_number)
                )

    def get_stats(self) -> dict:
        """Get overall statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT count(*) FROM tasks").fetchone()[0]
            pending = conn.execute("SELECT count(*) FROM tasks WHERE status = 'pending'").fetchone()[0]
            in_progress = conn.execute("SELECT count(*) FROM tasks WHERE status = 'in_progress'").fetchone()[0]
            submitted = conn.execute("SELECT count(*) FROM tasks WHERE status = 'submitted'").fetchone()[0]
            merged = conn.execute("SELECT count(*) FROM tasks WHERE status = 'merged'").fetchone()[0]
            earnings = conn.execute(
                "SELECT COALESCE(SUM(amount_rtc), 0) FROM tasks WHERE status = 'merged'"
            ).fetchone()[0]

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "submitted": submitted,
            "merged": merged,
            "earnings_rtc": earnings,
            "earnings_usd": earnings * RTC_TO_USD,
        }
