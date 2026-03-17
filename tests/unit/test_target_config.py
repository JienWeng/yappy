"""Tests for TargetConfig feature coverage."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import TargetConfig


class TestTargetConfigTypes:
    """Test TargetConfig type validation."""

    def test_type_keyword(self) -> None:
        """Should accept type keyword."""
        cfg = TargetConfig(type="keyword", value="python")
        assert cfg.type == "keyword"

    def test_type_url(self) -> None:
        """Should accept type url."""
        cfg = TargetConfig(type="url", value="https://linkedin.com/feed")
        assert cfg.type == "url"

    def test_type_feed(self) -> None:
        """Should accept type feed."""
        cfg = TargetConfig(type="feed")
        assert cfg.type == "feed"

    def test_type_connections(self) -> None:
        """Should accept type connections."""
        cfg = TargetConfig(type="connections")
        assert cfg.type == "connections"


class TestTargetConfigDefaults:
    """Test TargetConfig default values."""

    def test_default_max_posts(self) -> None:
        """Default max_posts should be 5."""
        cfg = TargetConfig(type="feed")
        assert cfg.max_posts == 5

    def test_default_recency_hours(self) -> None:
        """Default recency_hours should be 24."""
        cfg = TargetConfig(type="keyword", value="test")
        assert cfg.recency_hours == 24

    def test_default_value_empty_for_feed(self) -> None:
        """Default value should be empty for feed type."""
        cfg = TargetConfig(type="feed")
        assert cfg.value == ""


class TestTargetConfigValidation:
    """Test TargetConfig validation rules."""

    def test_max_posts_min_valid(self) -> None:
        """max_posts of 1 should be valid."""
        cfg = TargetConfig(type="feed", max_posts=1)
        assert cfg.max_posts == 1

    def test_max_posts_max_valid(self) -> None:
        """max_posts of 50 should be valid."""
        cfg = TargetConfig(type="feed", max_posts=50)
        assert cfg.max_posts == 50

    def test_max_posts_below_min_invalid(self) -> None:
        """max_posts below 1 should raise ValidationError."""
        with pytest.raises(ValidationError):
            TargetConfig(type="feed", max_posts=0)

    def test_max_posts_above_max_invalid(self) -> None:
        """max_posts above 50 should raise ValidationError."""
        with pytest.raises(ValidationError):
            TargetConfig(type="feed", max_posts=51)

    def test_recency_hours_min_valid(self) -> None:
        """recency_hours of 1 should be valid."""
        cfg = TargetConfig(type="keyword", value="test", recency_hours=1)
        assert cfg.recency_hours == 1

    def test_recency_hours_max_valid(self) -> None:
        """recency_hours of 168 should be valid."""
        cfg = TargetConfig(type="keyword", value="test", recency_hours=168)
        assert cfg.recency_hours == 168

    def test_recency_hours_below_min_invalid(self) -> None:
        """recency_hours below 1 should raise ValidationError."""
        with pytest.raises(ValidationError):
            TargetConfig(type="keyword", value="test", recency_hours=0)


class TestTargetConfigImmutable:
    """Test TargetConfig is immutable (frozen)."""

    def test_config_is_frozen(self) -> None:
        """TargetConfig should be frozen (immutable)."""
        cfg = TargetConfig(type="feed")
        with pytest.raises((ValidationError, TypeError)):
            cfg.max_posts = 10  # type: ignore[misc]
