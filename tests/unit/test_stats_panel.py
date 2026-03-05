"""Tests for the StatsPanel widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.stats_panel import StatsPanel


class StatsApp(App):
    def compose(self) -> ComposeResult:
        yield StatsPanel()


class TestStatsPanelInitialState:
    @pytest.mark.asyncio
    async def test_initial_reactive_values_are_defaults(self) -> None:
        async with StatsApp().run_test() as pilot:
            panel = pilot.app.query_one(StatsPanel)
            assert panel.comments_today == 0
            assert panel.daily_limit == 20
            assert panel.posts_scanned == 0
            assert panel.posts_skipped == 0
            assert panel.success_count == 0
            assert panel.fail_count == 0


class TestStatsPanelUpdateStats:
    @pytest.mark.asyncio
    async def test_update_stats_sets_reactive_values(self) -> None:
        async with StatsApp().run_test() as pilot:
            panel = pilot.app.query_one(StatsPanel)
            panel.update_stats(
                comments_today=7,
                daily_limit=20,
                posts_scanned=42,
                posts_skipped=35,
                success_count=6,
                fail_count=1,
            )
            assert panel.comments_today == 7
            assert panel.daily_limit == 20
            assert panel.posts_scanned == 42
            assert panel.posts_skipped == 35
            assert panel.success_count == 6
            assert panel.fail_count == 1
