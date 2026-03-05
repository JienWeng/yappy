"""
LinkedIn Auto-Commenter — Entry Point

First run: a browser window opens. Log into LinkedIn manually.
The session is saved to data/browser_profile/ and reused on subsequent runs.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.ai.comment_generator import CommentGenerator
from src.ai.gemini_client import GeminiClient
from src.core.config import load_config
from src.core.orchestrator import Orchestrator
from src.core.rate_limiter import DailyLimitExceededError, RateLimiter
from src.executor.comment_poster import CommentPoster
from src.executor.human_typer import HumanTyper
from src.scraper.browser_factory import create_persistent_context
from src.scraper.linkedin_scraper import LinkedInScraper
from src.storage.activity_log import ActivityLog

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/run.log"),
    ],
)
logger = logging.getLogger(__name__)


async def _ensure_logged_in(context: object) -> None:
    """Navigate to LinkedIn and pause if not logged in, waiting for the user."""
    page = await context.new_page()
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(2000)

        current_url = page.url
        # LinkedIn redirects to /login or /checkpoint when not authenticated
        if any(p in current_url for p in ("/login", "/checkpoint", "/authwall")):
            print("\n" + "=" * 60)
            print("  FIRST RUN: Please log into LinkedIn in the browser window.")
            print("  Once you're on the LinkedIn feed, come back here and")
            print("  press Enter to continue.")
            print("=" * 60 + "\n")
            await asyncio.get_event_loop().run_in_executor(None, input)
            # Brief pause to let the session cookies settle
            await page.wait_for_timeout(2000)
            logger.info("User confirmed login. Resuming.")
        else:
            logger.info("Session active — already logged in.")
    finally:
        await page.close()


async def main() -> None:
    config = load_config("config.yaml")
    logger.info("Config loaded. Targets: %d", len(config.targets))

    activity_log = ActivityLog(db_path=config.db_path)
    rate_limiter = RateLimiter(activity_log=activity_log, daily_limit=config.limits.daily_comment_limit)

    status = rate_limiter.check_status()
    logger.info(
        "Rate limit status: %d/%d comments used today (%d remaining)",
        status.comments_today,
        status.daily_limit,
        status.remaining,
    )

    if status.limit_reached:
        logger.warning("Daily comment limit already reached. Exiting.")
        return

    human_typer = HumanTyper(
        min_wpm=config.limits.min_wpm,
        max_wpm=config.limits.max_wpm,
    )
    gemini_client = GeminiClient(
        model_name=config.ai.model_name,
        temperature=config.ai.temperature,
        max_output_tokens=config.ai.max_output_tokens,
    )
    comment_generator = CommentGenerator(client=gemini_client, config=config.ai)

    async with create_persistent_context(
        user_data_dir=config.browser.user_data_dir,
        headless=config.browser.headless,
        viewport_width=config.browser.viewport_width,
        viewport_height=config.browser.viewport_height,
    ) as (_, context):
        await _ensure_logged_in(context)

        scraper = LinkedInScraper(
            context=context,
            activity_log=activity_log,
            min_reactions=config.limits.min_reactions,
            min_comments=config.limits.min_comments,
        )
        comment_poster = CommentPoster(context=context, human_typer=human_typer)

        orchestrator = Orchestrator(
            config=config,
            rate_limiter=rate_limiter,
            scraper=scraper,
            comment_generator=comment_generator,
            comment_poster=comment_poster,
            activity_log=activity_log,
        )

        logger.info("Starting pipeline...")
        result = await orchestrator.run()

    duration = (result.finished_at - result.started_at).total_seconds()
    logger.info(
        "Pipeline complete in %.1fs | scraped=%d | attempted=%d | succeeded=%d | failed=%d",
        duration,
        result.posts_scraped,
        result.comments_attempted,
        result.comments_succeeded,
        result.comments_failed,
    )

    if result.errors:
        logger.warning("%d error(s) occurred:", len(result.errors))
        for err in result.errors:
            logger.warning("  - %s", err)

    final_stats = activity_log.get_daily_stats()
    logger.info(
        "Today's totals: %d successful, %d failed",
        final_stats.successful,
        final_stats.failed,
    )


def show_report(db_path: str, limit: int = 50) -> None:
    from src.storage.activity_log import ActivityLog

    log = ActivityLog(db_path=db_path)
    records = log.get_recent(limit=limit)
    stats = log.get_daily_stats()

    if not records:
        print("No activity recorded yet.")
        return

    print(f"\n{'─' * 100}")
    print(f"  {'#':<5} {'STATUS':<10} {'TIME (UTC)':<26} {'POST URL':<52} COMMENT")
    print(f"{'─' * 100}")
    for r in records:
        status_icon = "✓" if r.status == "success" else "✗"
        time_str = r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        short_url = r.post_url.replace("https://www.linkedin.com/feed/update/", "").rstrip("/")
        short_url = (short_url[:48] + "..") if len(short_url) > 50 else short_url
        comment_preview = r.comment_text[:60].replace("\n", " ")
        if len(r.comment_text) > 60:
            comment_preview += ".."
        print(f"  {r.id:<5} {status_icon} {r.status:<8} {time_str:<26} {short_url:<52} {comment_preview}")
    print(f"{'─' * 100}")
    print(f"  Today: {stats.successful} succeeded, {stats.failed} failed  |  Total shown: {len(records)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Auto-Commenter")
    parser.add_argument(
        "--report", action="store_true", help="Show activity log and exit"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of records to show in report (default 50)"
    )
    parser.add_argument(
        "--no-tui", action="store_true", help="Run without TUI (original CLI mode)"
    )
    args = parser.parse_args()

    if args.report:
        from src.core.config import load_config
        cfg = load_config("config.yaml")
        show_report(db_path=cfg.db_path, limit=args.limit)
    elif args.no_tui:
        asyncio.run(main())
    else:
        from src.tui.app import LinkedInAutoCommenterApp
        app = LinkedInAutoCommenterApp()
        app.run()
