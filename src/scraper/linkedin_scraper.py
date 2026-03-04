from __future__ import annotations

import logging
import time
import urllib.parse
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from playwright.async_api import BrowserContext, Page

from src.scraper.models import LinkedInPost, ScrapeResult

if TYPE_CHECKING:
    from src.core.config import TargetConfig
    from src.storage.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def _parse_count(text: str) -> int | None:
    """Parse a reaction count string like '1,234', '1.2K', '23 reactions' → int."""
    import re
    text = text.strip().lower()
    # Extract the first number-like token
    m = re.search(r"([\d,]+\.?\d*)\s*([km])?", text)
    if not m:
        return None
    num_str = m.group(1).replace(",", "")
    try:
        value = float(num_str)
    except ValueError:
        return None
    suffix = m.group(2) or ""
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return int(value)

# CSS selectors — confirmed working via DOM diagnostics 2026-02-25
POST_CONTAINER_SELECTOR = "div.feed-shared-update-v2"

# Text: try most-specific first, fall back to any break-words span
POST_TEXT_SELECTORS = (
    "div.feed-shared-update-v2__description span.break-words",
    "div.feed-shared-update-v2__description",
    "div[class*='commentary'] span.break-words",
    "div[class*='commentary']",
    "span.break-words",
)

AUTHOR_NAME_SELECTORS = (
    "span.feed-shared-actor__name span[aria-hidden='true']",
    "span.feed-shared-actor__name",
    "a.app-aware-link span[aria-hidden='true']",
    "span[class*='actor__name']",
)

AUTHOR_URL_SELECTORS = (
    "a.feed-shared-actor__meta-link",
    "a.app-aware-link[href*='/in/']",
)

LINKEDIN_SEARCH_URL = (
    "https://www.linkedin.com/search/results/content/"
    "?keywords={keywords}&datePosted=past-{hours}h&sortBy=date"
)
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_CONNECTIONS_URL = "https://www.linkedin.com/feed/"
WAIT_TIMEOUT_MS = 15_000

# Reaction count selectors — try most specific first
REACTION_COUNT_SELECTORS = (
    "span.social-details-social-counts__reactions-count",
    "button.social-details-social-counts__count-value",
    "span[aria-label*='reaction' i]",
    "li.social-details-social-counts__item button",
)

# Comment count selectors
COMMENT_COUNT_SELECTORS = (
    "button[aria-label*='comment' i]",
    "span.social-details-social-counts__comments",
    "li.social-details-social-counts__item--right-aligned button",
    "button.social-details-social-counts__count-value[aria-label*='comment' i]",
)

# Job post signals — if any appear in the text the post is skipped
JOB_POST_SIGNALS = (
    "we're hiring", "we are hiring", "is hiring", "now hiring",
    "job opening", "job opportunity", "open role", "open position",
    "apply now", "apply here", "applications open", "applications are open",
    "join our team", "looking to hire", "looking for a",
    "#hiring", "#nowhiring", "#jobs", "#jobopening", "#careers",
    "full-time", "part-time", "remote role", "hybrid role",
    "salary range", "compensation package",
    "send your cv", "send your resume", "dm me your cv",
)


class LinkedInScraper:
    def __init__(
        self,
        context: BrowserContext,
        activity_log: "ActivityLog",
        min_reactions: int = 5,
        min_comments: int = 2,
    ) -> None:
        self._context = context
        self._log = activity_log
        self._min_reactions = min_reactions
        self._min_comments = min_comments

    async def scrape_target(self, target: "TargetConfig") -> ScrapeResult:
        started = time.monotonic()
        page = await self._context.new_page()
        try:
            posts = await self._scrape(page, target)
            return ScrapeResult(
                target_value=target.value,
                posts=tuple(posts),
                error=None,
                duration_seconds=time.monotonic() - started,
            )
        except Exception as exc:
            logger.error("Scrape error for target %r: %s", target.value, exc)
            return ScrapeResult(
                target_value=target.value,
                posts=(),
                error=str(exc),
                duration_seconds=time.monotonic() - started,
            )
        finally:
            await page.close()

    async def _scrape(self, page: Page, target: "TargetConfig") -> list[LinkedInPost]:
        if target.type == "feed":
            url = LINKEDIN_FEED_URL
        elif target.type == "connections":
            url = LINKEDIN_CONNECTIONS_URL
        elif target.type == "url":
            url = target.value
        else:  # keyword
            encoded = urllib.parse.quote_plus(target.value)
            url = LINKEDIN_SEARCH_URL.format(
                keywords=encoded,
                hours=target.recency_hours,
            )
        load_strategy = "load" if target.type in ("feed", "connections") else "domcontentloaded"
        await page.goto(url, wait_until=load_strategy, timeout=WAIT_TIMEOUT_MS)

        logger.info("Page loaded: %s  title=%r", page.url, await page.title())

        # Give LinkedIn's XHR feed API a chance to respond
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass  # networkidle may never settle on an SPA — that's fine

        await self._wait_for_feed_ready(page)
        await self._scroll_to_load_posts(page, target_count=target.max_posts * 2)

        await self._log_dom_diagnostics(page)
        return await self._extract_posts_from_page(page, target)

    async def _wait_for_feed_ready(self, page: Page) -> None:
        """Block until LinkedIn renders at least one post container, or fall through on timeout."""
        wait_selectors = (
            POST_CONTAINER_SELECTOR,                    # search results (old design)
            "[data-view-name='feed-full-update']",      # home feed (new design)
            "div[data-urn*='activity']",
            "div.scaffold-finite-scroll__content",
            "div.core-rail",
            "main",
        )
        for sel in wait_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8_000)
                logger.debug("Feed ready — found element: %r", sel)
                return
            except Exception:
                continue
        logger.warning("Feed ready timeout on all selectors — proceeding anyway")

    async def _scroll_to_load_posts(self, page: Page, target_count: int) -> None:
        """Scroll in passes until we have target_count containers or exhaust 5 passes."""
        for pass_num in range(1, 6):
            old_containers = await page.query_selector_all(POST_CONTAINER_SELECTOR)
            new_containers = await page.query_selector_all("[data-view-name='feed-full-update']")
            total = len(old_containers) + len(new_containers)
            logger.debug(
                "Scroll pass %d: %d containers found (need %d) [old=%d new=%d]",
                pass_num, total, target_count, len(old_containers), len(new_containers),
            )
            if total >= target_count:
                return
            await page.evaluate("window.scrollBy(0, 1200)")
            await page.wait_for_timeout(2000)

    async def _log_dom_diagnostics(self, page: Page) -> None:
        """Log counts for candidate selectors to help identify the right ones."""
        # Save screenshot so we can see what the browser is actually rendering
        import os, time as _time
        screenshot_path = f"/tmp/linkedin_debug_{int(_time.time())}.png"
        try:
            await page.screenshot(path=screenshot_path, full_page=False)
            logger.info("Screenshot saved: %s", screenshot_path)
        except Exception as exc:
            logger.debug("Screenshot failed: %s", exc)

        # Dump first child tag names of <main> and try deep shadow-DOM search
        try:
            main_children = await page.evaluate(
                "() => Array.from(document.querySelector('main')?.children ?? []).map(el => el.tagName + (el.className ? '.' + el.className.split(' ')[0] : ''))"
            )
            logger.info("main> children: %s", main_children[:10])
        except Exception:
            pass

        # Deep shadow-DOM traversal to find data-urn anywhere in the tree
        try:
            deep_counts = await page.evaluate("""() => {
                function deepQuery(root, sel) {
                    let found = [...(root.querySelectorAll(sel) || [])];
                    for (const el of root.querySelectorAll('*')) {
                        if (el.shadowRoot) found.push(...deepQuery(el.shadowRoot, sel));
                    }
                    return found;
                }
                const byUrn = deepQuery(document, 'div[data-urn]').length;
                const byActivity = deepQuery(document, '[data-urn*="activity"]').length;
                const byCard = deepQuery(document, '[class*="fie-impression"]').length;
                const allLi = deepQuery(document, 'li').length;
                const allArticle = deepQuery(document, 'article').length;
                return {byUrn, byActivity, byCard, allLi, allArticle};
            }""")
            logger.info("Deep shadow-DOM counts: %s", deep_counts)
        except Exception as exc:
            logger.debug("Deep query failed: %s", exc)

        # Dump main innerHTML to file for inspection
        try:
            html = await page.evaluate("() => document.querySelector('main')?.innerHTML ?? ''")
            dump_path = f"/tmp/linkedin_main_{int(_time.time())}.html"
            with open(dump_path, "w") as f:
                f.write(html)  # full dump, no cap
            logger.info("Main HTML dumped: %s (%d chars)", dump_path, len(html))
        except Exception as exc:
            logger.debug("HTML dump failed: %s", exc)

        # Live JS probe: inspect new-format feed-full-update containers
        try:
            new_feed_sample = await page.evaluate("""() => {
                const containers = document.querySelectorAll('[data-view-name="feed-full-update"]');
                return Array.from(containers).slice(0, 3).map(c => {
                    const allLinks = Array.from(c.querySelectorAll('a[href]')).map(a => ({
                        href: a.href,
                        text: a.textContent.trim().slice(0, 40),
                        ariaLabel: a.getAttribute('aria-label')
                    }));
                    const headerText = c.querySelector('[data-view-name="feed-header-text"]');
                    const controlMenu = c.querySelector('[data-view-name="feed-control-menu"]');
                    const commentary = c.querySelector('[data-view-name="feed-commentary"]');
                    const reactEl = c.querySelector('[data-view-name="feed-reaction-count"]');
                    // Timestamp links
                    const timeEls = Array.from(c.querySelectorAll('time')).map(t => ({
                        text: t.textContent.trim(),
                        parentHref: t.closest('a')?.href
                    }));
                    // Buttons with aria-labels in action area
                    const actionBtns = Array.from(c.querySelectorAll('button[aria-label]')).map(b => b.getAttribute('aria-label')).filter(Boolean);
                    // componentkey on root
                    const rootKey = c.getAttribute('componentkey') || c.closest('[componentkey]')?.getAttribute('componentkey');
                    return {
                        rootKey,
                        allLinks: allLinks.slice(0, 10),
                        authorName: headerText ? headerText.querySelector('strong')?.textContent : null,
                        controlMenuAriaLabel: controlMenu ? controlMenu.getAttribute('aria-label') : null,
                        postText: commentary ? commentary.textContent.slice(0, 80) : null,
                        timeEls,
                        actionBtns: actionBtns.slice(0, 10),
                        reactText: reactEl ? reactEl.textContent.trim().slice(0, 50) : null,
                    };
                });
            }""")
            for i, s in enumerate(new_feed_sample):
                logger.info("New-feed post[%d]: author=%r ctrl=%r text=%r", i, s.get('authorName'), s.get('controlMenuAriaLabel'), s.get('postText'))
                logger.info("  times=%s  actionBtns=%s", s.get('timeEls'), s.get('actionBtns'))
                logger.info("  links=%s", [l['href'] for l in s.get('allLinks', [])])
                logger.info("  rootKey=%r  reactText=%r", s.get('rootKey'), s.get('reactText'))
        except Exception as exc:
            logger.debug("New-feed JS probe failed: %s", exc)

        candidates = {
            "data-urn=activity (container)": "div[data-urn*='activity']",
            "feed-shared-update-v2": "div.feed-shared-update-v2",
            "occludable-update": "div.occludable-update",
            "reusable-search result li": "li.reusable-search__result-container",
            "search-result__occluded-item": "li.search-result__occluded-item",
            "entity-result": "div.entity-result",
            "update-components-actor": "div.update-components-actor",
            "scaffold-finite-scroll__content": "div.scaffold-finite-scroll__content",
            "any article": "article",
            "data-id attr": "[data-id]",
            "div[data-urn] (any)": "div[data-urn]",
            "fie-impression-container": "div.fie-impression-container",
            "artdeco-card": "div.artdeco-card",
            "core-rail": "div.core-rail",
            "main": "main",
        }
        logger.info("--- DOM DIAGNOSTICS ---")
        for label, sel in candidates.items():
            els = await page.query_selector_all(sel)
            if els:
                logger.info("  FOUND %3d  [%s]  selector: %s", len(els), label, sel)
            else:
                logger.debug("  none       [%s]", label)
        logger.info("-----------------------")

    async def _extract_posts_from_page(
        self, page: Page, target: "TargetConfig"
    ) -> list[LinkedInPost]:
        posts: list[LinkedInPost] = []
        containers = await page.query_selector_all(POST_CONTAINER_SELECTOR)
        logger.debug("Found %d containers with selector %r", len(containers), POST_CONTAINER_SELECTOR)

        for container in containers[: target.max_posts * 2]:  # over-fetch, filter dupes
            if len(posts) >= target.max_posts:
                break
            try:
                post = await self._parse_post_container(container, page, target.value)
                if post is None:
                    continue
                if self._already_commented(post.post_url):
                    logger.debug("Skipping already-commented post: %s", post.post_url)
                    continue
                if self._is_company_post(post.author_profile_url):
                    logger.debug("Skipping company post: %s", post.post_url)
                    continue
                if self._is_job_post(post.post_text):
                    logger.debug("Skipping job post: %s", post.post_url)
                    continue
                if self._is_media_only_post(post.post_text):
                    logger.debug("Skipping media-only post (no real text): %s", post.post_url)
                    continue
                if post.reaction_count < self._min_reactions:
                    logger.debug(
                        "Skipping low-reaction post (%d < %d): %s",
                        post.reaction_count, self._min_reactions, post.post_url,
                    )
                    continue
                if post.comment_count < self._min_comments:
                    logger.debug(
                        "Skipping low-comment post (%d < %d): %s",
                        post.comment_count, self._min_comments, post.post_url,
                    )
                    continue
                logger.info(
                    "Accepted post: reactions=%d comments=%d author=%r",
                    post.reaction_count, post.comment_count, post.author_name,
                )
                posts.append(post)
            except Exception as exc:
                logger.warning("Failed to parse post container: %s", exc)
                continue

        return posts

    async def _parse_post_container(
        self, container: object, page: Page, source_target: str
    ) -> LinkedInPost | None:
        # --- Post URL: prefer data-urn on the container itself ---
        data_urn = await container.get_attribute("data-urn")
        post_url: str | None = None
        if data_urn and "activity" in data_urn:
            post_url = f"https://www.linkedin.com/feed/update/{data_urn}/"
        else:
            # Fallback: find the first anchor pointing to /feed/update/ or /posts/
            link_el = await container.query_selector(
                "a[href*='/feed/update/'], a[href*='/posts/']"
            )
            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    post_url = href.split("?")[0]

        if not post_url:
            logger.debug("Container skipped: no post URL (data-urn=%r)", data_urn)
            return None

        # --- Post text: try selectors in order ---
        post_text = ""
        for sel in POST_TEXT_SELECTORS:
            el = await container.query_selector(sel)
            if el:
                post_text = (await el.inner_text()).strip()
                if post_text:
                    break

        if not post_text:
            logger.debug("Container skipped: no post text (url=%s)", post_url)
            return None

        # --- Author name ---
        author_name = ""
        for sel in AUTHOR_NAME_SELECTORS:
            el = await container.query_selector(sel)
            if el:
                author_name = (await el.inner_text()).strip()
                if author_name:
                    break

        # --- Author URL ---
        author_url = ""
        for sel in AUTHOR_URL_SELECTORS:
            el = await container.query_selector(sel)
            if el:
                href = await el.get_attribute("href")
                if href:
                    author_url = href.split("?")[0]
                    break

        # --- Reaction & comment counts ---
        reaction_count = await self._extract_reaction_count(container)
        comment_count = await self._extract_comment_count(container)

        logger.debug(
            "Parsed post: reactions=%d comments=%d author=%r text_len=%d",
            reaction_count, comment_count, author_name, len(post_text),
        )
        return LinkedInPost(
            post_url=post_url,
            author_name=author_name,
            author_profile_url=author_url,
            post_text=post_text[:2000],
            scraped_at=datetime.now(timezone.utc),
            source_target=source_target,
            reaction_count=reaction_count,
            comment_count=comment_count,
        )

    async def _extract_reaction_count(self, container: object) -> int:
        """Extract the numeric reaction count from a post container."""
        for sel in REACTION_COUNT_SELECTORS:
            el = await container.query_selector(sel)
            if not el:
                continue
            # Try aria-label first (e.g. "1,234 reactions")
            aria = await el.get_attribute("aria-label") or ""
            count = _parse_count(aria)
            if count is not None:
                return count
            # Fall back to visible text ("1,234" or "1.2K")
            text = (await el.inner_text()).strip()
            count = _parse_count(text)
            if count is not None:
                return count
        return 0

    async def _extract_comment_count(self, container: object) -> int:
        """Extract the numeric comment count from a post container."""
        for sel in COMMENT_COUNT_SELECTORS:
            el = await container.query_selector(sel)
            if not el:
                continue
            aria = await el.get_attribute("aria-label") or ""
            count = _parse_count(aria)
            if count is not None:
                return count
            text = (await el.inner_text()).strip()
            count = _parse_count(text)
            if count is not None:
                return count
        return 0

    async def fetch_comments(self, post_url: str, limit: int = 4) -> list[str]:
        """
        Navigate to the post page and return up to `limit` existing comment texts.
        Returns an empty list if the page fails or no comments are found.
        """
        page = await self._context.new_page()
        try:
            await page.goto(post_url, wait_until="domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(2500)

            # Selectors for comment text — tried in priority order
            comment_selectors = (
                "span.comments-comment-item__main-content",
                "div.comments-comment-item__content span.break-words",
                "article.comments-comment-item span.break-words",
                "div[class*='comment-item'] span.break-words",
            )

            comments: list[str] = []
            for sel in comment_selectors:
                els = await page.query_selector_all(sel)
                for el in els[:limit * 2]:  # over-fetch, dedupe below
                    text = (await el.inner_text()).strip()
                    if text and text not in comments:
                        comments.append(text)
                    if len(comments) >= limit:
                        break
                if comments:
                    break

            logger.debug("Fetched %d existing comments from %s", len(comments), post_url)
            return comments[:limit]
        except Exception as exc:
            logger.debug("Could not fetch comments for %s: %s", post_url, exc)
            return []
        finally:
            await page.close()

    def _is_company_post(self, author_profile_url: str) -> bool:
        """Return True if the post is from a LinkedIn Company Page, not a person."""
        return "/company/" in author_profile_url or "/school/" in author_profile_url

    def _is_media_only_post(self, text: str) -> bool:
        """Return True if the post has too little original text to comment on meaningfully."""
        # Strip common link/video placeholder words
        stripped = text.strip()
        return len(stripped) < 80

    def _is_job_post(self, text: str) -> bool:
        text_lower = text.lower()
        return any(signal in text_lower for signal in JOB_POST_SIGNALS)

    def _already_commented(self, post_url: str) -> bool:
        return self._log.was_commented(post_url)
