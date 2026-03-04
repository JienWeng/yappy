from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.config import TargetConfig


@dataclass(frozen=True)
class LinkedInPost:
    post_url: str
    author_name: str
    author_profile_url: str
    post_text: str
    scraped_at: datetime
    source_target: str  # The keyword or URL that led to this post
    reaction_count: int = 0
    comment_count: int = 0
    existing_comments: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScrapeResult:
    target_value: str
    posts: tuple[LinkedInPost, ...]
    error: str | None
    duration_seconds: float
