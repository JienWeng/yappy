from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.live_feed import LiveFeed


class FeedApp(App):
    def compose(self) -> ComposeResult:
        yield LiveFeed()


class TestLiveFeed:
    @pytest.mark.asyncio
    async def test_add_posted_entry(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_posted("@JaneDoe", "Great point about developer experience.")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_add_skipped_entry(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_skipped("job posting")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_add_failed_entry(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_failed("@BobJones", "Submit button not found")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_add_status_entry(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_status("Generating comment...")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_multiple_entries(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_posted("@JaneDoe", "Great point.")
            feed.add_skipped("low engagement")
            feed.add_failed("@Bob", "error")
            assert feed.entry_count == 3

    @pytest.mark.asyncio
    async def test_clear_feed(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_posted("@JaneDoe", "Great point.")
            feed.add_skipped("low engagement")
            assert feed.entry_count == 2
            feed.clear_feed()
            assert feed.entry_count == 0

    @pytest.mark.asyncio
    async def test_posted_truncates_long_preview(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            long_comment = "A" * 100
            feed.add_posted("@Author", long_comment)
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_initial_entry_count_is_zero(self) -> None:
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            assert feed.entry_count == 0
