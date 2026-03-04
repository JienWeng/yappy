"""Tests that orchestrator accepts and uses callbacks."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.core.callbacks import NullCallbacks
from src.core.orchestrator import Orchestrator


class TestOrchestratorWithCallbacks:
    def test_constructor_accepts_callbacks(self):
        config = MagicMock()
        config.targets = ()
        orch = Orchestrator(
            config=config,
            rate_limiter=MagicMock(),
            scraper=MagicMock(),
            comment_generator=MagicMock(),
            comment_poster=MagicMock(),
            activity_log=MagicMock(),
            callbacks=NullCallbacks(),
        )
        assert orch is not None

    def test_constructor_defaults_to_null_callbacks(self):
        config = MagicMock()
        config.targets = ()
        orch = Orchestrator(
            config=config,
            rate_limiter=MagicMock(),
            scraper=MagicMock(),
            comment_generator=MagicMock(),
            comment_poster=MagicMock(),
            activity_log=MagicMock(),
        )
        assert orch is not None
