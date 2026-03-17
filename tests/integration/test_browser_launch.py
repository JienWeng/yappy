from unittest.mock import AsyncMock, patch

import pytest

from src.scraper.browser_factory import create_persistent_context


@pytest.mark.asyncio
async def test_browser_factory_respects_headless_true():
    # Patch WHERE it is used
    with patch("src.scraper.browser_factory.async_playwright") as mock_ap:
        mock_p = AsyncMock()
        mock_ap.return_value.__aenter__.return_value = mock_p

        mock_browser_type = AsyncMock()
        mock_p.chromium = mock_browser_type

        mock_context = AsyncMock()
        mock_browser_type.launch_persistent_context.return_value = mock_context

        async with create_persistent_context(
            user_data_dir="test_dir",
            headless=True
        ) as (p, context):
            pass

        args, kwargs = mock_browser_type.launch_persistent_context.call_args
        assert kwargs["headless"] is True

@pytest.mark.asyncio
async def test_browser_factory_respects_headless_false():
    with patch("src.scraper.browser_factory.async_playwright") as mock_ap:
        mock_p = AsyncMock()
        mock_ap.return_value.__aenter__.return_value = mock_p
        mock_browser_type = AsyncMock()
        mock_p.chromium = mock_browser_type
        mock_browser_type.launch_persistent_context.return_value = AsyncMock()

        async with create_persistent_context(
            user_data_dir="test_dir",
            headless=False
        ) as (p, context):
            pass

        args, kwargs = mock_browser_type.launch_persistent_context.call_args
        assert kwargs["headless"] is False
