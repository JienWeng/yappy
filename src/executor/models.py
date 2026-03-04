from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PostResult:
    success: bool
    post_url: str
    comment_text: str
    posted_at: datetime
    error: str | None
    liked: bool = False


@dataclass(frozen=True)
class ExecutionRecord:
    post_url: str
    comment_text: str
    model_used: str
    wpm_used: float
    started_at: datetime
    finished_at: datetime
    success: bool
    error: str | None
