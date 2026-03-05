from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OrchestratorCallbacks(Protocol):
    """Protocol for orchestrator lifecycle callbacks."""

    def on_post_found(
        self, *, post_url: str, author_name: str, text_preview: str
    ) -> None: ...

    def on_post_skipped(self, *, post_url: str, reason: str) -> None: ...

    def on_status(self, message: str) -> None: ...

    def on_comment_generated(
        self, *, post_url: str, author_name: str, comment_text: str
    ) -> None: ...

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None: ...

    def on_comment_failed(self, *, post_url: str, error: str) -> None: ...

    def on_stats_updated(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None: ...

    def should_pause(self) -> bool: ...

    def should_stop(self) -> bool: ...

    def on_awaiting_approval(
        self,
        *,
        post_url: str,
        author_name: str,
        post_preview: str,
        comment_text: str,
    ) -> tuple[str, str]:
        """Called when a comment needs approval.

        Returns (decision, comment_text) where decision is one of:
        "approve", "skip", "regenerate".
        """
        ...


class NullCallbacks:
    """No-op implementation of OrchestratorCallbacks."""

    def on_post_found(
        self, *, post_url: str, author_name: str, text_preview: str
    ) -> None:
        return None

    def on_post_skipped(self, *, post_url: str, reason: str) -> None:
        return None

    def on_status(self, message: str) -> None:
        return None

    def on_comment_generated(
        self, *, post_url: str, author_name: str, comment_text: str
    ) -> None:
        return None

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None:
        return None

    def on_comment_failed(self, *, post_url: str, error: str) -> None:
        return None

    def on_stats_updated(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        return None

    def should_pause(self) -> bool:
        return False

    def should_stop(self) -> bool:
        return False

    def on_awaiting_approval(
        self,
        *,
        post_url: str,
        author_name: str,
        post_preview: str,
        comment_text: str,
    ) -> tuple[str, str]:
        return ("approve", comment_text)
