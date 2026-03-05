"""Header bar widget with app title and mode toggle."""
from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static


class BotMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class HeaderBar(Widget):
    """App header showing title and current mode."""

    DEFAULT_CSS = """
    HeaderBar {
        dock: top;
        width: 100%;
        height: 3;
        padding: 0 2;
        layout: horizontal;
        background: $primary;
        color: $text;
    }
    HeaderBar .header-title {
        width: 1fr;
        content-align-vertical: middle;
        text-style: bold;
    }
    HeaderBar .header-mode {
        width: auto;
        content-align-vertical: middle;
        margin-right: 2;
    }
    """

    mode: reactive[BotMode] = reactive(BotMode.AUTO)

    class ModeChanged(Message):
        """Emitted when the mode is toggled."""

        def __init__(self, mode: BotMode) -> None:
            super().__init__()
            self.mode = mode

    def compose(self) -> ComposeResult:
        yield Static("LinkedIn Auto-Commenter", classes="header-title")
        yield Label(
            f"Mode: {BotMode.AUTO.value.upper()}",
            id="mode-label",
            classes="header-mode",
        )

    def toggle_mode(self) -> None:
        new_mode = (
            BotMode.MANUAL if self.mode == BotMode.AUTO else BotMode.AUTO
        )
        self.mode = new_mode

    def watch_mode(self, value: BotMode) -> None:
        try:
            self.query_one("#mode-label", Label).update(
                f"Mode: {value.value.upper()}"
            )
        except Exception:
            pass
        self.post_message(self.ModeChanged(mode=value))
