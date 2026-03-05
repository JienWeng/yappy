"""Tests for the BotWorkerCallbacks bridge."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.tui.workers.bot_worker import BotWorkerCallbacks


class TestBotWorkerCallbacks:
    def test_on_post_found_posts_message(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        cb.on_post_found(
            post_url="https://linkedin.com/post/1",
            author_name="Jane",
            text_preview="Hello world",
        )
        app.call_from_thread.assert_called_once()

    def test_should_pause_reads_flag(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        assert cb.should_pause() is False
        cb.request_pause()
        assert cb.should_pause() is True
        cb.request_resume()
        assert cb.should_pause() is False

    def test_should_stop_reads_flag(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        assert cb.should_stop() is False
        cb.request_stop()
        assert cb.should_stop() is True

    def test_set_manual_mode(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        assert cb.is_manual_mode is False
        cb.is_manual_mode = True
        assert cb.is_manual_mode is True

    def test_auto_mode_approves_immediately(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        decision, text = cb.on_awaiting_approval(
            post_url="url",
            author_name="Jane",
            post_preview="preview",
            comment_text="comment",
        )
        assert decision == "approve"
        assert text == "comment"
