"""Config editor screen for modifying config.yaml settings."""
from __future__ import annotations

from pathlib import Path

import yaml
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Input, Label, Static


class ConfigEditorScreen(Screen):
    """Form-based editor for config.yaml values."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("ctrl+s", "save_config", "Save", show=True),
    ]

    DEFAULT_CSS = """
    ConfigEditorScreen {
        layout: vertical;
    }
    #config-title {
        dock: top;
        width: 100%;
        height: 3;
        text-style: bold;
        content-align: center middle;
        background: $primary;
    }
    #config-scroll {
        height: 1fr;
        padding: 1 4;
    }
    .config-section {
        margin-bottom: 2;
    }
    .config-section-title {
        text-style: bold;
        margin-bottom: 1;
    }
    .config-field {
        layout: horizontal;
        height: 3;
    }
    .config-field Label {
        width: 25;
        content-align-vertical: middle;
    }
    .config-field Input {
        width: 1fr;
    }
    #config-status {
        dock: bottom;
        width: 100%;
        height: 1;
        background: $surface;
        padding: 0 2;
    }
    """

    def __init__(
        self, config_path: str = "config.yaml", **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._config_path = config_path
        self._raw_config: dict = {}

    def compose(self) -> ComposeResult:
        yield Static("CONFIGURATION", id="config-title")
        with VerticalScroll(id="config-scroll"):
            with Vertical(classes="config-section"):
                yield Static("LIMITS", classes="config-section-title")
                with Static(classes="config-field"):
                    yield Label("Daily comment limit:")
                    yield Input(value="20", id="cfg-daily-limit")
                with Static(classes="config-field"):
                    yield Label("Min delay (seconds):")
                    yield Input(value="15", id="cfg-min-delay")
                with Static(classes="config-field"):
                    yield Label("Max delay (seconds):")
                    yield Input(value="55", id="cfg-max-delay")
                with Static(classes="config-field"):
                    yield Label("Min reactions:")
                    yield Input(value="5", id="cfg-min-reactions")
                with Static(classes="config-field"):
                    yield Label("Min comments:")
                    yield Input(value="2", id="cfg-min-comments")

            with Vertical(classes="config-section"):
                yield Static("AI SETTINGS", classes="config-section-title")
                with Static(classes="config-field"):
                    yield Label("Model:")
                    yield Input(
                        value="gemini-3-flash-preview", id="cfg-model"
                    )
                with Static(classes="config-field"):
                    yield Label("Temperature:")
                    yield Input(value="0.85", id="cfg-temperature")

        yield Static("Esc:Back  Ctrl+S:Save", id="config-status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_config()

    def _load_config(self) -> None:
        path = Path(self._config_path)
        if not path.exists():
            return
        with path.open() as f:
            self._raw_config = yaml.safe_load(f) or {}

        limits = self._raw_config.get("limits", {})
        ai = self._raw_config.get("ai", {})

        field_map = {
            "cfg-daily-limit": str(limits.get("daily_comment_limit", 20)),
            "cfg-min-delay": str(limits.get("min_delay_seconds", 15)),
            "cfg-max-delay": str(limits.get("max_delay_seconds", 55)),
            "cfg-min-reactions": str(limits.get("min_reactions", 5)),
            "cfg-min-comments": str(limits.get("min_comments", 2)),
            "cfg-model": str(ai.get("model_name", "gemini-3-flash-preview")),
            "cfg-temperature": str(ai.get("temperature", 0.85)),
        }
        for field_id, value in field_map.items():
            try:
                self.query_one(f"#{field_id}", Input).value = value
            except Exception:
                pass

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_save_config(self) -> None:
        errors = self._validate_and_collect()
        status = self.query_one("#config-status", Static)
        if errors:
            status.update(f"Validation errors: {'; '.join(errors)}")
            return

        path = Path(self._config_path)
        with path.open("w") as f:
            yaml.dump(
                self._raw_config,
                f,
                default_flow_style=False,
                sort_keys=False,
            )
        status.update("Config saved successfully")

    def _validate_and_collect(self) -> list[str]:
        errors: list[str] = []

        def _int_field(
            field_id: str,
            key: str,
            section: str,
            min_val: int,
            max_val: int,
        ) -> None:
            try:
                val = int(self.query_one(f"#{field_id}", Input).value)
                if val < min_val or val > max_val:
                    errors.append(f"{key} must be {min_val}-{max_val}")
                    return
                self._raw_config.setdefault(section, {})[key] = val
            except ValueError:
                errors.append(f"{key} must be a number")

        def _float_field(
            field_id: str,
            key: str,
            section: str,
            min_val: float,
            max_val: float,
        ) -> None:
            try:
                val = float(self.query_one(f"#{field_id}", Input).value)
                if val < min_val or val > max_val:
                    errors.append(f"{key} must be {min_val}-{max_val}")
                    return
                self._raw_config.setdefault(section, {})[key] = val
            except ValueError:
                errors.append(f"{key} must be a number")

        _int_field(
            "cfg-daily-limit", "daily_comment_limit", "limits", 1, 100
        )
        _int_field("cfg-min-delay", "min_delay_seconds", "limits", 5, 300)
        _int_field("cfg-max-delay", "max_delay_seconds", "limits", 10, 600)
        _int_field("cfg-min-reactions", "min_reactions", "limits", 0, 1000)
        _int_field("cfg-min-comments", "min_comments", "limits", 0, 100)
        _float_field("cfg-temperature", "temperature", "ai", 0.0, 2.0)

        model = self.query_one("#cfg-model", Input).value.strip()
        if model:
            self._raw_config.setdefault("ai", {})["model_name"] = model

        return errors
