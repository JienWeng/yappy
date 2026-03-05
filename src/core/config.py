from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from src.core import paths


class TargetConfig(BaseModel, frozen=True):
    type: Literal["keyword", "url", "feed", "connections"]
    value: str = ""          # empty for feed/connections types
    max_posts: int = Field(default=5, ge=1, le=50)
    recency_hours: int = Field(default=24, ge=1, le=168)  # only for keyword targets


class BrowserConfig(BaseModel, frozen=True):
    headless: bool = False
    user_data_dir: str = ""
    viewport_width: int = 1920
    viewport_height: int = 1080


class AIConfig(BaseModel, frozen=True):
    model_name: str = "gemini-3-flash-preview"
    temperature: float = Field(default=0.85, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=300, ge=50, le=1000)


class LimitsConfig(BaseModel, frozen=True):
    daily_comment_limit: int = Field(default=20, ge=1, le=100)
    min_delay_seconds: int = Field(default=15, ge=5)
    max_delay_seconds: int = Field(default=45, ge=10)
    min_wpm: int = Field(default=55, ge=20)
    max_wpm: int = Field(default=80, ge=30)
    min_reactions: int = Field(default=5, ge=0)
    min_comments: int = Field(default=2, ge=0)   # skip posts with fewer comments


class AppConfig(BaseModel, frozen=True):
    targets: tuple[TargetConfig, ...] = ()
    browser: BrowserConfig = BrowserConfig()
    ai: AIConfig = AIConfig()
    limits: LimitsConfig = LimitsConfig()
    gemini_api_key: str = ""
    db_path: str = ""


def load_env_vars() -> dict[str, str]:
    """Load and validate required environment variables."""
    from dotenv import load_dotenv

    # Load from XDG .env first, then local .env as fallback
    xdg_env = paths.env_file()
    local_env = Path(".env")

    if xdg_env.exists():
        load_dotenv(xdg_env)
    if local_env.exists():
        load_dotenv(local_env, override=False)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            f"Add your key to {xdg_env} or set the environment variable."
        )
    return {"gemini_api_key": api_key}


def load_config(config_path: str | None = None) -> AppConfig:
    """Load app config from YAML file and merge environment variables.

    If no config_path is given, checks XDG config dir then falls back to local config.yaml.
    """
    if config_path is not None:
        path = Path(config_path)
    else:
        xdg_config = paths.config_file()
        local_config = Path("config.yaml")
        path = xdg_config if xdg_config.exists() else local_config

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Run `yap` to create a default config at {paths.config_file()}"
        )

    with path.open() as f:
        raw = yaml.safe_load(f)

    env_vars = load_env_vars()

    targets = tuple(
        TargetConfig(**t) for t in (raw.get("targets") or [])
    )

    browser_raw = raw.get("browser") or {}
    if "user_data_dir" not in browser_raw:
        browser_raw["user_data_dir"] = str(paths.browser_profile_dir())
    browser = BrowserConfig(**browser_raw)

    ai_cfg = AIConfig(**(raw.get("ai") or {}))
    limits = LimitsConfig(**(raw.get("limits") or {}))

    db_path_str = raw.get("db_path", str(paths.db_path()))

    return AppConfig(
        targets=targets,
        browser=browser,
        ai=ai_cfg,
        limits=limits,
        gemini_api_key=env_vars["gemini_api_key"],
        db_path=db_path_str,
    )
