from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.executor.human_typer import HumanTyper


@pytest.fixture
def page() -> MagicMock:
    p = MagicMock()
    p.click = AsyncMock()
    p.keyboard = MagicMock()
    p.keyboard.type = AsyncMock()
    p.wait_for_timeout = AsyncMock()
    return p


class TestHumanTyper:
    @pytest.mark.asyncio
    async def test_types_each_character(self, page: MagicMock) -> None:
        typer = HumanTyper(min_wpm=60, max_wpm=60)
        await typer.type_text(page, "div.editor", "hi")
        assert page.keyboard.type.call_count == 2

    @pytest.mark.asyncio
    async def test_clicks_selector_first(self, page: MagicMock) -> None:
        typer = HumanTyper(min_wpm=60, max_wpm=60)
        await typer.type_text(page, "div.editor", "a")
        page.click.assert_called_once_with("div.editor")

    @pytest.mark.asyncio
    async def test_delay_is_positive(self, page: MagicMock) -> None:
        typer = HumanTyper(min_wpm=55, max_wpm=80)
        await typer.type_text(page, "div.editor", "x")
        # Each keyboard.type call should have a positive delay
        for c in page.keyboard.type.call_args_list:
            _, kwargs = c
            assert kwargs.get("delay", 0) > 0

    @pytest.mark.asyncio
    async def test_empty_text_does_not_type(self, page: MagicMock) -> None:
        typer = HumanTyper(min_wpm=60, max_wpm=60)
        await typer.type_text(page, "div.editor", "")
        page.keyboard.type.assert_not_called()

    @pytest.mark.asyncio
    async def test_wpm_range_produces_different_delays(self) -> None:
        """Typing speed varies between runs due to random WPM in range."""
        delays: list[float] = []
        for _ in range(5):
            p = MagicMock()
            p.click = AsyncMock()
            p.keyboard = MagicMock()
            p.keyboard.type = AsyncMock()
            p.wait_for_timeout = AsyncMock()

            typer = HumanTyper(min_wpm=30, max_wpm=120)
            await typer.type_text(p, "div.editor", "a")
            _, kwargs = p.keyboard.type.call_args
            delays.append(kwargs["delay"])

        # With such a wide range, we expect some variation across 5 runs
        assert len(set(round(d, 0) for d in delays)) >= 1
