"""Live feed widget showing real-time bot activity."""
from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class LiveFeed(Widget):
    """Scrolling log of real-time post processing activity."""

    DEFAULT_CSS = """
    LiveFeed {
        width: 100%;
        height: 100%;
    }
    LiveFeed RichLog {
        width: 100%;
        height: 100%;
        border: solid $primary;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._entry_count = 0

    @property
    def entry_count(self) -> int:
        return self._entry_count

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True, id="feed-log")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M")

    def _write(self, text: str) -> None:
        try:
            log = self.query_one("#feed-log", RichLog)
            log.write(text)
            self._entry_count += 1
        except Exception:
            pass

    def add_posted(self, author: str, comment_preview: str) -> None:
        ts = self._timestamp()
        preview = comment_preview[:60]
        self._write(
            f'{ts} [green]OK[/green]   Posted on {author}\n'
            f'       "{preview}"'
        )

    def add_skipped(self, reason: str) -> None:
        ts = self._timestamp()
        self._write(f"{ts} [yellow]SKIP[/yellow] Skipped ({reason})")

    def add_failed(self, author: str, error: str) -> None:
        ts = self._timestamp()
        self._write(f"{ts} [red]FAIL[/red] Failed on {author}: {error}")

    def add_status(self, message: str) -> None:
        ts = self._timestamp()
        self._write(f"{ts} [dim]...  {message}[/dim]")

    def clear_feed(self) -> None:
        try:
            log = self.query_one("#feed-log", RichLog)
            log.clear()
            self._entry_count = 0
        except Exception:
            pass
