"""Tests for the HeaderBar widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.header_bar import HeaderBar, BotMode


class HeaderApp(App):
    def compose(self) -> ComposeResult:
        yield HeaderBar()


class TestHeaderBar:
    @pytest.mark.asyncio
    async def test_initial_mode_is_auto(self):
        async with HeaderApp().run_test() as pilot:
            header = pilot.app.query_one(HeaderBar)
            assert header.mode == BotMode.AUTO

    @pytest.mark.asyncio
    async def test_toggle_mode(self):
        async with HeaderApp().run_test() as pilot:
            header = pilot.app.query_one(HeaderBar)
            header.toggle_mode()
            assert header.mode == BotMode.MANUAL
            header.toggle_mode()
            assert header.mode == BotMode.AUTO


class TestBotMode:
    def test_auto_value(self):
        assert BotMode.AUTO == "auto"

    def test_manual_value(self):
        assert BotMode.MANUAL == "manual"
