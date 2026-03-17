from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import BrowserContext, Playwright, async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

STEALTH_BROWSER_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--start-maximized",
    "--no-first-run",
    "--disable-extensions",
)


@asynccontextmanager
async def create_persistent_context(
    user_data_dir: str,
    headless: bool = False,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
) -> AsyncGenerator[tuple[Playwright, BrowserContext], None]:
    """
    Async context manager that yields (playwright, context).

    Stealth is applied AFTER launch to avoid UA-sniff timing issues.
    Note: LinkedIn may detect headless browsers via GPU/font fingerprinting.
    If scraping fails in headless mode, switch to visible mode.
    """
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser_args = list(STEALTH_BROWSER_ARGS)
        if headless:
            # Remove flags that conflict with headless
            if "--start-maximized" in browser_args:
                browser_args.remove("--start-maximized")
            # Extra stealth args for headless to avoid detection
            browser_args.extend([
                "--disable-gpu",
                "--window-size=1920,1080",
            ])

        logger.info("Launching persistent browser context (headless=%s)", headless)

        context = await pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            args=browser_args,
            viewport={"width": viewport_width, "height": viewport_height},
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Apply stealth AFTER context creation (not before)
        await Stealth().apply_stealth_async(context)
        logger.info("Stealth applied to browser context")

        try:
            yield pw, context
        finally:
            await context.close()
            logger.info("Browser context closed")
