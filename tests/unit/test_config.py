from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.core.config import AppConfig, BrowserConfig, LimitsConfig, load_config


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

    def test_raises_when_api_key_missing(
        self, tmp_config: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        # Prevent load_dotenv from picking up local .env
        monkeypatch.chdir(tmp_config.parent)
        with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
            load_config(str(tmp_config))

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
        from src.core.config import TargetConfig
        with pytest.raises(Exception):
            TargetConfig(type="keyword", value="test", max_posts=100)  # le=50
