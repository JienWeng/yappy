"""Main Textual application for Yappy."""
from __future__ import annotations

import asyncio as aio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import App

from src.tui.screens.activity_log import ActivityLogScreen
from src.tui.screens.config_editor import ConfigEditorScreen
from src.tui.screens.dashboard import DashboardScreen
from src.tui.screens.onboarding import OnboardingScreen
from src.tui.widgets.comment_review import ReviewDecision
from src.tui.events import BotPaused, BotStatus
from src.tui.workers.bot_worker import BotWorkerCallbacks

if TYPE_CHECKING:
    from src.tui.widgets.header_bar import BotMode

logger = logging.getLogger(__name__)


class YappyApp(App):
    """Yappy TUI Application."""

    TITLE = "Yappy"

    SUB_TITLE = "AI-powered LinkedIn engagement"

    CSS = """
    Screen {
        background: #1e2030;
        color: #cad3f5;
    }
    
    /* Catppuccin Macchiato Palette */
    $sapphire: #8aadf4;
    $mauve: #c6a0f6;
    $sky: #91d7e3;
    $peach: #f5a97f;
    $green: #a6da95;
    $red: #ed8796;
    $surface: #363a4f;
    $text: #cad3f5;
    """

    def __init__(
        self, skip_onboarding: bool = False, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._skip_onboarding = skip_onboarding
        self._worker_callbacks: BotWorkerCallbacks | None = None

    def on_mount(self) -> None:
        if self._skip_onboarding or self._onboarding_complete():
            self.push_screen(DashboardScreen())
        else:
            self.push_screen(OnboardingScreen())

    def _onboarding_complete(self) -> bool:
        """Check if onboarding has been completed by verifying the GEMINI_API_KEY."""
        from src.core import paths
        import os

        # Check environment first (may already be set by user)
        if os.environ.get("GEMINI_API_KEY"):
            return True

        # Check .env files
        env_paths = [paths.env_file(), Path(".env")]
        for path in env_paths:
            if path.exists():
                text = path.read_text()
                for line in text.splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        if key and not key.startswith("your-key"):
                            return True
        return False

    def on_onboarding_screen_onboarding_complete(
        self, event: OnboardingScreen.OnboardingComplete
    ) -> None:
        self.pop_screen()
        self.push_screen(DashboardScreen())

    # --- Bot control actions (called by DashboardScreen) ---

    def action_start_bot(self) -> None:
        self._run_bot()

    def action_pause_bot(self) -> None:
        if self._worker_callbacks:
            if self._worker_callbacks.should_pause():
                self._worker_callbacks.request_resume()
                self.post_message(BotStatus(message="Bot resumed"))
            else:
                self._worker_callbacks.request_pause()
                self.post_message(BotPaused())

    def action_open_config(self) -> None:
        self.push_screen(ConfigEditorScreen())

    def action_open_log(self) -> None:
        from src.core import paths

        db_path_str = str(paths.db_path())
        try:
            from src.core.config import load_config

            config = load_config()
            db_path_str = config.db_path
        except Exception:
            pass
        self.push_screen(ActivityLogScreen(db_path=db_path_str))

    def handle_review_decision(
        self, decision: ReviewDecision, comment_text: str
    ) -> None:
        if self._worker_callbacks:
            self._worker_callbacks.submit_approval(
                decision.value, comment_text
            )

    def set_bot_mode(self, mode: "BotMode") -> None:
        from src.tui.widgets.header_bar import BotMode

        if self._worker_callbacks:
            self._worker_callbacks.is_manual_mode = (
                mode == BotMode.MANUAL
            )

    @work(thread=True)
    def _run_bot(self) -> None:
        """Run the bot pipeline in a background thread."""
        from src.ai.comment_generator import CommentGenerator
        from src.ai.gemini_client import GeminiClient
        from src.core.config import load_config
        from src.core.orchestrator import Orchestrator
        from src.core.rate_limiter import RateLimiter
        from src.executor.comment_poster import CommentPoster
        from src.executor.human_typer import HumanTyper
        from src.scraper.browser_factory import create_persistent_context
        from src.scraper.linkedin_scraper import LinkedInScraper
        from src.storage.activity_log import ActivityLog
        from src.tui.events import BotError, BotStarted, BotStatus, BotStopped

        self._worker_callbacks = BotWorkerCallbacks(app=self)
        self.call_from_thread(self.post_message, BotStarted())

        def _status(msg: str) -> None:
            self.call_from_thread(
                self.post_message, BotStatus(message=msg)
            )

        try:
            _status("Loading config...")
            config = load_config()
            if not config.gemini_api_key:
                self.call_from_thread(
                    self.post_message,
                    BotError(error="GEMINI_API_KEY is missing. Please set it in Config -> Security."),
                )
                return

            activity_log = ActivityLog(db_path=config.db_path)
            rate_limiter = RateLimiter(
                activity_log=activity_log,
                daily_limit=config.limits.daily_comment_limit,
            )

            status = rate_limiter.check_status()
            if status.limit_reached:
                self.call_from_thread(
                    self.post_message,
                    BotStopped(reason="Daily limit already reached"),
                )
                return

            _status(f"Rate limit: {status.comments_today}/{status.daily_limit} comments used today")

            human_typer = HumanTyper(
                min_wpm=config.limits.min_wpm,
                max_wpm=config.limits.max_wpm,
            )
            gemini_client = GeminiClient(
                model_name=config.ai.model_name,
                temperature=config.ai.temperature,
                max_output_tokens=config.ai.max_output_tokens,
            )
            comment_generator = CommentGenerator(
                client=gemini_client, config=config.ai
            )

            headless_label = "headless" if config.browser.headless else "visible"
            _status(f"Launching browser ({headless_label})...")

            loop = aio.new_event_loop()
            aio.set_event_loop(loop)

            async def _run_pipeline() -> None:
                async with create_persistent_context(
                    user_data_dir=config.browser.user_data_dir,
                    headless=config.browser.headless,
                    viewport_width=config.browser.viewport_width,
                    viewport_height=config.browser.viewport_height,
                ) as (_, context):
                    _status("Browser ready. Starting pipeline...")
                    like_label = "comment + like" if config.limits.auto_like else "comment only"
                    _status(f"Mode: {like_label} | Targets: {len(config.targets)}")
                    scraper = LinkedInScraper(
                        context=context,
                        activity_log=activity_log,
                        min_reactions=config.limits.min_reactions,
                        min_comments=config.limits.min_comments,
                    )
                    comment_poster = CommentPoster(
                        context=context, human_typer=human_typer
                    )
                    orchestrator = Orchestrator(
                        config=config,
                        rate_limiter=rate_limiter,
                        scraper=scraper,
                        comment_generator=comment_generator,
                        comment_poster=comment_poster,
                        activity_log=activity_log,
                        callbacks=self._worker_callbacks,
                    )
                    await orchestrator.run()

            loop.run_until_complete(_run_pipeline())
            loop.close()

            self.call_from_thread(
                self.post_message,
                BotStopped(reason="Pipeline complete"),
            )

        except Exception as exc:
            logger.exception("Bot worker error")
            self.call_from_thread(
                self.post_message,
                BotError(error=str(exc)),
            )
