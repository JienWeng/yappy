"""Tests for BrowserConfig feature coverage."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import BrowserConfig


class TestBrowserConfigDefaults:
    """Test BrowserConfig default values."""

    def test_default_headless(self) -> None:
        """Default headless should be False (visible browser)."""
        cfg = BrowserConfig()
        assert cfg.headless is False

    def test_default_user_data_dir(self) -> None:
        """Default user_data_dir should be empty string."""
        cfg = BrowserConfig()
        assert cfg.user_data_dir == ""

    def test_default_viewport_width(self) -> None:
        """Default viewport_width should be 1920."""
        cfg = BrowserConfig()
        assert cfg.viewport_width == 1920

    def test_default_viewport_height(self) -> None:
        """Default viewport_height should be 1080."""
        cfg = BrowserConfig()
        assert cfg.viewport_height == 1080


class TestBrowserConfigCustomValues:
    """Test BrowserConfig accepts custom values."""

    def test_custom_headless_true(self) -> None:
        """Should accept headless=True."""
        cfg = BrowserConfig(headless=True)
        assert cfg.headless is True

    def test_custom_user_data_dir(self) -> None:
        """Should accept custom user_data_dir."""
        cfg = BrowserConfig(user_data_dir="/custom/path")
        assert cfg.user_data_dir == "/custom/path"

    def test_custom_viewport(self) -> None:
        """Should accept custom viewport dimensions."""
        cfg = BrowserConfig(viewport_width=1280, viewport_height=720)
        assert cfg.viewport_width == 1280
        assert cfg.viewport_height == 720


class TestBrowserConfigImmutable:
    """Test BrowserConfig is immutable (frozen)."""

    def test_config_is_frozen(self) -> None:
        """BrowserConfig should be frozen (immutable)."""
        cfg = BrowserConfig()
        with pytest.raises((ValidationError, TypeError)):
            cfg.headless = True  # type: ignore[misc]
