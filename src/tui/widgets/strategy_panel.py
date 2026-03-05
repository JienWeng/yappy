"""Widget for displaying current bot strategy and persona."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static


class StrategyPanel(Widget):
    """Displays current persona and targeting strategy."""

    DEFAULT_CSS = """
    StrategyPanel {
        background: $surface;
        border: tall #8aadf4;
        padding: 1 2;
        margin: 1 0;
        height: auto;
    }
    .strategy-title {
        text-style: bold;
        color: #c6a0f6;
        margin-bottom: 1;
        border-bottom: solid #c6a0f6;
    }
    .strategy-item {
        layout: horizontal;
        height: 1;
    }
    .strategy-item Label {
        width: 12;
        text-style: bold;
        color: #91d7e3;
    }
    .strategy-item .strategy-value {
        width: 1fr;
        color: $text;
    }
    """

    persona: reactive[str] = reactive("Not set")
    targets: reactive[str] = reactive("None")
    actions: reactive[str] = reactive("Commenting")

    def compose(self) -> ComposeResult:
        yield Static("CURRENT STRATEGY", classes="strategy-title")
        with Static(classes="strategy-item"):
            yield Label("Persona:")
            yield Label(self.persona, classes="strategy-value", id="strat-persona")
        with Static(classes="strategy-item"):
            yield Label("Targets:")
            yield Label(self.targets, classes="strategy-value", id="strat-targets")
        with Static(classes="strategy-item"):
            yield Label("Actions:")
            yield Label(self.actions, classes="strategy-value", id="strat-actions")

    def update_strategy(
        self, persona: str, targets: list[str], auto_like: bool = False
    ) -> None:
        """Update the displayed strategy values."""
        self.persona = persona.replace("_", " ").title()
        self.targets = ", ".join(targets) if targets else "Feed"
        self.actions = "Comment + Like" if auto_like else "Comment"

    def watch_persona(self, value: str) -> None:
        try:
            self.query_one("#strat-persona", Label).update(value)
        except Exception:
            pass

    def watch_targets(self, value: str) -> None:
        try:
            self.query_one("#strat-targets", Label).update(value)
        except Exception:
            pass

    def watch_actions(self, value: str) -> None:
        try:
            self.query_one("#strat-actions", Label).update(value)
        except Exception:
            pass
