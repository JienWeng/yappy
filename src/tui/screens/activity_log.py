"""Activity log screen showing historical comment data."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from src.storage.activity_log import ActivityLog


class ActivityLogScreen(Screen):
    """Displays historical activity from the SQLite database."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("q", "go_back", "Back", show=False),
        Binding("f", "filter_toggle", "Filter", show=True),
    ]

    DEFAULT_CSS = """
    ActivityLogScreen {
        layout: vertical;
    }
    #log-title {
        dock: top;
        width: 100%;
        height: 3;
        text-style: bold;
        content-align: center middle;
        background: #8aadf4;
        color: #1e2030;
    }
    #log-summary {
        height: 1;
        padding: 0 2;
        background: #363a4f;
        color: #c6a0f6;
    }
    DataTable {
        height: 1fr;
        border: tall #8aadf4;
    }
    #log-status {
        dock: bottom;
        width: 100%;
        height: 1;
        background: #363a4f;
        padding: 0 2;
        color: #91d7e3;
    }
    """

    def __init__(
        self, db_path: str = "data/activity.db", **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._db_path = db_path
        self._filter_status: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("ACTIVITY LOG", id="log-title")
        yield Static("", id="log-summary")
        yield DataTable(id="log-table")
        yield Static(
            "Esc:Back  Up/Down:Scroll  Enter:Details  f:Filter",
            id="log-status",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.add_columns("#", "ACTION", "STATUS", "TIME (UTC)", "POST URL", "COMMENT")
        self._load_data()

    def _load_data(self) -> None:
        try:
            log = ActivityLog(db_path=self._db_path)
            records = log.get_recent(limit=100)
            stats = log.get_daily_stats()
        except Exception:
            return

        summary = self.query_one("#log-summary", Static)
        summary.update(
            f"  Today: {stats.successful} posted, {stats.failed} failed | "
            f"Total shown: {len(records)}"
        )

        table = self.query_one("#log-table", DataTable)
        table.clear()

        for record in records:
            if (
                self._filter_status
                and record.status != self._filter_status
            ):
                continue
            status_text = "OK" if record.status == "success" else "FAIL"
            time_str = record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            short_url = (
                record.post_url[-40:]
                if len(record.post_url) > 40
                else record.post_url
            )
            preview = record.comment_text[:50].replace("\n", " ")
            action = getattr(record, "action_type", None) or "comment"
            action_display = action.upper()
            table.add_row(
                str(record.id),
                action_display,
                status_text,
                time_str,
                short_url,
                preview,
                key=str(record.id),
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_filter_toggle(self) -> None:
        if self._filter_status is None:
            self._filter_status = "success"
        elif self._filter_status == "success":
            self._filter_status = "failed"
        else:
            self._filter_status = None

        status = self.query_one("#log-status", Static)
        filter_text = (
            f" | Filter: {self._filter_status}"
            if self._filter_status
            else ""
        )
        status.update(
            f"Esc:Back  Up/Down:Scroll  f:Filter{filter_text}"
        )
        self._load_data()
