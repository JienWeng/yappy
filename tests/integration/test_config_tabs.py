import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.tui.app import YappyApp
from src.tui.screens.config_editor import ConfigEditorScreen
from textual.widgets import Checkbox, Input, Static

@pytest.mark.asyncio
async def test_config_editor_saves_headless_toggle(tmp_path, monkeypatch):
    from unittest.mock import patch
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
    from unittest.mock import patch
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

