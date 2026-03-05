"""Smoke tests for the TUI application."""
from __future__ import annotations

import pytest

from src.tui.app import YappyApp
from src.tui.screens.dashboard import DashboardScreen
from src.tui.widgets.header_bar import BotMode, HeaderBar
from src.tui.widgets.live_feed import LiveFeed
from src.tui.widgets.stats_panel import StatsPanel


class TestTUISmoke:
    @pytest.mark.asyncio
    async def test_app_starts_with_dashboard(self):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            assert isinstance(pilot.app.screen, DashboardScreen)
            screen = pilot.app.screen
            assert len(screen.query(StatsPanel)) == 1
            assert len(screen.query(LiveFeed)) == 1
            assert len(screen.query(HeaderBar)) == 1

    @pytest.mark.asyncio
    async def test_toggle_mode(self):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            header = pilot.app.screen.query_one(HeaderBar)
            assert header.mode == BotMode.AUTO
            await pilot.press("m")
            assert header.mode == BotMode.MANUAL
            await pilot.press("m")
            assert header.mode == BotMode.AUTO

    @pytest.mark.asyncio
    async def test_navigation_consistency(self):
        from src.tui.screens.config_editor import ConfigEditorScreen
        from src.tui.screens.activity_log import ActivityLogScreen

        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            # Dashboard to Config
            await pilot.press("c")
            assert isinstance(app.screen, ConfigEditorScreen)
            await pilot.press("escape")
            assert isinstance(app.screen, DashboardScreen)

            # Dashboard to Log
            await pilot.press("l")
            assert isinstance(app.screen, ActivityLogScreen)
            await pilot.press("escape")
            assert isinstance(app.screen, DashboardScreen)

            # Test 'q' on sub-screen (should also return to dashboard if configured that way, 
            # but we unified 'q' to 'Back' on sub-screens in Task 3)
            await pilot.press("c")
            await pilot.press("q")
            assert isinstance(app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_quit_consistency(self):
        app = YappyApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            # 'q' on dashboard should quit (but in run_test it might just close the pilot)
            # We just verify it doesn't crash
            await pilot.press("q")

