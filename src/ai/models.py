from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GeneratedComment:
    text: str
    post_url: str
    generated_at: datetime
    model_used: str


@dataclass(frozen=True)
class GenerateResult:
    comment: GeneratedComment | None
    error: str | None
