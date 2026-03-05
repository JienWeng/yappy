"""Yappy CLI — single entry point for the `yap` command."""
from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from src.core import paths


def _setup_logging() -> None:
    """Configure logging to file and stdout."""
    paths.ensure_dirs()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(paths.log_file())),
        ],
    )


def _ensure_playwright_browser() -> None:
    """Install Playwright Chromium if not already present."""
    # Quick check: if the chromium executable exists, skip
    try:
        from playwright._impl._driver import compute_driver_executable

        driver = compute_driver_executable()
        result = subprocess.run(
            [str(driver), "install", "--dry-run", "chromium"],
            capture_output=True,
            text=True,
        )
        # If dry-run shows nothing to install, we're good
        if result.returncode == 0 and "chromium" not in result.stdout.lower():
            return
    except Exception:
        pass

    print("Installing Playwright Chromium browser (first run only)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )
        print("Browser installed successfully.")
    except subprocess.CalledProcessError as exc:
        print(f"Failed to install Playwright browser: {exc}", file=sys.stderr)
        print("Try running manually: python -m playwright install chromium", file=sys.stderr)
        sys.exit(1)


def _ensure_config() -> None:
    """Create default config and .env if they don't exist."""
    paths.ensure_dirs()

    config_file = paths.config_file()
    if not config_file.exists():
        config_file.write_text(paths.DEFAULT_CONFIG_YAML)
        print(f"Created default config at {config_file}")

    env_file = paths.env_file()
    if not env_file.exists():
        env_file.write_text("# Add your Gemini API key here\n# GEMINI_API_KEY=your-key\n")
        print(f"Created .env template at {env_file}")


def _show_report(limit: int = 50) -> None:
    """Display the activity report."""
    from src.core.config import load_config
    from src.storage.activity_log import ActivityLog

    config = load_config()
    log = ActivityLog(db_path=config.db_path)
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


async def _run_headless() -> None:
    """Run the bot in headless CLI mode (no TUI)."""
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

    logger = logging.getLogger(__name__)

    config = load_config()
    if not config.gemini_api_key:
        print("\n" + "!" * 60)
        print("  ERROR: GEMINI_API_KEY is missing.")
        print("  Please run `yap onboarding` or set the key in ~/.config/yappy/.env")
        print("!" * 60 + "\n")
        return

    logger.info("Config loaded. Targets: %d", len(config.targets))

    activity_log = ActivityLog(db_path=config.db_path)
    rate_limiter = RateLimiter(
        activity_log=activity_log,
        daily_limit=config.limits.daily_comment_limit,
    )

    status = rate_limiter.check_status()
    logger.info(
        "Rate limit status: %d/%d comments used today (%d remaining)",
        status.comments_today, status.daily_limit, status.remaining,
    )

    if status.limit_reached:
        logger.warning("Daily comment limit already reached. Exiting.")
        return

    human_typer = HumanTyper(
        min_wpm=config.limits.min_wpm, max_wpm=config.limits.max_wpm,
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
        # Ensure logged in
        page = await context.new_page()
        try:
            await page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded", timeout=20_000,
            )
            await page.wait_for_timeout(2000)
            current_url = page.url
            if any(p in current_url for p in ("/login", "/checkpoint", "/authwall")):
                print("\n" + "=" * 60)
                print("  FIRST RUN: Please log into LinkedIn in the browser window.")
                print("  Once you're on the LinkedIn feed, press Enter to continue.")
                print("=" * 60 + "\n")
                await asyncio.get_event_loop().run_in_executor(None, input)
                await page.wait_for_timeout(2000)
                logger.info("User confirmed login. Resuming.")
            else:
                logger.info("Session active — already logged in.")
        finally:
            await page.close()

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
        duration, result.posts_scraped, result.comments_attempted,
        result.comments_succeeded, result.comments_failed,
    )

    if result.errors:
        logger.warning("%d error(s) occurred:", len(result.errors))
        for err in result.errors:
            logger.warning("  - %s", err)

    final_stats = activity_log.get_daily_stats()
    logger.info(
        "Today's totals: %d successful, %d failed",
        final_stats.successful, final_stats.failed,
    )


def _show_about() -> None:
    """Display the Ubuntu-style 'About Yappy' splash screen."""
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    import platform

    console = Console()

    # Catppuccin Macchiato Colors
    SAPPHIRE = "#8aadf4"
    MAUVE = "#c6a0f6"
    SKY = "#91d7e3"
    TEXT = "#cad3f5"

    # FIGlet 'Slant' Logo
    figlet_logo = f"""
[bold {MAUVE}] __  __                       [/]
[bold {MAUVE}] \\ \\/ /___ _____  ____  __  __[/]
[bold {MAUVE}]  \\  / __ `/ __ \\/ __ \\/ / / /[/]
[bold {MAUVE}]  / / /_/ / /_/ / /_/ / /_/ / [/]
[bold {MAUVE}] /_/\\__,_/ .___/ .___/\\__, /  [/]
[bold {MAUVE}]        /_/   /_/    /____/   [/]
    """

    # Project Info
    info_text = Text.assemble(
        (f"Yappy Assistant\n", f"bold {SAPPHIRE}"),
        (f"{'─' * 20}\n", f"{SKY}"),
        (f"Version: ", f"bold {TEXT}"), (f"0.1.0\n", f"{TEXT}"),
        (f"OS:      ", f"bold {TEXT}"), (f"{platform.system()} {platform.release()}\n", f"{TEXT}"),
        (f"Python:  ", f"bold {TEXT}"), (f"{platform.python_version()}\n", f"{TEXT}"),
        (f"Author:  ", f"bold {TEXT}"), (f"Jien Weng\n", f"{TEXT}"),
        (f"GitHub:  ", f"bold {TEXT}"), (f"github.com/jienweng/yappy\n", f"{SKY} underline"),
        (f"{'─' * 20}\n", f"{SKY}"),
        (f"Status:   ", f"bold {TEXT}"), (f"Open Source (MIT)\n", f"{TEXT}"),
    )

    # Layout using Columns
    columns = Columns([figlet_logo, info_text])
    console.print("\n")
    console.print(Panel(columns, border_style=SAPPHIRE, expand=False, padding=(1, 4)))
    console.print("\n")


def _handle_schedule(args: argparse.Namespace) -> None:
    """Handle the schedule subcommand."""
    from src.core import scheduler

    if args.clear:
        print(scheduler.clear_schedules())
    elif args.list:
        print(scheduler.list_schedules())
    elif args.daily:
        print(scheduler.register_daily_run(args.daily))
    else:
        print("Usage: yap schedule --daily HH:MM | --list | --clear")


def main() -> None:
    """Entry point for the `yap` command."""
    parser = argparse.ArgumentParser(
        prog="yap",
        description="Yappy — AI-powered LinkedIn engagement assistant",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Root flags (for backward compatibility and quick access)
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show activity log and exit",
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Show about screen and exit",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of records to show in report (default 50)",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Run without TUI (headless CLI mode)",
    )

    # Schedule subcommand
    sched_parser = subparsers.add_parser(
        "schedule", help="Manage background task schedules"
    )
    sched_parser.add_argument(
        "--daily",
        metavar="HH:MM",
        help="Schedule a daily run at specified time",
    )
    sched_parser.add_argument(
        "--list", action="store_true", help="List current active schedules"
    )
    sched_parser.add_argument(
        "--clear", action="store_true", help="Remove all active schedules"
    )

    # Onboarding subcommand
    subparsers.add_parser(
        "onboarding", help="Run the onboarding wizard manually"
    )

    args = parser.parse_args()

    # First-run setup
    _ensure_config()
    _ensure_playwright_browser()

    if args.command == "schedule":
        _handle_schedule(args)
    elif args.command == "onboarding":
        from src.tui.app import YappyApp

        app = YappyApp(skip_onboarding=False)
        app.run()
    elif args.report:
        _show_report(limit=args.limit)
    elif args.about:
        _show_about()
    elif args.no_tui:
        _setup_logging()
        asyncio.run(_run_headless())
    else:
        from src.tui.app import YappyApp

        app = YappyApp()
        app.run()


if __name__ == "__main__":
    main()
