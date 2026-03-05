from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class HumanTyper:
    """
    Types text character-by-character at human-like WPM.

    Strategy:
    - Click the selector ONCE to establish focus.
    - Type every character via page.keyboard.type(char) with a single
      per-character delay (no double-delay, no re-querying the selector).
    - Occasionally insert a slightly longer pause between words to mimic
      the natural rhythm of lifting and replanting fingers.
    - Verify the full text landed in the element after finishing.
    """

    def __init__(self, min_wpm: int = 55, max_wpm: int = 80) -> None:
        self._min_wpm = min_wpm
        self._max_wpm = max_wpm

    async def type_text(self, page: "Page", selector: str, text: str) -> None:
        if not text:
            return

        wpm = random.uniform(self._min_wpm, self._max_wpm)
        # ms per character at this WPM: (60s / wpm) / 5 chars_per_word * 1000
        base_ms = (60.0 / wpm) / 5.0 * 1000.0
        logger.debug(
            "Typing %d chars at %.1f WPM (%.1fms base/char)",
            len(text), wpm, base_ms,
        )

        # Click once — hold focus for the entire typing sequence
        await page.click(selector)
        await page.wait_for_timeout(300)

        for i, char in enumerate(text):
            # Per-character jitter: ±30%
            delay = base_ms * random.uniform(0.70, 1.30)
            await page.keyboard.type(char, delay=delay)

            # After a space (word boundary) add a slightly longer pause ~20% of the time
            if char == " " and random.random() < 0.20:
                await page.wait_for_timeout(base_ms * random.uniform(1.5, 3.0))

        logger.debug("Finished typing")

        # Verify the text actually landed
        actual = await self._read_content(page, selector)
        if actual is not None and actual.strip() != text.strip():
            logger.warning(
                "Typing mismatch: expected %d chars, element has %d chars",
                len(text), len(actual),
            )
        else:
            logger.debug("Typing verified (%d chars)", len(text))

    async def _read_content(self, page: "Page", selector: str) -> str | None:
        try:
            el = await page.query_selector(selector)
            if not el:
                return None
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            if tag in ("input", "textarea"):
                return await el.input_value()
            return await el.inner_text()
        except Exception:
            return None
