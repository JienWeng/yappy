from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ActivityRecord:
    id: int
    post_url: str
    comment_text: str
    status: str  # "success" | "failed"
    created_at: datetime
    failure_reason: str | None = None


@dataclass(frozen=True)
class DailyStats:
    date: str  # ISO date string YYYY-MM-DD
    total_attempts: int
    successful: int
    failed: int
