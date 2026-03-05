"""Smoke tests for the TUI application."""
from __future__ import annotations

import pytest

from src.tui.app import LinkedInAutoCommenterApp
from src.tui.screens.dashboard import DashboardScreen
from src.tui.widgets.header_bar import BotMode, HeaderBar
from src.tui.widgets.live_feed import LiveFeed
from src.tui.widgets.stats_panel import StatsPanel


class TestTUISmoke:
    @pytest.mark.asyncio
    async def test_app_starts_with_dashboard(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            assert isinstance(pilot.app.screen, DashboardScreen)
            screen = pilot.app.screen
            assert len(screen.query(StatsPanel)) == 1
            assert len(screen.query(LiveFeed)) == 1
            assert len(screen.query(HeaderBar)) == 1

    @pytest.mark.asyncio
    async def test_toggle_mode(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            header = pilot.app.screen.query_one(HeaderBar)
            assert header.mode == BotMode.AUTO
            await pilot.press("m")
            assert header.mode == BotMode.MANUAL
            await pilot.press("m")
            assert header.mode == BotMode.AUTO

    @pytest.mark.asyncio
    async def test_open_config_and_back(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.press("c")
            from src.tui.screens.config_editor import ConfigEditorScreen

            assert isinstance(pilot.app.screen, ConfigEditorScreen)
            await pilot.press("escape")
            assert isinstance(pilot.app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_open_log_and_back(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.press("l")
            from src.tui.screens.activity_log import ActivityLogScreen

            assert isinstance(pilot.app.screen, ActivityLogScreen)
            await pilot.press("escape")
            assert isinstance(pilot.app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_quit(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.press("q")
