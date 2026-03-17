"""Tests validating that like/comment behavior matches TUI display and config."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from src.core.config import (
    AIConfig,
    AppConfig,
    BrowserConfig,
    LimitsConfig,
    TargetConfig,
)
from src.executor.models import PostResult
from src.storage.activity_log import ActivityLog

# ---------------------------------------------------------------------------
# ActivityLog: count_today should only count comments, not likes
# ---------------------------------------------------------------------------

class TestActivityLogMigration:
    """Verify activity_log migrates old databases missing action_type column."""

    def test_legacy_db_without_action_type(self, tmp_path):
        """An old database without action_type column should be migrated on init."""
        db_path = tmp_path / "legacy.db"
        # Create a legacy table without action_type or failure_reason
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_url TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
                created_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO activity_log (post_url, comment_text, status, created_at) "
            "VALUES ('https://linkedin.com/post/old', 'old comment', 'success', ?)",
            (datetime.now(UTC).isoformat(),),
        )
        conn.commit()
        conn.close()

        # ActivityLog init should migrate the table
        log = ActivityLog(db_path=str(db_path))

        # count_today should work (not crash with "no such column")
        count = log.count_today()
        assert count == 1  # legacy row has NULL action_type, treated as comment

        # was_commented should work
        assert log.was_commented("https://linkedin.com/post/old") is True

        # New records with action_type should also work
        log.record_activity(
            post_url="https://linkedin.com/post/new",
            status="success",
            action_type="like",
        )
        assert log.count_today() == 1  # like shouldn't count


class TestActivityLogCounting:
    """Verify activity_log correctly separates comment vs like counts."""

    @pytest.fixture
    def log(self, tmp_path):
        db = tmp_path / "test.db"
        return ActivityLog(db_path=str(db))

    def test_count_today_ignores_likes(self, log):
        """count_today() should only count successful *comments*, not likes."""
        log.record_activity(
            post_url="https://linkedin.com/post/1",
            status="success",
            action_type="comment",
            comment_text="Great post!",
        )
        log.record_activity(
            post_url="https://linkedin.com/post/1",
            status="success",
            action_type="like",
        )
        log.record_activity(
            post_url="https://linkedin.com/post/2",
            status="success",
            action_type="comment",
            comment_text="Interesting take!",
        )
        # Should be 2 comments, not 3 total
        assert log.count_today() == 2

    def test_was_commented_ignores_likes(self, log):
        """was_commented() should only match comment actions, not likes."""
        log.record_activity(
            post_url="https://linkedin.com/post/1",
            status="success",
            action_type="like",
        )
        # A like should NOT count as "already commented"
        assert log.was_commented("https://linkedin.com/post/1") is False

        # Now add an actual comment
        log.record_activity(
            post_url="https://linkedin.com/post/1",
            status="success",
            action_type="comment",
            comment_text="Nice!",
        )
        assert log.was_commented("https://linkedin.com/post/1") is True

    def test_count_today_excludes_failed(self, log):
        """count_today() should exclude failed attempts."""
        log.record_activity(
            post_url="https://linkedin.com/post/1",
            status="failed",
            action_type="comment",
            failure_reason="timeout",
        )
        assert log.count_today() == 0


# ---------------------------------------------------------------------------
# Orchestrator: like recording and config-driven liking
# ---------------------------------------------------------------------------

class TestOrchestratorLikeConfig:
    """Verify the orchestrator respects auto_like configuration."""

    @pytest.fixture
    def mock_config(self):
        return AppConfig(
            targets=(TargetConfig(type="feed", max_posts=1),),
            browser=BrowserConfig(),
            ai=AIConfig(),
            limits=LimitsConfig(),
            gemini_api_key="test-key",
        )

    def test_post_result_tracks_liked(self):
        """PostResult should carry the liked boolean from CommentPoster."""
        result = PostResult(
            success=True,
            post_url="https://linkedin.com/post/1",
            comment_text="Nice!",
            posted_at=datetime.now(UTC),
            error=None,
            liked=True,
        )
        assert result.liked is True

    def test_post_result_liked_defaults_false(self):
        """PostResult.liked should default to False."""
        result = PostResult(
            success=True,
            post_url="https://linkedin.com/post/1",
            comment_text="Nice!",
            posted_at=datetime.now(UTC),
            error=None,
        )
        assert result.liked is False


# ---------------------------------------------------------------------------
# CommentPoster: like selectors and behavior
# ---------------------------------------------------------------------------

class TestCommentPosterLikeSelectors:
    """Verify the like button selectors target unreacted state only."""

    def test_like_selectors_avoid_unlike(self):
        """LIKE_BUTTON_SELECTORS should not match 'Unlike' buttons."""
        from src.executor.comment_poster import LIKE_BUTTON_SELECTORS

        for sel in LIKE_BUTTON_SELECTORS:
            # None of the selectors should contain 'Unlike' without :not
            if "Unlike" in sel:
                assert ":not" in sel, (
                    f"Selector {sel!r} matches 'Unlike' without a :not guard"
                )

    def test_like_selectors_non_empty(self):
        """There should be at least one like button selector."""
        from src.executor.comment_poster import LIKE_BUTTON_SELECTORS

        assert len(LIKE_BUTTON_SELECTORS) > 0


# ---------------------------------------------------------------------------
# StrategyPanel: auto_like display
# ---------------------------------------------------------------------------

class TestStrategyPanelDisplay:
    """Verify StrategyPanel displays actions correctly based on auto_like."""

    def test_update_strategy_comment_only(self):
        """When auto_like=False, actions should say 'Comment'."""
        from src.tui.widgets.strategy_panel import StrategyPanel

        panel = StrategyPanel()
        panel.update_strategy(
            persona="insightful_expert",
            targets=["Home Feed"],
            auto_like=False,
        )
        assert panel.actions == "Comment"

    def test_update_strategy_comment_and_like(self):
        """When auto_like=True, actions should say 'Comment + Like'."""
        from src.tui.widgets.strategy_panel import StrategyPanel

        panel = StrategyPanel()
        panel.update_strategy(
            persona="insightful_expert",
            targets=["Home Feed"],
            auto_like=True,
        )
        assert panel.actions == "Comment + Like"


# ---------------------------------------------------------------------------
# Config: auto_like option
# ---------------------------------------------------------------------------

class TestConfigAutoLike:
    """Verify config supports auto_like toggle."""

    def test_limits_config_has_auto_like(self):
        """LimitsConfig should have an auto_like field."""
        config = LimitsConfig()
        assert hasattr(config, "auto_like"), (
            "LimitsConfig is missing 'auto_like' field"
        )

    def test_auto_like_defaults_true(self):
        """auto_like should default to True for backward compatibility."""
        config = LimitsConfig()
        assert config.auto_like is True

    def test_auto_like_can_be_disabled(self):
        """auto_like can be set to False."""
        config = LimitsConfig(auto_like=False)
        assert config.auto_like is False
