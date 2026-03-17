"""Config editor screen for modifying config.yaml settings."""
from __future__ import annotations

from pathlib import Path

import yaml
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)


class ConfigEditorScreen(Screen):
    """Form-based editor for config.yaml values."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("q", "go_back", "Back", show=False),
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
        background: #8aadf4;
        color: #1e2030;
    }
    #config-tabs {
        height: 1fr;
    }
    .config-section {
        margin-bottom: 2;
        padding: 1 4;
        border: tall #8aadf4;
    }
    .config-section-title {
        text-style: bold;
        margin-bottom: 1;
        color: #c6a0f6;
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
        border: solid #8aadf4;
    }
    .config-area-field {
        height: auto;
        margin-top: 1;
    }
    .config-area-field Label {
        display: block;
        margin-bottom: 1;
    }
    .config-area-field TextArea {
        height: 10;
        border: solid #8aadf4;
    }
    .config-help-text {
        color: #cad3f5;
        text-style: italic;
        margin-top: 1;
        opacity: 0.7;
    }
    #config-status {
        dock: bottom;
        width: 100%;
        height: 1;
        background: #363a4f;
        padding: 0 2;
        color: #91d7e3;
    }
    """

    PERSONALITY_PRESETS = [
        ("The Insightful Expert", "insightful_expert"),
        ("The Supportive Peer", "supportive_peer"),
        ("The Friendly Challenger", "friendly_challenger"),
        ("The Data-Driven Analyst", "data_analyst"),
        ("Custom", "custom"),
    ]

    MODEL_OPTIONS = [
        ("Gemini 3.1 Pro (Frontier)", "gemini-3.1-pro-preview"),
        ("Gemini 3.1 Flash-Lite (Fast/Cheap)", "gemini-3.1-flash-lite-preview"),
        ("Gemini 3 Flash (Workhorse)", "gemini-3-flash-preview"),
        ("Gemini 2.0 Flash", "gemini-2.0-flash"),
        ("Gemini 1.5 Pro", "gemini-1.5-pro"),
    ]

    def __init__(
        self, config_path: str = "config.yaml", **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._config_path = config_path
        self._raw_config: dict = {}
        self._api_key: str = ""

    def compose(self) -> ComposeResult:
        yield Static("CONFIGURATION", id="config-title")
        with TabbedContent(id="config-tabs"):
            with TabPane("General", id="tab-general"):
                with VerticalScroll():
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
                        with Static(classes="config-field"):
                            yield Label("Auto-Like posts:")
                            yield Checkbox("Enabled", value=True, id="cfg-auto-like")

                    with Vertical(classes="config-section"):
                        yield Static("AI SETTINGS", classes="config-section-title")
                        with Static(classes="config-field"):
                            yield Label("Model Selection:")
                            yield Select(
                                self.MODEL_OPTIONS,
                                value="gemini-3-flash-preview",
                                id="cfg-model",
                            )
                        with Static(classes="config-field"):
                            yield Label("Temperature:")
                            yield Input(value="0.85", id="cfg-temperature")

                    with Vertical(classes="config-section"):
                        yield Static("BROWSER SETTINGS", classes="config-section-title")
                        with Static(classes="config-field"):
                            yield Label("Headless Mode:")
                            yield Checkbox("Enabled", id="cfg-headless")

            with TabPane("Advanced", id="tab-advanced"):
                with VerticalScroll():
                    with Vertical(classes="config-section"):
                        yield Static(
                            "PERSONALITY ENGINE", classes="config-section-title"
                        )
                        with Static(classes="config-field"):
                            yield Label("Persona Preset:")
                            yield Select(
                                self.PERSONALITY_PRESETS,
                                value="insightful_expert",
                                id="cfg-persona-preset",
                            )
                        with Vertical(classes="config-area-field"):
                            yield Label("Custom Prompt Prefix:")
                            yield TextArea(id="cfg-persona-prompt")


            with TabPane("Security", id="tab-security"):
                with VerticalScroll():
                    with Vertical(classes="config-section"):
                        yield Static("CREDENTIALS", classes="config-section-title")
                        with Vertical(classes="config-area-field"):
                            yield Label("Gemini API Key (stored in .env):")
                            yield Input(
                                placeholder="PASTE_YOUR_KEY_HERE",
                                password=True,
                                id="cfg-api-key",
                            )
                        yield Static(
                            "Keys are stored locally in your .env file and are never uploaded.",
                            classes="config-help-text",
                        )

                    with Vertical(classes="config-section"):
                        yield Static("LINKEDIN SESSION", classes="config-section-title")
                        with Static(classes="config-field"):
                            yield Label("Session Status:")
                            yield Label("Active (local profile)", id="cfg-linkedin-status")
                        yield Button(
                            "Refresh LinkedIn Login",
                            variant="primary",
                            id="cfg-btn-refresh-login",
                        )
                        yield Static(
                            "This will open a browser window for you to re-authenticate.",
                            classes="config-help-text",
                        )

        yield Static("Esc:Back  Ctrl+S:Save", id="config-status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_config()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle persona preset changes by pre-filling the prompt area."""
        if event.select.id == "cfg-persona-preset" and event.value != "custom":
            prompts = {
                "insightful_expert": "You are a recognized expert in this field. Your comments should be analytical, provide a unique perspective, and cite potential trends.",
                "supportive_peer": "You are a supportive colleague. Your comments should be encouraging, relate to common industry experiences, and build community.",
                "friendly_challenger": "You are a friendly but critical thinker. Your comments should respectfully question assumptions and spark deeper discussion.",
                "data_analyst": "You are a data-driven professional. Your comments should focus on metrics, evidence, and logical outcomes.",
            }
            if event.value in prompts:
                self.query_one("#cfg-persona-prompt", TextArea).text = prompts[
                    event.value
                ]

    def _load_config(self) -> None:
        path = Path(self._config_path)
        if not path.exists():
            return
        with path.open() as f:
            self._raw_config = yaml.safe_load(f) or {}

        limits = self._raw_config.get("limits", {})
        ai = self._raw_config.get("ai", {})
        browser = self._raw_config.get("browser", {})

        # Basic fields
        field_map = {
            "cfg-daily-limit": str(limits.get("daily_comment_limit", 20)),
            "cfg-min-delay": str(limits.get("min_delay_seconds", 15)),
            "cfg-max-delay": str(limits.get("max_delay_seconds", 55)),
            "cfg-temperature": str(ai.get("temperature", 0.85)),
        }
        for field_id, value in field_map.items():
            try:
                self.query_one(f"#{field_id}", Input).value = value
            except Exception:
                pass

        # Checkboxes
        try:
            self.query_one("#cfg-headless", Checkbox).value = browser.get(
                "headless", False
            )
        except Exception:
            pass

        # New limit fields
        try:
            self.query_one("#cfg-min-reactions", Input).value = str(limits.get("min_reactions", 5))
            self.query_one("#cfg-min-comments", Input).value = str(limits.get("min_comments", 2))
            self.query_one("#cfg-auto-like", Checkbox).value = limits.get("auto_like", True)
        except Exception:
            pass

        # Advanced / Select fields
        try:
            model_name = ai.get("model_name", "gemini-3-flash-preview")
            # Safety check: ensure loaded value exists in options to avoid crash
            valid_models = [opt[1] for opt in self.MODEL_OPTIONS]
            if model_name not in valid_models:
                model_name = "gemini-3-flash-preview"
            self.query_one("#cfg-model", Select).value = model_name

            self.query_one("#cfg-persona-preset", Select).value = ai.get(
                "persona_preset", "insightful_expert"
            )
            self.query_one("#cfg-persona-prompt", TextArea).text = ai.get(
                "personality_prefix", ""
            )
        except Exception:
            pass

        # Load API Key from .env
        from src.core.config import load_env_vars

        try:
            env = load_env_vars()
            self._api_key = env.get("gemini_api_key", "")
            self.query_one("#cfg-api-key", Input).value = self._api_key
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

        # Save config.yaml
        path = Path(self._config_path)
        with path.open("w") as f:
            yaml.dump(
                self._raw_config,
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        # Save API key to .env
        self._save_api_key()

        status.update("Config and API Key saved successfully")

    def _save_api_key(self) -> None:
        from src.core import paths

        new_key = self.query_one("#cfg-api-key", Input).value.strip()
        if not new_key:
            return

        env_path = paths.env_file()
        lines: list[str] = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()

        new_lines = [
            line for line in lines if not line.startswith("GEMINI_API_KEY=")
        ]
        new_lines.append(f"GEMINI_API_KEY={new_key}")
        env_path.write_text("\n".join(new_lines) + "\n")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cfg-btn-refresh-login":
            self.run_worker(self._refresh_linkedin_login)

    async def _refresh_linkedin_login(self) -> None:
        """Open browser for LinkedIn re-authentication."""
        import asyncio

        from src.core.config import load_config
        from src.scraper.browser_factory import create_persistent_context

        config = load_config()
        self.query_one("#config-status", Static).update("Opening browser for login...")

        async with create_persistent_context(
            user_data_dir=config.browser.user_data_dir,
            headless=False,  # MUST be False for interactive login
        ) as (_, context):
            page = await context.new_page()
            await page.goto("https://www.linkedin.com/feed/")
            # Wait for user to finish
            while True:
                if "feed" in page.url and not any(
                    p in page.url for p in ("/login", "/checkpoint", "/authwall")
                ):
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(2)  # extra buffer

        self.query_one("#config-status", Static).update("LinkedIn session refreshed!")

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
        _int_field("cfg-min-comments", "min_comments", "limits", 0, 1000)
        limits_section = self._raw_config.setdefault("limits", {})
        limits_section["auto_like"] = self.query_one("#cfg-auto-like", Checkbox).value

        # Cross-field validation for min/max pairs
        limits = self._raw_config.get("limits", {})
        if limits.get("min_delay_seconds", 15) >= limits.get("max_delay_seconds", 55):
            errors.append("Min delay must be less than max delay")

        _float_field("cfg-temperature", "temperature", "ai", 0.0, 2.0)

        # AI Advanced
        ai = self._raw_config.setdefault("ai", {})
        ai["model_name"] = self.query_one("#cfg-model", Select).value
        ai["persona_preset"] = self.query_one("#cfg-persona-preset", Select).value
        ai["personality_prefix"] = self.query_one("#cfg-persona-prompt", TextArea).text

        # Browser
        browser = self._raw_config.setdefault("browser", {})
        browser["headless"] = self.query_one("#cfg-headless", Checkbox).value

        return errors
