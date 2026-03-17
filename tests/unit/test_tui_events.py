from __future__ import annotations

from textual.message import Message

from src.tui.events import (
    BotError,
    BotPaused,
    BotStarted,
    BotStatus,
    BotStopped,
    CommentAwaitingApproval,
    CommentFailed,
    CommentGenerated,
    CommentPosted,
    PostFound,
    PostSkipped,
    StatsUpdated,
)


class TestBotStarted:
    def test_construction(self) -> None:
        event = BotStarted()
        assert isinstance(event, Message)


class TestPostFound:
    def test_construction_and_attributes(self) -> None:
        event = PostFound(
            post_url="https://linkedin.com/post/1",
            author_name="Alice",
            text_preview="Hello world...",
        )
        assert event.post_url == "https://linkedin.com/post/1"
        assert event.author_name == "Alice"
        assert event.text_preview == "Hello world..."
        assert isinstance(event, Message)


class TestPostSkipped:
    def test_construction_and_attributes(self) -> None:
        event = PostSkipped(
            post_url="https://linkedin.com/post/2",
            reason="already commented",
        )
        assert event.post_url == "https://linkedin.com/post/2"
        assert event.reason == "already commented"
        assert isinstance(event, Message)


class TestCommentGenerated:
    def test_construction_and_attributes(self) -> None:
        event = CommentGenerated(
            post_url="https://linkedin.com/post/3",
            author_name="Bob",
            comment_text="Great insight!",
        )
        assert event.post_url == "https://linkedin.com/post/3"
        assert event.author_name == "Bob"
        assert event.comment_text == "Great insight!"
        assert isinstance(event, Message)


class TestCommentAwaitingApproval:
    def test_construction_and_attributes(self) -> None:
        event = CommentAwaitingApproval(
            post_url="https://linkedin.com/post/4",
            author_name="Carol",
            post_preview="A post about AI...",
            comment_text="Interesting perspective!",
        )
        assert event.post_url == "https://linkedin.com/post/4"
        assert event.author_name == "Carol"
        assert event.post_preview == "A post about AI..."
        assert event.comment_text == "Interesting perspective!"
        assert isinstance(event, Message)


class TestCommentPosted:
    def test_construction_and_attributes(self) -> None:
        event = CommentPosted(
            post_url="https://linkedin.com/post/5",
            comment_text="Well said!",
        )
        assert event.post_url == "https://linkedin.com/post/5"
        assert event.comment_text == "Well said!"
        assert isinstance(event, Message)


class TestCommentFailed:
    def test_construction_and_attributes(self) -> None:
        event = CommentFailed(
            post_url="https://linkedin.com/post/6",
            error="Timeout occurred",
        )
        assert event.post_url == "https://linkedin.com/post/6"
        assert event.error == "Timeout occurred"
        assert isinstance(event, Message)


class TestStatsUpdated:
    def test_construction_and_attributes(self) -> None:
        event = StatsUpdated(
            comments_today=5,
            daily_limit=20,
            posts_scanned=50,
            posts_skipped=10,
            success_count=5,
            fail_count=1,
        )
        assert event.comments_today == 5
        assert event.daily_limit == 20
        assert event.posts_scanned == 50
        assert event.posts_skipped == 10
        assert event.success_count == 5
        assert event.fail_count == 1
        assert isinstance(event, Message)


class TestBotPaused:
    def test_construction(self) -> None:
        event = BotPaused()
        assert isinstance(event, Message)


class TestBotStopped:
    def test_construction_with_default_reason(self) -> None:
        event = BotStopped()
        assert event.reason == ""
        assert isinstance(event, Message)

    def test_construction_with_custom_reason(self) -> None:
        event = BotStopped(reason="user requested")
        assert event.reason == "user requested"


class TestBotStatus:
    def test_construction_and_attributes(self) -> None:
        event = BotStatus(message="Bot resumed")
        assert event.message == "Bot resumed"
        assert isinstance(event, Message)


class TestPauseResumeStatusText:
    """Verify the dashboard shows 'p to resume' (not 's to resume') on pause."""

    def test_paused_status_contains_p_to_resume(self) -> None:
        """The on_bot_paused handler must tell users to press p, not s."""
        # Import here to avoid circular import issues at module level
        import inspect

        from src.tui.screens.dashboard import DashboardScreen

        source = inspect.getsource(DashboardScreen.on_bot_paused)
        assert "p to resume" in source, (
            "on_bot_paused should instruct 'press p to resume'"
        )
        assert "s to resume" not in source, (
            "on_bot_paused must NOT say 'press s to resume'"
        )


class TestBotError:
    def test_construction_and_attributes(self) -> None:
        event = BotError(error="Connection lost")
        assert event.error == "Connection lost"
        assert isinstance(event, Message)


class TestMessageRoutingToScreen:
    """Verify messages posted on screen (not app) reach DashboardScreen handlers."""

    def test_app_post_message_does_not_reach_screen(self) -> None:
        """Textual messages bubble UP, so app.post_message never reaches child screens."""
        import inspect

        from src.tui.app import YappyApp

        source = inspect.getsource(YappyApp._run_bot)
        # _run_bot must NOT use self.post_message (posts on App, never reaches Screen)
        # It should use screen.post_message instead
        assert "self.post_message" not in source, (
            "_run_bot must post on screen, not app — "
            "app.post_message drops messages (Textual bubbles UP only)"
        )

    def test_bot_worker_posts_on_screen(self) -> None:
        """BotWorkerCallbacks must post on screen, not app."""
        import inspect

        from src.tui.workers.bot_worker import BotWorkerCallbacks

        source = inspect.getsource(BotWorkerCallbacks)
        assert "self._app.post_message" not in source, (
            "BotWorkerCallbacks must use self._screen.post_message, not self._app.post_message"
        )
