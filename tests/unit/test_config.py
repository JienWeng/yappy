from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from pydantic import ValidationError

from src.core.config import AppConfig, BrowserConfig, LimitsConfig, TargetConfig, load_config


def write_config(data: dict, path: Path) -> None:
    with path.open("w") as f:
        yaml.dump(data, f)


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.yaml"
    write_config(
        {
            "targets": [{"type": "keyword", "value": "test keyword", "max_posts": 3}],
            "browser": {"headless": False, "user_data_dir": "data/browser_profile"},
            "ai": {"model_name": "gemini-3-flash-preview", "temperature": 0.85},
            "limits": {"daily_comment_limit": 10, "min_wpm": 55, "max_wpm": 80},
        },
        cfg,
    )
    return cfg


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        config = load_config(str(tmp_config))
        assert isinstance(config, AppConfig)
        assert len(config.targets) == 1
        assert config.targets[0].value == "test keyword"
        assert config.gemini_api_key == "test-key-123"

    def test_does_not_raise_when_api_key_missing(
        self, tmp_config: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unittest.mock import patch
        import os
        # Fully clear env to avoid picking up keys from system
        with patch.dict(os.environ, {}, clear=True):
            # Mock paths.env_file to point to a non-existent file in tmp_config.parent
            with patch("src.core.paths.env_file", return_value=tmp_config.parent / ".env.missing"):
                # Prevent load_dotenv from picking up local .env by staying in empty tmp dir
                monkeypatch.chdir(tmp_config.parent)
                
                config = load_config(str(tmp_config))
                assert config.gemini_api_key == ""
                # Verify it actually returns empty even if it was called

    def test_raises_when_config_file_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_config_is_frozen(self, tmp_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        config = load_config(str(tmp_config))
        with pytest.raises(Exception):  # ValidationError or TypeError for frozen
            config.db_path = "new_path"  # type: ignore[misc]

    def test_browser_config_defaults(self) -> None:
        b = BrowserConfig()
        assert b.headless is False
        assert b.user_data_dir == ""

    def test_limits_config_validation(self) -> None:
        with pytest.raises(Exception):
            LimitsConfig(daily_comment_limit=0)  # ge=1

    def test_limits_config_max_posts_cap(self) -> None:
        with pytest.raises(Exception):
            TargetConfig(type="keyword", value="test", max_posts=100)  # le=50


class TestLimitsConfigCrossFieldValidation:
    def test_min_delay_must_be_less_than_max_delay(self) -> None:
        with pytest.raises(ValidationError):
            LimitsConfig(min_delay_seconds=50, max_delay_seconds=10)

    def test_min_delay_equal_to_max_delay_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LimitsConfig(min_delay_seconds=30, max_delay_seconds=30)

    def test_min_wpm_must_be_less_than_max_wpm(self) -> None:
        with pytest.raises(ValidationError):
            LimitsConfig(min_wpm=80, max_wpm=30)

    def test_min_wpm_equal_to_max_wpm_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LimitsConfig(min_wpm=50, max_wpm=50)

    def test_valid_min_max_accepted(self) -> None:
        cfg = LimitsConfig(
            min_delay_seconds=10, max_delay_seconds=50,
            min_wpm=40, max_wpm=90,
        )
        assert cfg.min_delay_seconds < cfg.max_delay_seconds
        assert cfg.min_wpm < cfg.max_wpm


class TestAppConfigTargetValidation:
    def test_empty_targets_raises(self) -> None:
        """AppConfig with no targets should raise ValidationError."""
        with pytest.raises(ValidationError):
            AppConfig(targets=())

    def test_default_targets_raises(self) -> None:
        """AppConfig with default (empty) targets should raise ValidationError."""
        with pytest.raises(ValidationError):
            AppConfig()

    def test_single_target_accepted(self) -> None:
        """AppConfig with at least one target should be valid."""
        cfg = AppConfig(targets=(TargetConfig(type="feed"),))
        assert len(cfg.targets) == 1

    def test_multiple_targets_accepted(self) -> None:
        """AppConfig with multiple targets should be valid."""
        cfg = AppConfig(
            targets=(
                TargetConfig(type="feed"),
                TargetConfig(type="keyword", value="python"),
            ),
        )
        assert len(cfg.targets) == 2
