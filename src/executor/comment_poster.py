from __future__ import annotations

import logging
import random
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.executor.models import PostResult

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext
    from src.ai.models import GeneratedComment
    from src.executor.human_typer import HumanTyper
    from src.scraper.models import LinkedInPost

logger = logging.getLogger(__name__)

MAX_TYPING_ATTEMPTS = 3

# LinkedIn comment box — ql-editor is the Quill instance LinkedIn uses
# Ordered most-specific first; the first visible match is used for the initial click
COMMENT_BOX_SELECTOR = "div.ql-editor[contenteditable='true']"
COMMENT_BOX_SELECTOR_FALLBACKS = (
    "div.comments-comment-box__form div[contenteditable='true']",
    "div[contenteditable='true'][data-placeholder]",
    "div[contenteditable='true']",
)
# Submit button candidates — tried in order (confirmed via DOM diagnostics 2026-02-25)
COMMENT_SUBMIT_SELECTORS = (
    "button[class*='submit']",          # 1 visible match — most reliable
    "button:has-text('Post')",          # 2 visible — scoped by text
    "button.comments-comment-box__submit-button",
    "button.comments-comment-texteditor__submitButton",
    "button[type='submit']",
)
COMMENT_BUTTON_SELECTOR = (
    "button[aria-label*='comment' i]",
    "button.comment-button",
    "button[data-view-name='feed-full-update-comment-button']",
)
# Like button — match the unreacted state only (avoids accidentally un-liking)
LIKE_BUTTON_SELECTORS = (
    "button[aria-label='React Like']",
    "button[aria-label*='Like' i]:not([aria-label*='Unlike' i])",
    "button.reactions-react-button[aria-label*='Like' i]",
    "button[data-view-name='feed-full-update-like-button']",
)
WAIT_TIMEOUT_MS = 20_000


class CommentPoster:
    def __init__(self, context: "BrowserContext", human_typer: "HumanTyper") -> None:
        self._context = context
        self._typer = human_typer

    async def _read_comment_box(self, page: object, selector: str) -> str:
        """Return the current text content of the comment box (empty string on error)."""
        try:
            el = await page.query_selector(selector)
            if not el:
                return ""
            return (await el.inner_text()).strip()
        except Exception:
            return ""

    async def _clear_comment_box(self, page: object, selector: str) -> None:
        """Select all text in the comment box and delete it."""
        await page.click(selector)
        await page.wait_for_timeout(200)
        await page.keyboard.press("Control+a")
        await page.wait_for_timeout(100)
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(400)

    @staticmethod
    def _normalize(text: str) -> str:
        """Collapse whitespace for comparison — ignores invisible differences."""
        return re.sub(r"\s+", " ", text).strip()

    async def _type_and_verify(
        self, page: object, selector: str, expected: str
    ) -> None:
        """
        Type `expected` into the comment box and verify the box content matches.

        If the content doesn't match after typing, clear the box and retype.
        Repeats up to MAX_TYPING_ATTEMPTS times before raising RuntimeError.
        """
        expected_norm = self._normalize(expected)

        for attempt in range(1, MAX_TYPING_ATTEMPTS + 1):
            if attempt > 1:
                logger.info(
                    "Retype attempt %d/%d: clearing box and retyping",
                    attempt, MAX_TYPING_ATTEMPTS,
                )
                await self._clear_comment_box(page, selector)
                await page.wait_for_timeout(500)

            await self._typer.type_text(page, selector, expected)

            actual = await self._read_comment_box(page, selector)
            actual_norm = self._normalize(actual)

            if actual_norm == expected_norm:
                logger.info(
                    "Comment verified on attempt %d/%d (%d chars)",
                    attempt, MAX_TYPING_ATTEMPTS, len(expected),
                )
                return

            logger.warning(
                "Typing mismatch (attempt %d/%d): expected %d chars, got %d chars",
                attempt, MAX_TYPING_ATTEMPTS, len(expected_norm), len(actual_norm),
            )
            logger.debug("Expected: %r", expected_norm[:120])
            logger.debug("Actual:   %r", actual_norm[:120])

        raise RuntimeError(
            f"Comment text still mismatched after {MAX_TYPING_ATTEMPTS} attempts. "
            "Refusing to submit incomplete comment."
        )

    async def _resolve_comment_box(self, page: object) -> str | None:
        """Return the first comment box selector that is visible on the page."""
        all_selectors = (COMMENT_BOX_SELECTOR,) + COMMENT_BOX_SELECTOR_FALLBACKS
        for sel in all_selectors:
            try:
                await page.wait_for_selector(sel, timeout=5_000)
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.debug("Comment box resolved: %s", sel)
                    return sel
            except Exception:
                continue
        return None

    async def _like_post(self, page: object) -> bool:
        """Click the Like button if the post hasn't been liked yet. Returns True if liked."""
        for sel in LIKE_BUTTON_SELECTORS:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(random.uniform(800, 1500))
                    logger.debug("Post liked with selector: %s", sel)
                    return True
            except Exception as exc:
                logger.debug("Like attempt failed (%s): %s", sel, exc)
        logger.debug("Like button not found — skipping like")
        return False

    async def _log_submit_diagnostics(self, page: object) -> None:
        """Log all visible buttons to help identify the correct submit selector."""
        candidates = {
            "comments-comment-box__submit-button": "button.comments-comment-box__submit-button",
            "comments-comment-texteditor__submitButton": "button.comments-comment-texteditor__submitButton",
            "any button[type=submit]": "button[type='submit']",
            "any button with 'submit' in class": "button[class*='submit']",
            "any button with 'primary' in class": "button[class*='primary']",
            "any button with 'Post' text": "button:has-text('Post')",
            "any button with 'Comment' text": "button:has-text('Comment')",
        }
        logger.debug("--- SUBMIT BUTTON DIAGNOSTICS ---")
        for label, sel in candidates.items():
            try:
                els = await page.query_selector_all(sel)
                visible = [e for e in els if await e.is_visible()]
                if visible:
                    logger.info("  FOUND %d visible  [%s]  selector: %s", len(visible), label, sel)
                elif els:
                    logger.debug("  found %d hidden   [%s]", len(els), label)
            except Exception:
                pass
        logger.debug("---------------------------------")

    async def post_comment(
        self, post: "LinkedInPost", comment: "GeneratedComment"
    ) -> PostResult:
        page = await self._context.new_page()
        liked = False
        try:
            logger.info("Navigating to post: %s", post.post_url)
            await page.goto(post.post_url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(2000)

            # Simulate reading: scroll down through the post
            await page.evaluate("window.scrollBy(0, 400)")
            await page.wait_for_timeout(random.uniform(1500, 3000))
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(random.uniform(1000, 2000))

            # Like the post while "reading" — before opening the comment box
            liked = await self._like_post(page)
            if liked:
                logger.info("Liked post: %s", post.post_url)
                # Pause as a human would after reacting
                await page.wait_for_timeout(random.uniform(1000, 2500))

            # Click the "Comment" trigger button to open the comment box
            comment_btn = None
            for sel in (COMMENT_BUTTON_SELECTOR if isinstance(COMMENT_BUTTON_SELECTOR, tuple) else (COMMENT_BUTTON_SELECTOR,)):
                comment_btn = await page.query_selector(sel)
                if comment_btn and await comment_btn.is_visible():
                    logger.debug("Found visible comment button with selector: %s", sel)
                    break
            
            if comment_btn:
                await comment_btn.click()
                await page.wait_for_timeout(1500)
            else:
                logger.warning("No visible comment button found with any selector.")
                # Maybe it is already open? Let's try to resolve the box anyway

            # Resolve comment box — find the first selector that actually appears
            box_selector = await self._resolve_comment_box(page)
            if not box_selector:
                raise RuntimeError("Comment box did not appear after clicking.")

            # Type the comment and verify it matches the stored response.
            # Retypes from scratch (up to MAX_TYPING_ATTEMPTS) if the box content
            # doesn't exactly match what Gemini generated.
            await self._type_and_verify(page, box_selector, comment.text)

            # Pause to simulate reviewing before submitting (1–3 seconds)
            await page.wait_for_timeout(random.uniform(1000, 3000))

            # Give LinkedIn a moment to reveal the submit button after typing
            await page.wait_for_timeout(1500)

            # Diagnose what submit-like buttons exist right now
            await self._log_submit_diagnostics(page)

            # Try each submit selector in order
            submitted = False
            for sel in COMMENT_SUBMIT_SELECTORS:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    logger.debug("Clicking submit with selector: %s", sel)
                    await btn.click()
                    submitted = True
                    break

            if not submitted:
                # Fallback: keyboard shortcut (Ctrl+Enter / Cmd+Enter)
                logger.debug("No submit button found — using keyboard shortcut Ctrl+Enter")
                await page.keyboard.press("Control+Enter")

            await page.wait_for_timeout(2000)

            logger.info("Comment submitted on %s (liked=%s)", post.post_url, liked)
            return PostResult(
                success=True,
                post_url=post.post_url,
                comment_text=comment.text,
                posted_at=datetime.now(timezone.utc),
                error=None,
                liked=liked,
            )

        except Exception as exc:
            logger.error("Failed to post comment on %s: %s", post.post_url, exc)
            return PostResult(
                success=False,
                post_url=post.post_url,
                comment_text=comment.text,
                posted_at=datetime.now(timezone.utc),
                error=str(exc),
                liked=liked,
            )
        finally:
            await page.close()
