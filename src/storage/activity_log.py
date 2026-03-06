from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.storage.models import ActivityRecord, DailyStats

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_url TEXT NOT NULL,
    comment_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
    failure_reason TEXT,
    action_type TEXT DEFAULT 'comment',
    created_at TEXT NOT NULL
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at
ON activity_log (created_at)
"""


class ActivityLog:
    """SQLite-backed log of commenting activity with daily limit enforcement."""

    def __init__(self, db_path: str = "data/activity.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)
            conn.execute(_CREATE_INDEX)
            # Migrate existing databases that lack newer columns
            for col_sql in (
                "ALTER TABLE activity_log ADD COLUMN failure_reason TEXT",
                "ALTER TABLE activity_log ADD COLUMN action_type TEXT DEFAULT 'comment'",
            ):
                try:
                    conn.execute(col_sql)
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.commit()

    def record_activity(
        self,
        post_url: str,
        status: str,
        action_type: str = "comment",
        comment_text: str = "",
        failure_reason: str | None = None,
    ) -> None:
        """Record an activity (comment or like) attempt in the log."""
        if status not in ("success", "failed"):
            raise ValueError(
                f"Invalid status: {status!r}. Must be 'success' or 'failed'."
            )
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO activity_log (post_url, comment_text, status, failure_reason, action_type, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (post_url, comment_text, status, failure_reason, action_type, now),
            )
            conn.commit()

    def record_comment(self, post_url: str, comment_text: str, status: str, failure_reason: str | None = None) -> None:
        """Deprecated: use record_activity instead."""
        self.record_activity(
            post_url=post_url,
            status=status,
            action_type="comment",
            comment_text=comment_text,
            failure_reason=failure_reason,
        )

    def count_today(self) -> int:
        """Count successful comments posted today (UTC). Excludes likes."""
        today = datetime.now(timezone.utc).date().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM activity_log "
                "WHERE status = 'success' AND created_at LIKE ? "
                "AND (action_type = 'comment' OR action_type IS NULL)",
                (f"{today}%",),
            ).fetchone()
        return row[0] if row else 0

    def was_commented(self, post_url: str) -> bool:
        """Return True if this post URL was already successfully commented on."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM activity_log "
                "WHERE post_url = ? AND status = 'success' "
                "AND (action_type = 'comment' OR action_type IS NULL) LIMIT 1",
                (post_url,),
            ).fetchone()
        return row is not None

    def get_recent(self, limit: int = 50) -> list[ActivityRecord]:
        """Return the most recent activity records, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, post_url, comment_text, status, failure_reason, action_type, created_at "
                "FROM activity_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            ActivityRecord(
                id=row["id"],
                post_url=row["post_url"],
                comment_text=row["comment_text"],
                status=row["status"],
                failure_reason=row["failure_reason"],
                action_type=row["action_type"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_daily_stats(self, date: str | None = None) -> DailyStats:
        """Return stats for a given UTC date (default: today)."""
        if date is None:
            date = datetime.now(timezone.utc).date().isoformat()

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM activity_log "
                "WHERE created_at LIKE ? GROUP BY status",
                (f"{date}%",),
            ).fetchall()

        counts: dict[str, int] = {"success": 0, "failed": 0}
        for row in rows:
            counts[row["status"]] = row["cnt"]

        return DailyStats(
            date=date,
            total_attempts=counts["success"] + counts["failed"],
            successful=counts["success"],
            failed=counts["failed"],
        )
