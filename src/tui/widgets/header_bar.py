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
    HeaderBar .update-badge {
        width: auto;
        content-align-vertical: middle;
        background: #ee99a0;
        color: #1e2030;
        padding: 0 1;
        margin-right: 2;
        text-style: bold;
    }
    """

    mode: reactive[BotMode] = reactive(BotMode.AUTO)
    update_version: reactive[str | None] = reactive(None)

    class ModeChanged(Message):
        """Emitted when the mode is toggled."""

        def __init__(self, mode: BotMode) -> None:
            super().__init__()
            self.mode = mode

    def compose(self) -> ComposeResult:
        # Two-tone logo: SAPPHIRE/MAUVE + Dog Emoji
        yield Static("[#8aadf4 bold]YAP[/][#c6a0f6 bold]PY[/] 🐶", classes="header-title")
        yield Label(
            "",
            id="update-label",
            classes="update-badge",
        )
        yield Label(
            f"Mode: {BotMode.AUTO.value.upper()}",
            id="mode-label",
            classes="header-mode",
        )

    def on_mount(self) -> None:
        """Start update check on mount."""
        self.query_one("#update-label", Label).display = False
        self.run_worker(self._perform_update_check, thread=True)

    async def _perform_update_check(self) -> None:
        from src.core.updates import VERSION, check_for_updates
        latest = await check_for_updates(VERSION)
        if latest:
            self.update_version = latest

    def watch_update_version(self, value: str | None) -> None:
        if value:
            label = self.query_one("#update-label", Label)
            label.update(f"Update Available: v{value}")
            label.display = True

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
