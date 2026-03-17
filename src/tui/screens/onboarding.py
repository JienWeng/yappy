"""Onboarding wizard screen for first-time setup."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Input,
    Label,
    Static,
)

STEP_TITLES = (
    "Welcome",
    "API Key Setup",
    "LinkedIn Login",
    "Target Configuration",
    "Dry Run Preview",
)


class OnboardingScreen(Screen):
    """Multi-step onboarding wizard."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    OnboardingScreen {
        align: center middle;
    }
    #onboarding-container {
        width: 70;
        height: auto;
        max-height: 90%;
        border: solid $accent;
        padding: 2 4;
    }
    .step-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    .step-content {
        margin-bottom: 2;
    }
    .nav-buttons {
        layout: horizontal;
        align: center middle;
        height: 3;
    }
    .nav-buttons Button {
        margin: 0 1;
    }
    Input {
        margin: 1 0;
    }
    .error-label {
        color: $error;
    }
    .success-label {
        color: $success;
    }
    """

    class OnboardingComplete(Message):
        """Emitted when the user finishes onboarding."""

        pass

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._current_step = 0
        self._api_key = ""

    @property
    def current_step(self) -> int:
        return self._current_step

    def compose(self) -> ComposeResult:
        with Vertical(id="onboarding-container"):
            yield Static("", id="step-title", classes="step-title")
            with VerticalScroll(id="step-content", classes="step-content"):
                yield Static("", id="step-body")
                yield Input(
                    placeholder="Enter your Gemini API key",
                    id="api-key-input",
                )
                yield Label("", id="validation-label")
                yield Button("Test Connection", id="btn-test-key", variant="warning")
                yield Checkbox(
                    "Feed (your network posts)", id="cb-feed", value=True
                )
                yield Checkbox(
                    "Connections (direct connections)",
                    id="cb-connections",
                    value=True,
                )
                yield Input(
                    placeholder="Keyword (e.g. 'AI startup')",
                    id="keyword-input",
                )
                yield Input(
                    placeholder="Max posts per target",
                    id="max-posts-input",
                    value="10",
                )
            with Static(classes="nav-buttons"):
                yield Button("Back", id="btn-back", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button(
                    "Get Started", id="btn-start", variant="success"
                )
        yield Footer()

    def on_mount(self) -> None:
        self._render_step()

    def _render_step(self) -> None:
        step = self._current_step
        title = self.query_one("#step-title", Static)
        body = self.query_one("#step-body", Static)
        api_input = self.query_one("#api-key-input", Input)
        validation = self.query_one("#validation-label", Label)
        cb_feed = self.query_one("#cb-feed", Checkbox)
        cb_conn = self.query_one("#cb-connections", Checkbox)
        kw_input = self.query_one("#keyword-input", Input)
        mp_input = self.query_one("#max-posts-input", Input)
        btn_back = self.query_one("#btn-back", Button)
        btn_next = self.query_one("#btn-next", Button)
        btn_start = self.query_one("#btn-start", Button)
        btn_test = self.query_one("#btn-test-key", Button)

        # Hide all dynamic elements
        for widget in (
            api_input,
            validation,
            cb_feed,
            cb_conn,
            kw_input,
            mp_input,
            btn_test,
        ):
            widget.display = False

        title.update(
            f"Step {step + 1}/5: {STEP_TITLES[step]} "
            f"{'•' * (step + 1)}{'◦' * (4 - step)}"
        )
        btn_back.display = step > 0
        btn_next.display = step < 4
        btn_start.display = step == 0

        if step == 0:
            body.update(
                "Welcome to Yappy! This tool automatically discovers "
                "LinkedIn posts and leaves thoughtful, AI-generated comments.\n\n"
                "This wizard will guide you through:\n"
                "  1. Setting up your Gemini API key\n"
                "  2. Logging into LinkedIn\n"
                "  3. Configuring which posts to target\n"
                "  4. Previewing what the bot would do"
            )
            btn_next.display = False
        elif step == 1:
            body.update(
                "You need a Gemini API key to generate comments.\n"
                "Get one at: https://aistudio.google.com/apikey"
            )
            api_input.display = True
            validation.display = True
            btn_test.display = True
            btn_start.display = False
        elif step == 2:
            body.update(
                "A browser window will open.\n"
                "Please log into your LinkedIn account manually.\n\n"
                "⚠️ IMPORTANT: Wait until you see your actual LinkedIn feed before clicking 'Next'.\n"
                "This ensures your session is correctly saved."
            )
            btn_start.display = False
        elif step == 3:
            body.update("Select post sources and configure limits:")
            cb_feed.display = True
            cb_conn.display = True
            kw_input.display = True
            mp_input.display = True
            btn_start.display = False
        elif step == 4:
            body.update(
                "Ready to run a dry preview.\n"
                "This will scan for posts but NOT post any comments.\n\n"
                "Click Next to finish setup."
            )
            btn_start.display = False
            btn_next.display = True
            btn_next.label = "Finish Setup"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-test-key":
            self.run_worker(self._test_gemini_key)
        elif button_id == "btn-start":
            self._current_step = 1
            self._render_step()
        elif button_id == "btn-next":
            if self._validate_current_step():
                if self._current_step == 4:
                    self._finish_onboarding()
                else:
                    self._current_step += 1
                    self._render_step()
        elif button_id == "btn-back":
            if self._current_step > 0:
                self._current_step -= 1
                self._render_step()

    async def _test_gemini_key(self) -> None:
        """Test the provided Gemini API key with a simple request."""
        api_input = self.query_one("#api-key-input", Input)
        key = api_input.value.strip()
        validation = self.query_one("#validation-label", Label)

        if not key:
            validation.update("Enter a key first")
            return

        validation.update("Testing key...")

        try:
            import os

            from src.ai.gemini_client import GeminiClient

            # Temporary env override for testing
            os.environ["GEMINI_API_KEY"] = key
            client = GeminiClient(model_name="gemini-1.5-flash")
            # Try to generate a single word
            client.generate("Say 'Connected'")
            validation.update("✅ Key works! Connection successful.")
            validation.remove_class("error-label")
            validation.add_class("success-label")
        except Exception as e:
            validation.update(f"❌ Connection failed: {str(e)}")
            validation.add_class("error-label")
            validation.remove_class("success-label")

    def action_go_back(self) -> None:
        if self._current_step > 0:
            self._current_step -= 1
            self._render_step()

    def _validate_current_step(self) -> bool:
        validation = self.query_one("#validation-label", Label)
        if self._current_step == 1:
            api_input = self.query_one("#api-key-input", Input)
            key = api_input.value.strip()
            if not key:
                validation.update("API key is required")
                validation.add_class("error-label")
                validation.remove_class("success-label")
                return False
            self._api_key = key
            validation.update("API key saved")
            validation.remove_class("error-label")
            validation.add_class("success-label")
        return True

    def _finish_onboarding(self) -> None:
        # Save API key to XDG .env
        from src.core import paths

        paths.ensure_dirs()
        env_path = paths.env_file()

        lines: list[str] = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()
        new_lines = [
            line for line in lines if not line.startswith("GEMINI_API_KEY=")
        ]
        new_lines.append(f"GEMINI_API_KEY={self._api_key}")
        env_path.write_text("\n".join(new_lines) + "\n")

        # Also ensure config.yaml exists
        config_file = paths.config_file()
        if not config_file.exists():
            config_file.write_text(paths.DEFAULT_CONFIG_YAML)

        self.post_message(self.OnboardingComplete())
