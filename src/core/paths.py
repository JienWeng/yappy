"""XDG-compatible paths for Yappy configuration and data."""
from __future__ import annotations

import platform
from pathlib import Path


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def config_dir() -> Path:
    """Return the config directory (~/.config/yappy/)."""
    return Path.home() / ".config" / "yappy"


def data_dir() -> Path:
    """Return the data directory (XDG or macOS Application Support)."""
    if _is_macos():
        return Path.home() / "Library" / "Application Support" / "yappy"
    xdg = Path(
        __import__("os").environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    )
    return xdg / "yappy"


def config_file() -> Path:
    """Return path to config.yaml."""
    return config_dir() / "config.yaml"


def env_file() -> Path:
    """Return path to .env file."""
    return config_dir() / ".env"


def db_path() -> Path:
    """Return path to the activity database."""
    return data_dir() / "activity.db"


def browser_profile_dir() -> Path:
    """Return path to the Playwright browser profile."""
    return data_dir() / "browser_profile"


def log_dir() -> Path:
    """Return path to the log directory."""
    return data_dir() / "logs"


def log_file() -> Path:
    """Return path to the main log file."""
    return log_dir() / "run.log"


def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    for d in (config_dir(), data_dir(), log_dir()):
        d.mkdir(parents=True, exist_ok=True)


# Default config.yaml content for first-run
DEFAULT_CONFIG_YAML = """\
targets:
  - type: feed
    max_posts: 15
  - type: connections
    max_posts: 5

browser:
  headless: false
  viewport_width: 1920
  viewport_height: 1080

ai:
  model_name: gemini-3-flash-preview
  temperature: 0.85
  max_output_tokens: 150

limits:
  daily_comment_limit: 20
  min_delay_seconds: 15
  max_delay_seconds: 55
  min_wpm: 55
  max_wpm: 80
  min_reactions: 5
  min_comments: 2
"""
