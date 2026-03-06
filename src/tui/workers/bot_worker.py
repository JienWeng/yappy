"""Bot worker bridge: translates orchestrator callbacks to Textual messages."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from src.core.callbacks import NullCallbacks
from src.tui.events import (
    CommentAwaitingApproval,
    CommentFailed,
    CommentGenerated,
    CommentPosted,
    PostFound,
    PostSkipped,
    StatsUpdated,
    BotStatus,
)

if TYPE_CHECKING:
    from textual.app import App


class BotWorkerCallbacks(NullCallbacks):
    """Bridges orchestrator callbacks to Textual messages.

    Runs in a worker thread. Uses app.call_from_thread() to safely
    post messages to the Textual event loop.

    Messages are posted on the active *screen* (not the App) because
    Textual messages bubble UP — posting on App means handlers on
    DashboardScreen never see them.
    """

    def __init__(self, app: "App") -> None:
        self._app = app
        self._screen = app.screen
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._manual_mode = False
        self._approval_event = threading.Event()
        self._approval_decision: str = ""
        self._approval_text: str = ""

    @property
    def is_manual_mode(self) -> bool:
        return self._manual_mode

    @is_manual_mode.setter
    def is_manual_mode(self, value: bool) -> None:
        self._manual_mode = value

    def request_pause(self) -> None:
        self._pause_event.set()

    def request_resume(self) -> None:
        self._pause_event.clear()

    def request_stop(self) -> None:
        self._stop_event.set()

    def should_pause(self) -> bool:
        return self._pause_event.is_set()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def on_post_found(
        self, *, post_url: str, author_name: str, text_preview: str
    ) -> None:
        self._app.call_from_thread(
            self._screen.post_message,
            PostFound(
                post_url=post_url,
                author_name=author_name,
                text_preview=text_preview,
            ),
        )

    def on_post_skipped(self, *, post_url: str, reason: str) -> None:
        self._app.call_from_thread(
            self._screen.post_message,
            PostSkipped(post_url=post_url, reason=reason),
        )

    def on_status(self, message: str) -> None:
        self._app.call_from_thread(
            self._screen.post_message,
            BotStatus(message=message),
        )

    def on_comment_generated(
        self, *, post_url: str, author_name: str, comment_text: str
    ) -> None:
        self._app.call_from_thread(
            self._screen.post_message,
            CommentGenerated(
                post_url=post_url,
                author_name=author_name,
                comment_text=comment_text,
            ),
        )

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None:
        self._app.call_from_thread(
            self._screen.post_message,
            CommentPosted(post_url=post_url, comment_text=comment_text),
        )

    def on_comment_failed(self, *, post_url: str, error: str) -> None:
        self._app.call_from_thread(
            self._screen.post_message,
            CommentFailed(post_url=post_url, error=error),
        )

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
        self._app.call_from_thread(
            self._screen.post_message,
            StatsUpdated(
                comments_today=comments_today,
                daily_limit=daily_limit,
                posts_scanned=posts_scanned,
                posts_skipped=posts_skipped,
                success_count=success_count,
                fail_count=fail_count,
            ),
        )

    def on_awaiting_approval(
        self,
        *,
        post_url: str,
        author_name: str,
        post_preview: str,
        comment_text: str,
    ) -> tuple[str, str]:
        if not self._manual_mode:
            return ("approve", comment_text)

        self._app.call_from_thread(
            self._screen.post_message,
            CommentAwaitingApproval(
                post_url=post_url,
                author_name=author_name,
                post_preview=post_preview,
                comment_text=comment_text,
            ),
        )

        decision, text = self.wait_for_approval()
        return (decision, text)

    def submit_approval(self, decision: str, comment_text: str) -> None:
        """Called from UI thread when user makes a review decision."""
        self._approval_decision = decision
        self._approval_text = comment_text
        self._approval_event.set()

    def wait_for_approval(self) -> tuple[str, str]:
        """Called from worker thread. Blocks until user decides."""
        self._approval_event.clear()
        self._approval_event.wait()
        return self._approval_decision, self._approval_text
