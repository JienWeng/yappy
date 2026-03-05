"""Custom Textual Message classes for worker-UI communication."""

from __future__ import annotations

from textual.message import Message


class BotStarted(Message):
    """Emitted when the bot worker starts running."""


class BotStatus(Message):
    """General status update from the bot."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message


class PostFound(Message):
    """Emitted when a new LinkedIn post is discovered."""

    def __init__(
        self,
        post_url: str,
        author_name: str,
        text_preview: str,
    ) -> None:
        super().__init__()
        self.post_url = post_url
        self.author_name = author_name
        self.text_preview = text_preview


class PostSkipped(Message):
    """Emitted when a post is skipped (e.g., already commented, filtered)."""

    def __init__(self, post_url: str, reason: str) -> None:
        super().__init__()
        self.post_url = post_url
        self.reason = reason


class CommentGenerated(Message):
    """Emitted when the AI generates a comment for a post."""

    def __init__(
        self,
        post_url: str,
        author_name: str,
        comment_text: str,
    ) -> None:
        super().__init__()
        self.post_url = post_url
        self.author_name = author_name
        self.comment_text = comment_text


class CommentAwaitingApproval(Message):
    """Emitted when a generated comment requires user approval before posting."""

    def __init__(
        self,
        post_url: str,
        author_name: str,
        post_preview: str,
        comment_text: str,
    ) -> None:
        super().__init__()
        self.post_url = post_url
        self.author_name = author_name
        self.post_preview = post_preview
        self.comment_text = comment_text


class CommentPosted(Message):
    """Emitted when a comment is successfully posted to LinkedIn."""

    def __init__(self, post_url: str, comment_text: str) -> None:
        super().__init__()
        self.post_url = post_url
        self.comment_text = comment_text


class CommentFailed(Message):
    """Emitted when posting a comment fails."""

    def __init__(self, post_url: str, error: str) -> None:
        super().__init__()
        self.post_url = post_url
        self.error = error


class StatsUpdated(Message):
    """Emitted to update the UI with current session statistics."""

    def __init__(
        self,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        super().__init__()
        self.comments_today = comments_today
        self.daily_limit = daily_limit
        self.posts_scanned = posts_scanned
        self.posts_skipped = posts_skipped
        self.success_count = success_count
        self.fail_count = fail_count


class BotPaused(Message):
    """Emitted when the bot is paused."""


class BotStopped(Message):
    """Emitted when the bot stops running."""

    def __init__(self, reason: str = "") -> None:
        super().__init__()
        self.reason = reason


class BotError(Message):
    """Emitted when the bot encounters an error."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error
