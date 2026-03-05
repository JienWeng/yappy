"""Tests for the main TUI App."""
from __future__ import annotations

import pytest

from src.tui.app import YappyApp
from src.tui.screens.dashboard import DashboardScreen


class TestApp:
    @pytest.mark.asyncio
    async def test_app_launches(self):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            assert pilot.app is not None

    @pytest.mark.asyncio
    async def test_app_shows_dashboard_when_skipping_onboarding(self):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            assert isinstance(pilot.app.screen, DashboardScreen)
