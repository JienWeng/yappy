"""Stats panel widget showing today's commenting statistics."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static


class StatsPanel(Widget):
    """Displays today's commenting statistics and rate limit progress."""

    DEFAULT_CSS = """
    StatsPanel {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    StatsPanel .stats-title {
        text-style: bold;
        margin-bottom: 1;
    }
    StatsPanel ProgressBar {
        margin: 1 0;
    }
    """

    comments_today: reactive[int] = reactive(0)
    daily_limit: reactive[int] = reactive(20)
    posts_scanned: reactive[int] = reactive(0)
    posts_skipped: reactive[int] = reactive(0)
    success_count: reactive[int] = reactive(0)
    fail_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("TODAY'S STATS", classes="stats-title")
        yield Label("Comments: 0/20", id="comments-label")
        yield Label("Success Rate: --", id="success-rate-label")
        yield Label("Posts Scanned: 0", id="scanned-label")
        yield Label("Posts Skipped: 0", id="skipped-label")
        yield Label("Rate Limit:")
        yield ProgressBar(
            total=20, show_eta=False, show_percentage=True, id="rate-bar"
        )

    def update_stats(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        self.comments_today = comments_today
        self.daily_limit = daily_limit
        self.posts_scanned = posts_scanned
        self.posts_skipped = posts_skipped
        self.success_count = success_count
        self.fail_count = fail_count

    def watch_comments_today(self, value: int) -> None:
        try:
            self.query_one("#comments-label", Label).update(
                f"Comments: {value}/{self.daily_limit}"
            )
            bar = self.query_one("#rate-bar", ProgressBar)
            bar.total = self.daily_limit
            bar.progress = value
        except Exception:
            pass

    def watch_posts_scanned(self, value: int) -> None:
        try:
            self.query_one("#scanned-label", Label).update(
                f"Posts Scanned: {value}"
            )
        except Exception:
            pass

    def watch_posts_skipped(self, value: int) -> None:
        try:
            self.query_one("#skipped-label", Label).update(
                f"Posts Skipped: {value}"
            )
        except Exception:
            pass

    def reset(self) -> None:
        self.update_stats(
            comments_today=0,
            daily_limit=self.daily_limit,
            posts_scanned=0,
            posts_skipped=0,
            success_count=0,
            fail_count=0,
        )

    def watch_success_count(self, value: int) -> None:
        try:
            total = value + self.fail_count
            rate = f"{(value / total * 100):.0f}%" if total > 0 else "--"
            self.query_one("#success-rate-label", Label).update(
                f"Success Rate: {rate}"
            )
        except Exception:
            pass
