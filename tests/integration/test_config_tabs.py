from unittest.mock import patch

import pytest
import yaml
from textual.widgets import Checkbox, Input

from src.tui.app import YappyApp
from src.tui.screens.config_editor import ConfigEditorScreen


@pytest.mark.asyncio
async def test_config_editor_saves_headless_toggle(tmp_path, monkeypatch):
    import os
    import textwrap
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        limits:
          daily_comment_limit: 20
          min_delay_seconds: 15
          max_delay_seconds: 55
        ai:
          model_name: gemini-3-flash-preview
          temperature: 0.85
        browser:
          headless: false
        """))

    monkeypatch.setattr("src.core.paths.config_file", lambda: config_file)
    monkeypatch.setattr("src.core.paths.env_file", lambda: tmp_path / ".env")

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            # Manually push screen with correct path to avoid local config.yaml usage
            await pilot.app.push_screen(ConfigEditorScreen(config_path=str(config_file)))
            await pilot.pause(0.1)

            # Set value directly
            screen = pilot.app.screen
            checkbox = screen.query_one("#cfg-headless", Checkbox)
            checkbox.value = True

            # Call save directly
            screen.action_save_config()
            await pilot.pause(0.1)

            # Verify file
            with open(config_file) as f:
                saved_config = yaml.safe_load(f)
                assert saved_config["browser"]["headless"] is True
@pytest.mark.asyncio
async def test_config_editor_saves_api_key_to_env(tmp_path, monkeypatch):
    import os
    config_file = tmp_path / "config.yaml"
    config_file.write_text("browser:\n  headless: true\n")
    env_file = tmp_path / ".env"

    monkeypatch.setattr("src.core.paths.config_file", lambda: config_file)
    monkeypatch.setattr("src.core.paths.env_file", lambda: env_file)
    with patch.dict(os.environ, {"GEMINI_API_KEY": "old-key"}):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            # Manually push screen with correct path
            await pilot.app.push_screen(ConfigEditorScreen(config_path=str(config_file)))
            await pilot.pause(0.1)

            # Set value directly
            screen = pilot.app.screen
            api_input = screen.query_one("#cfg-api-key", Input)
            api_input.value = "new-secret-key"

            # Call save directly
            screen.action_save_config()
            await pilot.pause(0.1)

            # Verify .env
            assert "GEMINI_API_KEY=new-secret-key" in env_file.read_text()


def test_config_save_roundtrip(tmp_path, monkeypatch):
    """Saving config should produce a valid AppConfig on reload."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "targets": [{"type": "feed"}],
        "limits": {
            "daily_comment_limit": 10,
            "min_delay_seconds": 10,
            "max_delay_seconds": 60,
            "min_wpm": 40,
            "max_wpm": 90,
        },
        "ai": {"model_name": "gemini-3-flash-preview"},
        "browser": {"headless": True},
    }))

    monkeypatch.setattr("src.core.paths.env_file", lambda: tmp_path / ".env")
    monkeypatch.setattr("src.core.paths.browser_profile_dir", lambda: tmp_path / "browser")
    monkeypatch.setattr("src.core.paths.db_path", lambda: tmp_path / "db.sqlite")

    from src.core.config import load_config
    cfg = load_config(str(config_file))
    assert cfg.limits.daily_comment_limit == 10
    assert cfg.limits.min_delay_seconds < cfg.limits.max_delay_seconds
    assert cfg.limits.min_wpm < cfg.limits.max_wpm
    assert len(cfg.targets) == 1
    assert cfg.targets[0].type == "feed"
    assert cfg.browser.headless is True


def test_config_invalid_min_max_rejects(tmp_path, monkeypatch):
    """Config with min_delay >= max_delay should fail to load."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "targets": [{"type": "feed"}],
        "limits": {
            "min_delay_seconds": 60,
            "max_delay_seconds": 10,
        },
    }))

    monkeypatch.setattr("src.core.paths.env_file", lambda: tmp_path / ".env")
    monkeypatch.setattr("src.core.paths.browser_profile_dir", lambda: tmp_path / "browser")
    monkeypatch.setattr("src.core.paths.db_path", lambda: tmp_path / "db.sqlite")

    from src.core.config import load_config
    with pytest.raises(Exception):
        load_config(str(config_file))

