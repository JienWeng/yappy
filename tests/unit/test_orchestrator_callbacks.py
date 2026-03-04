from __future__ import annotations

from src.core.callbacks import NullCallbacks, OrchestratorCallbacks


class TestNullCallbacksSatisfiesProtocol:
    def test_null_callbacks_is_instance_of_protocol(self) -> None:
        cb = NullCallbacks()
        assert isinstance(cb, OrchestratorCallbacks)


class TestNullCallbacksNoOps:
    def test_on_post_found_returns_none(self) -> None:
        cb = NullCallbacks()
        result = cb.on_post_found(
            post_url="https://linkedin.com/post/1",
            author_name="Alice",
            text_preview="Hello world",
        )
        assert result is None

    def test_on_post_skipped_returns_none(self) -> None:
        cb = NullCallbacks()
        result = cb.on_post_skipped(
            post_url="https://linkedin.com/post/1",
            reason="duplicate",
        )
        assert result is None

    def test_on_comment_generated_returns_none(self) -> None:
        cb = NullCallbacks()
        result = cb.on_comment_generated(
            post_url="https://linkedin.com/post/1",
            author_name="Alice",
            comment_text="Great post!",
        )
        assert result is None

    def test_on_comment_posted_returns_none(self) -> None:
        cb = NullCallbacks()
        result = cb.on_comment_posted(
            post_url="https://linkedin.com/post/1",
            comment_text="Great post!",
        )
        assert result is None

    def test_on_comment_failed_returns_none(self) -> None:
        cb = NullCallbacks()
        result = cb.on_comment_failed(
            post_url="https://linkedin.com/post/1",
            error="timeout",
        )
        assert result is None

    def test_on_stats_updated_returns_none(self) -> None:
        cb = NullCallbacks()
        result = cb.on_stats_updated(
            comments_today=5,
            daily_limit=20,
            posts_scanned=10,
            posts_skipped=3,
            success_count=5,
            fail_count=2,
        )
        assert result is None


class TestNullCallbacksControlMethods:
    def test_should_pause_returns_false(self) -> None:
        cb = NullCallbacks()
        assert cb.should_pause() is False

    def test_should_stop_returns_false(self) -> None:
        cb = NullCallbacks()
        assert cb.should_stop() is False
