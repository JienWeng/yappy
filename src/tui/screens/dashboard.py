"""Main dashboard screen with stats panel, live feed, and controls."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static

from src.tui.events import (
    BotError,
    BotPaused,
    BotStarted,
    BotStatus,
    BotStopped,
    CommentAwaitingApproval,
    CommentFailed,
    CommentGenerated,
    CommentPosted,
    PostFound,
    PostSkipped,
    StatsUpdated,
)
from src.tui.widgets.comment_review import CommentReview, ReviewDecision
from src.tui.widgets.header_bar import BotMode, HeaderBar
from src.tui.widgets.live_feed import LiveFeed
from src.tui.widgets.stats_panel import StatsPanel
from src.tui.widgets.strategy_panel import StrategyPanel


class DashboardScreen(Screen):
    """Main dashboard with stats, live feed, and bot controls."""

    BINDINGS = [
        Binding("s", "start_bot", "Start", show=True),
        Binding("p", "pause_bot", "Pause", show=True),
        Binding("m", "toggle_mode", "Mode", show=True),
        Binding("c", "open_config", "Config", show=True),
        Binding("l", "open_log", "Log", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("escape", "quit_app", "Quit", show=False),
        Binding("a", "approve_comment", "Approve", show=False),
        Binding("x", "skip_comment", "Skip", show=False),
        Binding("e", "edit_comment", "Edit", show=False),
        Binding("r", "regenerate_comment", "Regenerate", show=False),
    ]

    DEFAULT_CSS = """
    DashboardScreen {
        layout: vertical;
    }
    #dashboard-body {
        layout: horizontal;
        height: 1fr;
    }
    #stats-container {
        width: 30;
        height: 100%;
        border-right: tall #8aadf4;
    }
    #feed-container {
        width: 1fr;
        height: 100%;
    }
    #status-bar {
        dock: bottom;
        width: 100%;
        height: 1;
        background: #363a4f;
        padding: 0 2;
        color: #91d7e3;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._bot_running = False

    def compose(self) -> ComposeResult:
        yield HeaderBar()
        with Horizontal(id="dashboard-body"):
            with Vertical(id="stats-container"):
                yield StatsPanel()
                yield StrategyPanel()
            with Vertical(id="feed-container"):
                yield LiveFeed()
                yield CommentReview()
        yield Static("STATUS: Idle | Press s to start", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize strategy panel from config."""
        try:
            from src.core.config import load_config

            config = load_config()
            strategy = self.query_one(StrategyPanel)
            targeting = []
            for t in config.targets:
                if t.type == "keyword":
                    targeting.append(f"Keyword: {t.value}")
                elif t.type == "feed":
                    targeting.append("Home Feed")

            strategy.update_strategy(
                persona=config.ai.persona_preset,
                targets=targeting,
                auto_like=config.limits.auto_like,
            )
        except Exception:
            pass

    def _update_status(self, text: str) -> None:
        try:
            self.query_one("#status-bar", Static).update(text)
        except Exception:
            pass

    # --- Keybinding actions ---

    def action_start_bot(self) -> None:
        if self._bot_running:
            return
        self._bot_running = True
        self._update_status("STATUS: Starting...")
        self.app.action_start_bot()

    def action_pause_bot(self) -> None:
        if not self._bot_running:
            return
        self.app.action_pause_bot()

    def action_toggle_mode(self) -> None:
        self.query_one(HeaderBar).toggle_mode()

    def action_open_config(self) -> None:
        self.app.action_open_config()

    def action_open_log(self) -> None:
        self.app.action_open_log()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_approve_comment(self) -> None:
        review = self.query_one(CommentReview)
        if review.is_visible:
            review.post_message(
                CommentReview.Decided(
                    decision=ReviewDecision.APPROVE,
                    comment_text=review.current_comment,
                )
            )
            review.hide_review()

    def action_skip_comment(self) -> None:
        review = self.query_one(CommentReview)
        if review.is_visible:
            review.post_message(
                CommentReview.Decided(
                    decision=ReviewDecision.SKIP,
                    comment_text=review.current_comment,
                )
            )
            review.hide_review()

    def action_edit_comment(self) -> None:
        review = self.query_one(CommentReview)
        if review.is_visible:
            try:
                from textual.widgets import TextArea

                area = review.query_one("#review-comment-area", TextArea)
                area.read_only = False
                area.focus()
            except Exception:
                pass

    def action_regenerate_comment(self) -> None:
        review = self.query_one(CommentReview)
        if review.is_visible:
            review.post_message(
                CommentReview.Decided(
                    decision=ReviewDecision.REGENERATE,
                    comment_text=review.current_comment,
                )
            )
            review.hide_review()

    # --- Event handlers ---

    def on_bot_started(self, event: BotStarted) -> None:
        self._bot_running = True
        self.query_one(StatsPanel).reset()
        self.query_one(LiveFeed).add_status("Bot started")
        self._update_status("STATUS: Running")

    def on_bot_status(self, event: BotStatus) -> None:
        self.query_one(LiveFeed).add_status(event.message)

    def on_post_found(self, event: PostFound) -> None:
        self.query_one(LiveFeed).add_status(
            f"Found post by {event.author_name}"
        )

    def on_post_skipped(self, event: PostSkipped) -> None:
        self.query_one(LiveFeed).add_skipped(event.reason)

    def on_comment_generated(self, event: CommentGenerated) -> None:
        self.query_one(LiveFeed).add_status(
            f"Generated comment for {event.author_name}"
        )

    def on_comment_awaiting_approval(
        self, event: CommentAwaitingApproval
    ) -> None:
        self.query_one(CommentReview).show_review(
            author=event.author_name,
            post_preview=event.post_preview,
            comment_text=event.comment_text,
        )
        self._update_status(
            "STATUS: Awaiting approval | a:Approve x:Skip e:Edit r:Regenerate"
        )

    def on_comment_posted(self, event: CommentPosted) -> None:
        author = event.post_url.split("/")[-1][:20]
        self.query_one(LiveFeed).add_posted(author, event.comment_text)

    def on_comment_failed(self, event: CommentFailed) -> None:
        self.query_one(LiveFeed).add_failed("post", event.error)

    def on_stats_updated(self, event: StatsUpdated) -> None:
        self.query_one(StatsPanel).update_stats(
            comments_today=event.comments_today,
            daily_limit=event.daily_limit,
            posts_scanned=event.posts_scanned,
            posts_skipped=event.posts_skipped,
            success_count=event.success_count,
            fail_count=event.fail_count,
        )
        mode = self.query_one(HeaderBar).mode.value.upper()
        self._update_status(
            f"STATUS: Running | "
            f"{event.comments_today}/{event.daily_limit} comments | "
            f"Mode: {mode}"
        )

    def on_bot_paused(self, event: BotPaused) -> None:
        self._update_status("STATUS: Paused | Press p to resume")
        self.query_one(LiveFeed).add_status("Bot paused")

    def on_bot_stopped(self, event: BotStopped) -> None:
        self._bot_running = False
        reason = f" ({event.reason})" if event.reason else ""
        self._update_status(f"STATUS: Stopped{reason} | Press s to start")
        self.query_one(LiveFeed).add_status(f"Bot stopped{reason}")

    def on_bot_error(self, event: BotError) -> None:
        self._bot_running = False
        self._update_status(f"STATUS: Error: {event.error}")
        self.query_one(LiveFeed).add_failed("bot", event.error)

    def on_comment_review_decided(
        self, event: CommentReview.Decided
    ) -> None:
        self.app.handle_review_decision(event.decision, event.comment_text)
        self._update_status("STATUS: Running")

    def on_header_bar_mode_changed(
        self, event: HeaderBar.ModeChanged
    ) -> None:
        self.app.set_bot_mode(event.mode)
        self._update_status(
            f"STATUS: Mode changed to {event.mode.value.upper()}"
        )
