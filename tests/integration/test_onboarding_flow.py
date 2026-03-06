import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.tui.app import YappyApp
from src.tui.screens.onboarding import OnboardingScreen
from src.tui.screens.dashboard import DashboardScreen
from textual.widgets import Input

@pytest.mark.asyncio
async def test_onboarding_flow_saves_api_key(tmp_path, monkeypatch):
    from unittest.mock import patch
    import os
    # Mock paths to use tmp_path
    monkeypatch.setattr("src.core.paths.env_file", lambda: tmp_path / ".env")
    monkeypatch.setattr("src.core.paths.config_file", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("src.core.paths.ensure_dirs", lambda: None)

    # Fully clear env to ensure onboarding is triggered
    with patch.dict(os.environ, {}, clear=True):
        app = YappyApp(skip_onboarding=False)
        async with app.run_test() as pilot:
            # Step 0: Welcome — click "Get Started"
            await pilot.click("#btn-start")
            await pilot.pause(0.3)

            # Step 1: API Key — set value THEN advance
            screen = pilot.app.screen
            screen.query_one("#api-key-input", Input).value = "test-api-key-999"
            await pilot.pause(0.1)  # let value propagate
            await pilot.click("#btn-next")
            await pilot.pause(0.3)

            # Step 2: LinkedIn
            await pilot.click("#btn-next")
            await pilot.pause(0.3)

            # Step 3: Targets
            await pilot.click("#btn-next")
            await pilot.pause(0.3)

            # Step 4: Finish — this triggers _finish_onboarding + file write
            await pilot.click("#btn-next")
            await pilot.pause(1.0)  # generous wait for file I/O on CI

            # Verify result
            env_file = tmp_path / ".env"
            assert env_file.exists(), (
                f"Expected .env at {env_file}. "
                f"Onboarding screen step: {screen.current_step if hasattr(screen, 'current_step') else 'unknown'}"
            )
            assert "GEMINI_API_KEY=test-api-key-999" in env_file.read_text()

            assert isinstance(app.screen, DashboardScreen)

@pytest.mark.asyncio
async def test_app_skips_onboarding_if_key_exists(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=existing-key")
    
    monkeypatch.setattr("src.core.paths.env_file", lambda: env_file)
    monkeypatch.setattr("src.core.paths.config_file", lambda: tmp_path / "config.yaml")
    
    app = YappyApp()
    async with app.run_test() as pilot:
        assert isinstance(app.screen, DashboardScreen)
