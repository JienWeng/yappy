# TUI Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the CLI entry point with a full Textual TUI featuring onboarding wizard, live dashboard, config editor, and activity log — with both auto and manual comment approval modes.

**Architecture:** Single Textual app with Worker threads. The bot pipeline runs in a `@work(thread=True)` worker that posts custom `Message` events to the UI. Existing `src/core`, `src/scraper`, `src/ai`, `src/executor`, `src/storage` modules are untouched except the orchestrator, which gains a callback interface.

**Tech Stack:** Python 3.9+, Textual 8.x, existing Playwright/Gemini/SQLite stack.

**Design doc:** `docs/plans/2026-03-04-tui-dashboard-design.md`

---

### Task 1: Add Textual Dependency and Create Package Structure

**Files:**
- Modify: `requirements.txt`
- Create: `src/tui/__init__.py`
- Create: `src/tui/screens/__init__.py`
- Create: `src/tui/widgets/__init__.py`
- Create: `src/tui/workers/__init__.py`

**Step 1: Add textual to requirements.txt**

Add this line to `requirements.txt`:

```
textual>=0.80.0
```

Note: Use `>=0.80.0` not `>=3.0` — Textual's PyPI versioning is 0.x. Version 8.0.1 is the latest but the `>=0.80.0` constraint covers it. Actually, the latest is `8.0.1` on PyPI, so use:

```
textual>=8.0.0
```

**Step 2: Create package directories**

```bash
mkdir -p src/tui/screens src/tui/widgets src/tui/workers
touch src/tui/__init__.py src/tui/screens/__init__.py src/tui/widgets/__init__.py src/tui/workers/__init__.py
```

**Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 4: Verify textual is importable**

```bash
python -c "import textual; print(textual.__version__)"
```

Expected: prints version like `8.0.1`

**Step 5: Commit**

```bash
git add requirements.txt src/tui/
git commit -m "chore: add textual dependency and tui package structure"
```

---

### Task 2: Create Custom Events Module

**Files:**
- Create: `src/tui/events.py`
- Create: `tests/unit/test_tui_events.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_tui_events.py
"""Tests for TUI custom event messages."""
from __future__ import annotations

from src.tui.events import (
    BotStarted,
    PostFound,
    PostSkipped,
    CommentGenerated,
    CommentAwaitingApproval,
    CommentPosted,
    CommentFailed,
    StatsUpdated,
    BotPaused,
    BotStopped,
    BotError,
)


class TestWorkerToUIEvents:
    def test_bot_started_is_message(self):
        event = BotStarted()
        assert event is not None

    def test_post_found_carries_data(self):
        event = PostFound(
            post_url="https://linkedin.com/post/123",
            author_name="Jane Doe",
            text_preview="Excited to announce...",
        )
        assert event.post_url == "https://linkedin.com/post/123"
        assert event.author_name == "Jane Doe"
        assert event.text_preview == "Excited to announce..."

    def test_post_skipped_carries_reason(self):
        event = PostSkipped(
            post_url="https://linkedin.com/post/456",
            reason="job posting",
        )
        assert event.post_url == "https://linkedin.com/post/456"
        assert event.reason == "job posting"

    def test_comment_generated_carries_data(self):
        event = CommentGenerated(
            post_url="https://linkedin.com/post/123",
            author_name="Jane Doe",
            comment_text="Great point about developer experience.",
        )
        assert event.comment_text == "Great point about developer experience."

    def test_comment_awaiting_approval_carries_data(self):
        event = CommentAwaitingApproval(
            post_url="https://linkedin.com/post/123",
            author_name="Jane Doe",
            post_preview="Excited to announce...",
            comment_text="Great point about developer experience.",
        )
        assert event.post_preview == "Excited to announce..."

    def test_comment_posted_carries_data(self):
        event = CommentPosted(
            post_url="https://linkedin.com/post/123",
            comment_text="Great point.",
        )
        assert event.post_url == "https://linkedin.com/post/123"

    def test_comment_failed_carries_error(self):
        event = CommentFailed(
            post_url="https://linkedin.com/post/123",
            error="Submit button not found",
        )
        assert event.error == "Submit button not found"

    def test_stats_updated_carries_counts(self):
        event = StatsUpdated(
            comments_today=7,
            daily_limit=20,
            posts_scanned=42,
            posts_skipped=35,
            success_count=6,
            fail_count=1,
        )
        assert event.comments_today == 7
        assert event.daily_limit == 20

    def test_bot_stopped_carries_reason(self):
        event = BotStopped(reason="rate limit reached")
        assert event.reason == "rate limit reached"

    def test_bot_error_carries_error(self):
        event = BotError(error="Browser crashed")
        assert event.error == "Browser crashed"

    def test_bot_paused(self):
        event = BotPaused()
        assert event is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_tui_events.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.tui.events'`

**Step 3: Write the events module**

```python
# src/tui/events.py
"""Custom Textual messages for worker <-> UI communication."""
from __future__ import annotations

from textual.message import Message


# --- Worker -> UI Messages ---


class BotStarted(Message):
    """Bot pipeline has begun."""
    pass


class PostFound(Message):
    """A post was discovered during scraping."""

    def __init__(
        self,
        post_url: str,
        author_name: str,
        text_preview: str,
    ) -> None:
        super().__init__()
        self.post_url = post_url
        self.author_name = author_name
        self.text_preview = text_preview


class PostSkipped(Message):
    """A post was filtered out."""

    def __init__(self, post_url: str, reason: str) -> None:
        super().__init__()
        self.post_url = post_url
        self.reason = reason


class CommentGenerated(Message):
    """A comment was generated for a post."""

    def __init__(
        self,
        post_url: str,
        author_name: str,
        comment_text: str,
    ) -> None:
        super().__init__()
        self.post_url = post_url
        self.author_name = author_name
        self.comment_text = comment_text


class CommentAwaitingApproval(Message):
    """Manual mode: comment generated, waiting for user decision."""

    def __init__(
        self,
        post_url: str,
        author_name: str,
        post_preview: str,
        comment_text: str,
    ) -> None:
        super().__init__()
        self.post_url = post_url
        self.author_name = author_name
        self.post_preview = post_preview
        self.comment_text = comment_text


class CommentPosted(Message):
    """Comment was successfully posted."""

    def __init__(self, post_url: str, comment_text: str) -> None:
        super().__init__()
        self.post_url = post_url
        self.comment_text = comment_text


class CommentFailed(Message):
    """Comment posting failed."""

    def __init__(self, post_url: str, error: str) -> None:
        super().__init__()
        self.post_url = post_url
        self.error = error


class StatsUpdated(Message):
    """Updated pipeline statistics."""

    def __init__(
        self,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        super().__init__()
        self.comments_today = comments_today
        self.daily_limit = daily_limit
        self.posts_scanned = posts_scanned
        self.posts_skipped = posts_skipped
        self.success_count = success_count
        self.fail_count = fail_count


class BotPaused(Message):
    """Bot was paused by user."""
    pass


class BotStopped(Message):
    """Bot finished or was stopped."""

    def __init__(self, reason: str = "") -> None:
        super().__init__()
        self.reason = reason


class BotError(Message):
    """Unrecoverable bot error."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_tui_events.py -v
```

Expected: all 11 tests PASS

**Step 5: Commit**

```bash
git add src/tui/events.py tests/unit/test_tui_events.py
git commit -m "feat: add custom Textual events for worker-UI communication"
```

---

### Task 3: Add Callback Interface to Orchestrator

**Files:**
- Create: `src/core/callbacks.py`
- Modify: `src/core/orchestrator.py` (lines 32-48 constructor, lines 49-136 run method)
- Create: `tests/unit/test_orchestrator_callbacks.py`

This task adds a callback protocol to the orchestrator so the TUI worker can receive events without the orchestrator knowing about Textual.

**Step 1: Write the failing test**

```python
# tests/unit/test_orchestrator_callbacks.py
"""Tests for orchestrator callback interface."""
from __future__ import annotations

from src.core.callbacks import OrchestratorCallbacks, NullCallbacks


class TestNullCallbacks:
    """NullCallbacks should be a no-op implementation."""

    def test_on_post_found_is_noop(self):
        cb = NullCallbacks()
        cb.on_post_found(post_url="url", author_name="name", text_preview="text")

    def test_on_post_skipped_is_noop(self):
        cb = NullCallbacks()
        cb.on_post_skipped(post_url="url", reason="reason")

    def test_on_comment_generated_is_noop(self):
        cb = NullCallbacks()
        cb.on_comment_generated(post_url="url", author_name="name", comment_text="text")

    def test_on_comment_posted_is_noop(self):
        cb = NullCallbacks()
        cb.on_comment_posted(post_url="url", comment_text="text")

    def test_on_comment_failed_is_noop(self):
        cb = NullCallbacks()
        cb.on_comment_failed(post_url="url", error="err")

    def test_on_stats_updated_is_noop(self):
        cb = NullCallbacks()
        cb.on_stats_updated(
            comments_today=0, daily_limit=20,
            posts_scanned=0, posts_skipped=0,
            success_count=0, fail_count=0,
        )

    def test_should_pause_returns_false(self):
        cb = NullCallbacks()
        assert cb.should_pause() is False

    def test_should_stop_returns_false(self):
        cb = NullCallbacks()
        assert cb.should_stop() is False


class TestOrchestratorCallbacksProtocol:
    """OrchestratorCallbacks should be a Protocol class."""

    def test_null_callbacks_satisfies_protocol(self):
        cb: OrchestratorCallbacks = NullCallbacks()
        assert isinstance(cb, NullCallbacks)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_orchestrator_callbacks.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Create the callbacks module**

```python
# src/core/callbacks.py
"""Callback interface for orchestrator pipeline events.

The orchestrator calls these methods at each stage. Implementations
can forward events to a TUI, logger, webhook, etc. The orchestrator
does not depend on any specific UI framework.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OrchestratorCallbacks(Protocol):
    """Protocol for receiving orchestrator pipeline events."""

    def on_post_found(
        self, *, post_url: str, author_name: str, text_preview: str
    ) -> None: ...

    def on_post_skipped(self, *, post_url: str, reason: str) -> None: ...

    def on_comment_generated(
        self, *, post_url: str, author_name: str, comment_text: str
    ) -> None: ...

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None: ...

    def on_comment_failed(self, *, post_url: str, error: str) -> None: ...

    def on_stats_updated(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None: ...

    def should_pause(self) -> bool: ...

    def should_stop(self) -> bool: ...


class NullCallbacks:
    """No-op implementation. Used when no UI is attached."""

    def on_post_found(
        self, *, post_url: str, author_name: str, text_preview: str
    ) -> None:
        pass

    def on_post_skipped(self, *, post_url: str, reason: str) -> None:
        pass

    def on_comment_generated(
        self, *, post_url: str, author_name: str, comment_text: str
    ) -> None:
        pass

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None:
        pass

    def on_comment_failed(self, *, post_url: str, error: str) -> None:
        pass

    def on_stats_updated(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        pass

    def should_pause(self) -> bool:
        return False

    def should_stop(self) -> bool:
        return False
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_orchestrator_callbacks.py -v
```

Expected: all 9 tests PASS

**Step 5: Commit**

```bash
git add src/core/callbacks.py tests/unit/test_orchestrator_callbacks.py
git commit -m "feat: add OrchestratorCallbacks protocol and NullCallbacks"
```

---

### Task 4: Integrate Callbacks into Orchestrator

**Files:**
- Modify: `src/core/orchestrator.py`

This modifies the orchestrator to accept an optional `callbacks` parameter and call it at each pipeline stage. The existing behavior is preserved (NullCallbacks is the default). Also adds `should_pause()` and `should_stop()` checks in the main loop.

**Step 1: Write the failing test**

```python
# tests/unit/test_orchestrator_integration.py
"""Tests that orchestrator calls callbacks at each pipeline stage."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.callbacks import NullCallbacks
from src.core.orchestrator import Orchestrator


class RecordingCallbacks(NullCallbacks):
    """Records all callback invocations for testing."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._should_pause = False
        self._should_stop = False

    def on_post_found(self, *, post_url: str, author_name: str, text_preview: str) -> None:
        self.calls.append(("post_found", {"post_url": post_url, "author_name": author_name}))

    def on_comment_generated(self, *, post_url: str, author_name: str, comment_text: str) -> None:
        self.calls.append(("comment_generated", {"post_url": post_url, "comment_text": comment_text}))

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None:
        self.calls.append(("comment_posted", {"post_url": post_url}))

    def on_comment_failed(self, *, post_url: str, error: str) -> None:
        self.calls.append(("comment_failed", {"post_url": post_url, "error": error}))

    def on_stats_updated(self, **kwargs) -> None:
        self.calls.append(("stats_updated", kwargs))

    def should_pause(self) -> bool:
        return self._should_pause

    def should_stop(self) -> bool:
        return self._should_stop


class TestOrchestratorWithCallbacks:
    def test_constructor_accepts_callbacks(self):
        """Orchestrator should accept an optional callbacks parameter."""
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
        """Orchestrator should work without callbacks (backward compat)."""
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_orchestrator_integration.py -v
```

Expected: FAIL — `Orchestrator.__init__() got an unexpected keyword argument 'callbacks'`

**Step 3: Modify orchestrator to accept and use callbacks**

In `src/core/orchestrator.py`, make the following changes:

1. Add import for callbacks at the top (in TYPE_CHECKING block):

```python
if TYPE_CHECKING:
    from src.core.callbacks import OrchestratorCallbacks
    from src.core.config import AppConfig
    ...
```

2. Add `from src.core.callbacks import NullCallbacks` as a regular import.

3. Modify `__init__` to accept `callbacks`:

```python
def __init__(
    self,
    config: "AppConfig",
    rate_limiter: "RateLimiter",
    scraper: "LinkedInScraper",
    comment_generator: "CommentGenerator",
    comment_poster: "CommentPoster",
    activity_log: "ActivityLog",
    callbacks: "OrchestratorCallbacks | None" = None,
) -> None:
    self._config = config
    self._rate_limiter = rate_limiter
    self._scraper = scraper
    self._generator = comment_generator
    self._poster = comment_poster
    self._log = activity_log
    self._callbacks: OrchestratorCallbacks = callbacks or NullCallbacks()
```

4. In the `run()` method, add callback calls after each stage. Add these calls at the appropriate locations:

After scraping posts (line ~68, after `posts_scraped += len(scrape_result.posts)`):
```python
for post in scrape_result.posts:
    self._callbacks.on_post_found(
        post_url=post.post_url,
        author_name=post.author_name,
        text_preview=post.post_text[:100],
    )
```

After successful comment generation (after `generate_result = self._generator.generate(post)`, before posting):
```python
self._callbacks.on_comment_generated(
    post_url=post.post_url,
    author_name=post.author_name,
    comment_text=generate_result.comment.text,
)
```

After successful post (after `comments_succeeded += 1`):
```python
self._callbacks.on_comment_posted(
    post_url=post.post_url,
    comment_text=generate_result.comment.text,
)
```

In the exception handler (after `comments_failed += 1`):
```python
self._callbacks.on_comment_failed(
    post_url=post.post_url,
    error=str(exc),
)
```

After each post processing (before `await self._random_delay()`):
```python
status = self._rate_limiter.check_status()
self._callbacks.on_stats_updated(
    comments_today=status.comments_today,
    daily_limit=status.daily_limit,
    posts_scanned=posts_scraped,
    posts_skipped=posts_scraped - comments_attempted,
    success_count=comments_succeeded,
    fail_count=comments_failed,
)
```

At the top of the per-post loop, add pause/stop checks:
```python
if self._callbacks.should_stop():
    logger.info("Stop requested via callback")
    break

while self._callbacks.should_pause():
    await asyncio.sleep(0.5)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_orchestrator_integration.py -v
```

Expected: both tests PASS

**Step 5: Run all existing tests to verify no regression**

```bash
pytest tests/ -v
```

Expected: all existing tests still PASS

**Step 6: Commit**

```bash
git add src/core/orchestrator.py tests/unit/test_orchestrator_integration.py
git commit -m "feat: integrate callback interface into orchestrator"
```

---

### Task 5: Create Stats Panel Widget

**Files:**
- Create: `src/tui/widgets/stats_panel.py`
- Create: `tests/unit/test_stats_panel.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_stats_panel.py
"""Tests for the StatsPanel widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.stats_panel import StatsPanel


class StatsApp(App):
    """Minimal app for testing StatsPanel."""

    def compose(self) -> ComposeResult:
        yield StatsPanel()


class TestStatsPanel:
    @pytest.mark.asyncio
    async def test_initial_values_are_zero(self):
        async with StatsApp().run_test() as pilot:
            panel = pilot.app.query_one(StatsPanel)
            assert panel.comments_today == 0
            assert panel.daily_limit == 20
            assert panel.posts_scanned == 0
            assert panel.posts_skipped == 0

    @pytest.mark.asyncio
    async def test_update_stats(self):
        async with StatsApp().run_test() as pilot:
            panel = pilot.app.query_one(StatsPanel)
            panel.update_stats(
                comments_today=7,
                daily_limit=20,
                posts_scanned=42,
                posts_skipped=35,
                success_count=6,
                fail_count=1,
            )
            assert panel.comments_today == 7
            assert panel.posts_scanned == 42
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_stats_panel.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the StatsPanel widget**

```python
# src/tui/widgets/stats_panel.py
"""Stats panel widget showing today's commenting statistics."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static


class StatsPanel(Widget):
    """Displays today's commenting statistics and rate limit progress."""

    DEFAULT_CSS = """
    StatsPanel {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    StatsPanel .stats-title {
        text-style: bold;
        margin-bottom: 1;
    }
    StatsPanel .stats-row {
        margin-bottom: 0;
    }
    StatsPanel .stats-separator {
        margin: 1 0;
    }
    StatsPanel ProgressBar {
        margin: 1 0;
    }
    """

    comments_today: reactive[int] = reactive(0)
    daily_limit: reactive[int] = reactive(20)
    posts_scanned: reactive[int] = reactive(0)
    posts_skipped: reactive[int] = reactive(0)
    success_count: reactive[int] = reactive(0)
    fail_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("TODAY'S STATS", classes="stats-title")
        yield Static("", classes="stats-separator")
        yield Label("Comments: 0/20", id="comments-label")
        yield Label("Success Rate: --", id="success-rate-label")
        yield Label("Posts Scanned: 0", id="scanned-label")
        yield Label("Posts Skipped: 0", id="skipped-label")
        yield Static("", classes="stats-separator")
        yield Label("Rate Limit:", id="rate-limit-label")
        yield ProgressBar(total=20, show_eta=False, show_percentage=True, id="rate-bar")

    def update_stats(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        self.comments_today = comments_today
        self.daily_limit = daily_limit
        self.posts_scanned = posts_scanned
        self.posts_skipped = posts_skipped
        self.success_count = success_count
        self.fail_count = fail_count

    def watch_comments_today(self, value: int) -> None:
        try:
            label = self.query_one("#comments-label", Label)
            label.update(f"Comments: {value}/{self.daily_limit}")
            bar = self.query_one("#rate-bar", ProgressBar)
            bar.total = self.daily_limit
            bar.progress = value
        except Exception:
            pass

    def watch_posts_scanned(self, value: int) -> None:
        try:
            self.query_one("#scanned-label", Label).update(f"Posts Scanned: {value}")
        except Exception:
            pass

    def watch_posts_skipped(self, value: int) -> None:
        try:
            self.query_one("#skipped-label", Label).update(f"Posts Skipped: {value}")
        except Exception:
            pass

    def watch_success_count(self, value: int) -> None:
        try:
            total = value + self.fail_count
            rate = f"{(value / total * 100):.0f}%" if total > 0 else "--"
            self.query_one("#success-rate-label", Label).update(f"Success Rate: {rate}")
        except Exception:
            pass
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_stats_panel.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/widgets/stats_panel.py tests/unit/test_stats_panel.py
git commit -m "feat: add StatsPanel widget with reactive stats display"
```

---

### Task 6: Create Live Feed Widget

**Files:**
- Create: `src/tui/widgets/live_feed.py`
- Create: `tests/unit/test_live_feed.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_live_feed.py
"""Tests for the LiveFeed widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.live_feed import LiveFeed


class FeedApp(App):
    def compose(self) -> ComposeResult:
        yield LiveFeed()


class TestLiveFeed:
    @pytest.mark.asyncio
    async def test_add_posted_entry(self):
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_posted("@JaneDoe", "Great point about developer experience.")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_add_skipped_entry(self):
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_skipped("job posting")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_add_failed_entry(self):
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_failed("@BobJones", "Submit button not found")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_add_status_entry(self):
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_status("Generating comment...")
            assert feed.entry_count == 1

    @pytest.mark.asyncio
    async def test_multiple_entries(self):
        async with FeedApp().run_test() as pilot:
            feed = pilot.app.query_one(LiveFeed)
            feed.add_posted("@JaneDoe", "Great point.")
            feed.add_skipped("low engagement")
            feed.add_failed("@Bob", "error")
            assert feed.entry_count == 3
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_live_feed.py -v
```

Expected: FAIL

**Step 3: Write the LiveFeed widget**

```python
# src/tui/widgets/live_feed.py
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

    def __init__(self, **kwargs) -> None:
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
        self._write(f"{ts} [green]OK[/green]   Posted on {author}\n       \"{preview}\"")

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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_live_feed.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/widgets/live_feed.py tests/unit/test_live_feed.py
git commit -m "feat: add LiveFeed widget for real-time activity display"
```

---

### Task 7: Create Comment Review Widget

**Files:**
- Create: `src/tui/widgets/comment_review.py`
- Create: `tests/unit/test_comment_review.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_comment_review.py
"""Tests for the CommentReview widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.comment_review import CommentReview, ReviewDecision


class ReviewApp(App):
    BINDINGS = []

    def compose(self) -> ComposeResult:
        yield CommentReview()


class TestCommentReview:
    @pytest.mark.asyncio
    async def test_show_review_sets_content(self):
        async with ReviewApp().run_test() as pilot:
            widget = pilot.app.query_one(CommentReview)
            widget.show_review(
                author="@JaneDoe",
                post_preview="Excited to announce our new product...",
                comment_text="Congrats on the launch!",
            )
            assert widget.current_comment == "Congrats on the launch!"
            assert widget.is_visible is True

    @pytest.mark.asyncio
    async def test_hide_review(self):
        async with ReviewApp().run_test() as pilot:
            widget = pilot.app.query_one(CommentReview)
            widget.show_review(
                author="@JaneDoe",
                post_preview="Post text",
                comment_text="Comment text",
            )
            widget.hide_review()
            assert widget.current_comment == ""


class TestReviewDecision:
    def test_approve_value(self):
        assert ReviewDecision.APPROVE == "approve"

    def test_skip_value(self):
        assert ReviewDecision.SKIP == "skip"

    def test_edit_value(self):
        assert ReviewDecision.EDIT == "edit"

    def test_regenerate_value(self):
        assert ReviewDecision.REGENERATE == "regenerate"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_comment_review.py -v
```

Expected: FAIL

**Step 3: Write the CommentReview widget**

```python
# src/tui/widgets/comment_review.py
"""Comment review widget for manual approval mode."""
from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Static, TextArea


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    SKIP = "skip"
    EDIT = "edit"
    REGENERATE = "regenerate"


class CommentReview(Widget):
    """Widget for reviewing and approving/rejecting generated comments."""

    DEFAULT_CSS = """
    CommentReview {
        width: 100%;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        display: none;
    }
    CommentReview.visible {
        display: block;
    }
    CommentReview .review-title {
        text-style: bold;
        margin-bottom: 1;
    }
    CommentReview .review-post-preview {
        margin-bottom: 1;
        color: $text-muted;
    }
    CommentReview TextArea {
        height: 4;
        margin-bottom: 1;
    }
    CommentReview .review-buttons {
        layout: horizontal;
        height: 3;
    }
    CommentReview Button {
        margin-right: 1;
    }
    """

    class Decided(Message):
        """User made a review decision."""

        def __init__(self, decision: ReviewDecision, comment_text: str) -> None:
            super().__init__()
            self.decision = decision
            self.comment_text = comment_text

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_comment = ""

    @property
    def current_comment(self) -> str:
        return self._current_comment

    @property
    def is_visible(self) -> bool:
        return self.has_class("visible")

    def compose(self) -> ComposeResult:
        yield Static("REVIEW COMMENT", classes="review-title")
        yield Label("", id="review-post-info", classes="review-post-preview")
        yield Static("Generated comment:")
        yield TextArea("", id="review-comment-area", read_only=True)
        with Static(classes="review-buttons"):
            yield Button("Approve [a]", id="btn-approve", variant="success")
            yield Button("Skip [x]", id="btn-skip", variant="default")
            yield Button("Edit [e]", id="btn-edit", variant="warning")
            yield Button("Regenerate [r]", id="btn-regenerate", variant="primary")

    def show_review(
        self, *, author: str, post_preview: str, comment_text: str
    ) -> None:
        self._current_comment = comment_text
        self.add_class("visible")
        try:
            self.query_one("#review-post-info", Label).update(
                f"Post by {author}: \"{post_preview[:80]}\""
            )
            area = self.query_one("#review-comment-area", TextArea)
            area.load_text(comment_text)
        except Exception:
            pass

    def hide_review(self) -> None:
        self._current_comment = ""
        self.remove_class("visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        decision_map = {
            "btn-approve": ReviewDecision.APPROVE,
            "btn-skip": ReviewDecision.SKIP,
            "btn-edit": ReviewDecision.EDIT,
            "btn-regenerate": ReviewDecision.REGENERATE,
        }
        button_id = event.button.id or ""
        decision = decision_map.get(button_id)
        if decision is None:
            return

        if decision == ReviewDecision.EDIT:
            try:
                area = self.query_one("#review-comment-area", TextArea)
                area.read_only = False
                area.focus()
            except Exception:
                pass
            return

        comment_text = self._current_comment
        try:
            area = self.query_one("#review-comment-area", TextArea)
            comment_text = area.text
        except Exception:
            pass

        self.post_message(self.Decided(decision=decision, comment_text=comment_text))
        self.hide_review()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_comment_review.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/widgets/comment_review.py tests/unit/test_comment_review.py
git commit -m "feat: add CommentReview widget with approve/skip/edit/regenerate"
```

---

### Task 8: Create Header Bar Widget

**Files:**
- Create: `src/tui/widgets/header_bar.py`
- Create: `tests/unit/test_header_bar.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_header_bar.py
"""Tests for the HeaderBar widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.header_bar import HeaderBar, BotMode


class HeaderApp(App):
    def compose(self) -> ComposeResult:
        yield HeaderBar()


class TestHeaderBar:
    @pytest.mark.asyncio
    async def test_initial_mode_is_auto(self):
        async with HeaderApp().run_test() as pilot:
            header = pilot.app.query_one(HeaderBar)
            assert header.mode == BotMode.AUTO

    @pytest.mark.asyncio
    async def test_toggle_mode(self):
        async with HeaderApp().run_test() as pilot:
            header = pilot.app.query_one(HeaderBar)
            header.toggle_mode()
            assert header.mode == BotMode.MANUAL
            header.toggle_mode()
            assert header.mode == BotMode.AUTO


class TestBotMode:
    def test_auto_value(self):
        assert BotMode.AUTO == "auto"

    def test_manual_value(self):
        assert BotMode.MANUAL == "manual"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_header_bar.py -v
```

Expected: FAIL

**Step 3: Write the HeaderBar widget**

```python
# src/tui/widgets/header_bar.py
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
        yield Label(f"Mode: {BotMode.AUTO.value.upper()}", id="mode-label", classes="header-mode")

    def toggle_mode(self) -> None:
        new_mode = BotMode.MANUAL if self.mode == BotMode.AUTO else BotMode.AUTO
        self.mode = new_mode

    def watch_mode(self, value: BotMode) -> None:
        try:
            self.query_one("#mode-label", Label).update(f"Mode: {value.value.upper()}")
        except Exception:
            pass
        self.post_message(self.ModeChanged(mode=value))
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_header_bar.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/widgets/header_bar.py tests/unit/test_header_bar.py
git commit -m "feat: add HeaderBar widget with mode toggle"
```

---

### Task 9: Create Bot Worker

**Files:**
- Create: `src/tui/workers/bot_worker.py`
- Create: `tests/unit/test_bot_worker.py`

The bot worker bridges the orchestrator callbacks to Textual messages. It implements `OrchestratorCallbacks` and posts Textual messages to the app.

**Step 1: Write the failing test**

```python
# tests/unit/test_bot_worker.py
"""Tests for the BotWorkerCallbacks bridge."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.tui.workers.bot_worker import BotWorkerCallbacks


class TestBotWorkerCallbacks:
    def test_on_post_found_posts_message(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        cb.on_post_found(
            post_url="https://linkedin.com/post/1",
            author_name="Jane",
            text_preview="Hello world",
        )
        app.call_from_thread.assert_called_once()

    def test_should_pause_reads_flag(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        assert cb.should_pause() is False
        cb.request_pause()
        assert cb.should_pause() is True
        cb.request_resume()
        assert cb.should_pause() is False

    def test_should_stop_reads_flag(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        assert cb.should_stop() is False
        cb.request_stop()
        assert cb.should_stop() is True

    def test_set_manual_mode(self):
        app = MagicMock()
        cb = BotWorkerCallbacks(app=app)
        assert cb.is_manual_mode is False
        cb.is_manual_mode = True
        assert cb.is_manual_mode is True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_bot_worker.py -v
```

Expected: FAIL

**Step 3: Write the BotWorkerCallbacks**

```python
# src/tui/workers/bot_worker.py
"""Bot worker bridge: translates orchestrator callbacks to Textual messages."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from src.core.callbacks import NullCallbacks
from src.tui.events import (
    BotError,
    BotPaused,
    BotStarted,
    BotStopped,
    CommentAwaitingApproval,
    CommentFailed,
    CommentGenerated,
    CommentPosted,
    PostFound,
    PostSkipped,
    StatsUpdated,
)

if TYPE_CHECKING:
    from textual.app import App


class BotWorkerCallbacks(NullCallbacks):
    """Bridges orchestrator callbacks to Textual messages.

    Runs in a worker thread. Uses `app.call_from_thread()` to safely
    post messages to the Textual event loop.
    """

    def __init__(self, app: "App") -> None:
        self._app = app
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._manual_mode = False
        self._approval_event = threading.Event()
        self._approval_decision: str = ""
        self._approval_text: str = ""

    @property
    def is_manual_mode(self) -> bool:
        return self._manual_mode

    @is_manual_mode.setter
    def is_manual_mode(self, value: bool) -> None:
        self._manual_mode = value

    def request_pause(self) -> None:
        self._pause_event.set()

    def request_resume(self) -> None:
        self._pause_event.clear()

    def request_stop(self) -> None:
        self._stop_event.set()

    def should_pause(self) -> bool:
        return self._pause_event.is_set()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def on_post_found(
        self, *, post_url: str, author_name: str, text_preview: str
    ) -> None:
        self._app.call_from_thread(
            self._app.post_message,
            PostFound(
                post_url=post_url,
                author_name=author_name,
                text_preview=text_preview,
            ),
        )

    def on_post_skipped(self, *, post_url: str, reason: str) -> None:
        self._app.call_from_thread(
            self._app.post_message,
            PostSkipped(post_url=post_url, reason=reason),
        )

    def on_comment_generated(
        self, *, post_url: str, author_name: str, comment_text: str
    ) -> None:
        self._app.call_from_thread(
            self._app.post_message,
            CommentGenerated(
                post_url=post_url,
                author_name=author_name,
                comment_text=comment_text,
            ),
        )

    def on_comment_posted(self, *, post_url: str, comment_text: str) -> None:
        self._app.call_from_thread(
            self._app.post_message,
            CommentPosted(post_url=post_url, comment_text=comment_text),
        )

    def on_comment_failed(self, *, post_url: str, error: str) -> None:
        self._app.call_from_thread(
            self._app.post_message,
            CommentFailed(post_url=post_url, error=error),
        )

    def on_stats_updated(
        self,
        *,
        comments_today: int,
        daily_limit: int,
        posts_scanned: int,
        posts_skipped: int,
        success_count: int,
        fail_count: int,
    ) -> None:
        self._app.call_from_thread(
            self._app.post_message,
            StatsUpdated(
                comments_today=comments_today,
                daily_limit=daily_limit,
                posts_scanned=posts_scanned,
                posts_skipped=posts_skipped,
                success_count=success_count,
                fail_count=fail_count,
            ),
        )

    def submit_approval(self, decision: str, comment_text: str) -> None:
        """Called from UI thread when user makes a review decision."""
        self._approval_decision = decision
        self._approval_text = comment_text
        self._approval_event.set()

    def wait_for_approval(self) -> tuple[str, str]:
        """Called from worker thread. Blocks until user decides."""
        self._approval_event.clear()
        self._approval_event.wait()
        return self._approval_decision, self._approval_text
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_bot_worker.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/workers/bot_worker.py tests/unit/test_bot_worker.py
git commit -m "feat: add BotWorkerCallbacks bridge for orchestrator-TUI communication"
```

---

### Task 10: Create Dashboard Screen

**Files:**
- Create: `src/tui/screens/dashboard.py`
- Create: `tests/unit/test_dashboard_screen.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_dashboard_screen.py
"""Tests for the Dashboard screen."""
from __future__ import annotations

import pytest
from textual.app import App

from src.tui.screens.dashboard import DashboardScreen
from src.tui.widgets.stats_panel import StatsPanel
from src.tui.widgets.live_feed import LiveFeed
from src.tui.widgets.header_bar import HeaderBar


class DashboardApp(App):
    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())


class TestDashboardScreen:
    @pytest.mark.asyncio
    async def test_dashboard_has_stats_panel(self):
        async with DashboardApp().run_test() as pilot:
            panels = pilot.app.query(StatsPanel)
            assert len(panels) == 1

    @pytest.mark.asyncio
    async def test_dashboard_has_live_feed(self):
        async with DashboardApp().run_test() as pilot:
            feeds = pilot.app.query(LiveFeed)
            assert len(feeds) == 1

    @pytest.mark.asyncio
    async def test_dashboard_has_header(self):
        async with DashboardApp().run_test() as pilot:
            headers = pilot.app.query(HeaderBar)
            assert len(headers) == 1

    @pytest.mark.asyncio
    async def test_keybinding_q_exits(self):
        async with DashboardApp().run_test() as pilot:
            await pilot.press("q")
            # App should have requested exit
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_dashboard_screen.py -v
```

Expected: FAIL

**Step 3: Write the Dashboard screen**

```python
# src/tui/screens/dashboard.py
"""Main dashboard screen with stats panel, live feed, and controls."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static

from src.tui.events import (
    CommentAwaitingApproval,
    CommentFailed,
    CommentGenerated,
    CommentPosted,
    PostFound,
    PostSkipped,
    StatsUpdated,
    BotStarted,
    BotStopped,
    BotError,
    BotPaused,
)
from src.tui.widgets.comment_review import CommentReview, ReviewDecision
from src.tui.widgets.header_bar import BotMode, HeaderBar
from src.tui.widgets.live_feed import LiveFeed
from src.tui.widgets.stats_panel import StatsPanel


class DashboardScreen(Screen):
    """Main dashboard with stats, live feed, and bot controls."""

    BINDINGS = [
        Binding("s", "start_bot", "Start", show=True),
        Binding("p", "pause_bot", "Pause", show=True),
        Binding("m", "toggle_mode", "Mode", show=True),
        Binding("c", "open_config", "Config", show=True),
        Binding("l", "open_log", "Log", show=True),
        Binding("q", "quit_app", "Quit", show=True),
    ]

    DEFAULT_CSS = """
    DashboardScreen {
        layout: vertical;
    }
    #dashboard-body {
        layout: horizontal;
        height: 1fr;
    }
    #stats-container {
        width: 30;
        height: 100%;
        border-right: solid $primary;
    }
    #feed-container {
        width: 1fr;
        height: 100%;
    }
    #status-bar {
        dock: bottom;
        width: 100%;
        height: 1;
        background: $surface;
        padding: 0 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bot_running = False

    def compose(self) -> ComposeResult:
        yield HeaderBar()
        with Horizontal(id="dashboard-body"):
            with Vertical(id="stats-container"):
                yield StatsPanel()
            with Vertical(id="feed-container"):
                yield LiveFeed()
                yield CommentReview()
        yield Static("STATUS: Idle | Press s to start", id="status-bar")
        yield Footer()

    def _update_status(self, text: str) -> None:
        try:
            self.query_one("#status-bar", Static).update(text)
        except Exception:
            pass

    # --- Keybinding actions ---

    def action_start_bot(self) -> None:
        if self._bot_running:
            return
        self._bot_running = True
        self._update_status("STATUS: Starting...")
        self.app.action_start_bot()

    def action_pause_bot(self) -> None:
        if not self._bot_running:
            return
        self.app.action_pause_bot()

    def action_toggle_mode(self) -> None:
        header = self.query_one(HeaderBar)
        header.toggle_mode()

    def action_open_config(self) -> None:
        self.app.action_open_config()

    def action_open_log(self) -> None:
        self.app.action_open_log()

    def action_quit_app(self) -> None:
        self.app.exit()

    # --- Event handlers ---

    def on_bot_started(self, event: BotStarted) -> None:
        self._bot_running = True
        feed = self.query_one(LiveFeed)
        feed.add_status("Bot started")
        self._update_status("STATUS: Running")

    def on_post_found(self, event: PostFound) -> None:
        feed = self.query_one(LiveFeed)
        feed.add_status(f"Found post by {event.author_name}")

    def on_post_skipped(self, event: PostSkipped) -> None:
        feed = self.query_one(LiveFeed)
        feed.add_skipped(event.reason)

    def on_comment_generated(self, event: CommentGenerated) -> None:
        feed = self.query_one(LiveFeed)
        feed.add_status(f"Generated comment for {event.author_name}")

    def on_comment_awaiting_approval(self, event: CommentAwaitingApproval) -> None:
        review = self.query_one(CommentReview)
        review.show_review(
            author=event.author_name,
            post_preview=event.post_preview,
            comment_text=event.comment_text,
        )
        self._update_status("STATUS: Awaiting approval | a:Approve x:Skip e:Edit r:Regenerate")

    def on_comment_posted(self, event: CommentPosted) -> None:
        feed = self.query_one(LiveFeed)
        author = event.post_url.split("/")[-1][:20]
        feed.add_posted(author, event.comment_text)

    def on_comment_failed(self, event: CommentFailed) -> None:
        feed = self.query_one(LiveFeed)
        feed.add_failed("post", event.error)

    def on_stats_updated(self, event: StatsUpdated) -> None:
        panel = self.query_one(StatsPanel)
        panel.update_stats(
            comments_today=event.comments_today,
            daily_limit=event.daily_limit,
            posts_scanned=event.posts_scanned,
            posts_skipped=event.posts_skipped,
            success_count=event.success_count,
            fail_count=event.fail_count,
        )
        header = self.query_one(HeaderBar)
        mode = header.mode.value.upper()
        self._update_status(
            f"STATUS: Running | {event.comments_today}/{event.daily_limit} comments | Mode: {mode}"
        )

    def on_bot_paused(self, event: BotPaused) -> None:
        self._update_status("STATUS: Paused | Press s to resume")
        feed = self.query_one(LiveFeed)
        feed.add_status("Bot paused")

    def on_bot_stopped(self, event: BotStopped) -> None:
        self._bot_running = False
        reason = f" ({event.reason})" if event.reason else ""
        self._update_status(f"STATUS: Stopped{reason} | Press s to start")
        feed = self.query_one(LiveFeed)
        feed.add_status(f"Bot stopped{reason}")

    def on_bot_error(self, event: BotError) -> None:
        self._bot_running = False
        self._update_status(f"STATUS: Error: {event.error}")
        feed = self.query_one(LiveFeed)
        feed.add_failed("bot", event.error)

    def on_comment_review_decided(self, event: CommentReview.Decided) -> None:
        self.app.handle_review_decision(event.decision, event.comment_text)
        self._update_status("STATUS: Running")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_dashboard_screen.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/screens/dashboard.py tests/unit/test_dashboard_screen.py
git commit -m "feat: add Dashboard screen with stats, live feed, and controls"
```

---

### Task 11: Create Onboarding Screen

**Files:**
- Create: `src/tui/screens/onboarding.py`
- Create: `tests/unit/test_onboarding_screen.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_onboarding_screen.py
"""Tests for the Onboarding wizard screen."""
from __future__ import annotations

import pytest
from textual.app import App

from src.tui.screens.onboarding import OnboardingScreen


class OnboardingApp(App):
    def on_mount(self) -> None:
        self.push_screen(OnboardingScreen())


class TestOnboardingScreen:
    @pytest.mark.asyncio
    async def test_starts_at_step_zero(self):
        async with OnboardingApp().run_test() as pilot:
            screen = pilot.app.query_one(OnboardingScreen)
            assert screen.current_step == 0

    @pytest.mark.asyncio
    async def test_has_welcome_content(self):
        async with OnboardingApp().run_test() as pilot:
            screen = pilot.app.query_one(OnboardingScreen)
            assert screen.current_step == 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_onboarding_screen.py -v
```

Expected: FAIL

**Step 3: Write the Onboarding screen**

```python
# src/tui/screens/onboarding.py
"""Onboarding wizard screen for first-time setup."""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
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

if TYPE_CHECKING:
    pass

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
    .step-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
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
        margin: 1 0;
    }
    .success-label {
        color: $success;
        margin: 1 0;
    }
    """

    class OnboardingComplete(Message):
        """Emitted when the user finishes onboarding."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_step = 0
        self._api_key = ""
        self._targets_feed = True
        self._targets_connections = True
        self._targets_keyword = ""
        self._max_posts = 10

    @property
    def current_step(self) -> int:
        return self._current_step

    def compose(self) -> ComposeResult:
        with Vertical(id="onboarding-container"):
            yield Static("", id="step-title", classes="step-title")
            yield Static("", id="step-subtitle", classes="step-subtitle")
            with VerticalScroll(id="step-content", classes="step-content"):
                yield Static("", id="step-body")
                yield Input(placeholder="Enter your Gemini API key", id="api-key-input")
                yield Label("", id="validation-label")
                yield Checkbox("Feed (your network posts)", id="cb-feed", value=True)
                yield Checkbox("Connections (direct connections)", id="cb-connections", value=True)
                yield Input(placeholder="Keyword (e.g. 'AI startup')", id="keyword-input")
                yield Input(placeholder="Max posts per target", id="max-posts-input", value="10")
            with Static(classes="nav-buttons"):
                yield Button("Back", id="btn-back", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button("Get Started", id="btn-start", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        self._render_step()

    def _render_step(self) -> None:
        step = self._current_step
        title = self.query_one("#step-title", Static)
        subtitle = self.query_one("#step-subtitle", Static)
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

        # Hide all dynamic elements
        api_input.display = False
        validation.display = False
        cb_feed.display = False
        cb_conn.display = False
        kw_input.display = False
        mp_input.display = False

        title.update(f"Step {step + 1}/5: {STEP_TITLES[step]}")
        btn_back.display = step > 0
        btn_next.display = step < 4
        btn_start.display = step == 0

        if step == 0:
            subtitle.update("LinkedIn Auto-Commenter")
            body.update(
                "This tool automatically discovers LinkedIn posts and "
                "leaves thoughtful, AI-generated comments.\n\n"
                "This wizard will guide you through:\n"
                "  1. Setting up your Gemini API key\n"
                "  2. Logging into LinkedIn\n"
                "  3. Configuring which posts to target\n"
                "  4. Previewing what the bot would do"
            )
            btn_start.display = True
            btn_next.display = False
        elif step == 1:
            subtitle.update("Enter your Google Gemini API key")
            body.update(
                "You need a Gemini API key to generate comments.\n"
                "Get one at: https://aistudio.google.com/apikey"
            )
            api_input.display = True
            validation.display = True
            btn_start.display = False
        elif step == 2:
            subtitle.update("Log into LinkedIn")
            body.update(
                "A browser window will open.\n"
                "Please log into your LinkedIn account.\n\n"
                "Once you see your LinkedIn feed, click Next."
            )
            btn_start.display = False
        elif step == 3:
            subtitle.update("Choose which posts to target")
            body.update("Select post sources and configure limits:")
            cb_feed.display = True
            cb_conn.display = True
            kw_input.display = True
            mp_input.display = True
            btn_start.display = False
        elif step == 4:
            subtitle.update("Preview")
            body.update(
                "Ready to run a dry preview.\n"
                "This will scan for posts but NOT post any comments.\n\n"
                "Click Next to finish setup."
            )
            btn_start.display = False
            btn_next.label = "Finish Setup"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-start":
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
                return False
            self._api_key = key
            validation.update("API key saved")
            validation.remove_class("error-label")
            validation.add_class("success-label")
        return True

    def _finish_onboarding(self) -> None:
        # Save API key to .env
        env_path = Path(".env")
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()
        new_lines = [l for l in lines if not l.startswith("GEMINI_API_KEY=")]
        new_lines.append(f"GEMINI_API_KEY={self._api_key}")
        env_path.write_text("\n".join(new_lines) + "\n")

        # Build config targets
        self._targets_feed = self.query_one("#cb-feed", Checkbox).value
        self._targets_connections = self.query_one("#cb-connections", Checkbox).value
        self._targets_keyword = self.query_one("#keyword-input", Input).value.strip()

        self.post_message(self.OnboardingComplete())
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_onboarding_screen.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/screens/onboarding.py tests/unit/test_onboarding_screen.py
git commit -m "feat: add Onboarding wizard screen with 5-step setup flow"
```

---

### Task 12: Create Config Editor Screen

**Files:**
- Create: `src/tui/screens/config_editor.py`
- Create: `tests/unit/test_config_editor.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_config_editor.py
"""Tests for the ConfigEditor screen."""
from __future__ import annotations

import pytest
from textual.app import App

from src.tui.screens.config_editor import ConfigEditorScreen


class ConfigApp(App):
    BINDINGS = []

    def on_mount(self) -> None:
        self.push_screen(ConfigEditorScreen())


class TestConfigEditorScreen:
    @pytest.mark.asyncio
    async def test_screen_renders(self):
        async with ConfigApp().run_test() as pilot:
            screen = pilot.app.query_one(ConfigEditorScreen)
            assert screen is not None

    @pytest.mark.asyncio
    async def test_escape_pops_screen(self):
        async with ConfigApp().run_test() as pilot:
            await pilot.press("escape")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_config_editor.py -v
```

Expected: FAIL

**Step 3: Write the ConfigEditor screen**

```python
# src/tui/screens/config_editor.py
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
        margin-bottom: 0;
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

    def __init__(self, config_path: str = "config.yaml", **kwargs) -> None:
        super().__init__(**kwargs)
        self._config_path = config_path
        self._raw_config: dict = {}

    def compose(self) -> ComposeResult:
        yield Static("CONFIGURATION", id="config-title")
        with VerticalScroll(id="config-scroll"):
            # Limits section
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

            # AI section
            with Vertical(classes="config-section"):
                yield Static("AI SETTINGS", classes="config-section-title")
                with Static(classes="config-field"):
                    yield Label("Model:")
                    yield Input(value="gemini-3-flash-preview", id="cfg-model")
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
            yaml.dump(self._raw_config, f, default_flow_style=False, sort_keys=False)
        status.update("Config saved successfully")

    def _validate_and_collect(self) -> list[str]:
        errors: list[str] = []

        def _int_field(field_id: str, key: str, section: str, min_val: int, max_val: int) -> None:
            try:
                val = int(self.query_one(f"#{field_id}", Input).value)
                if val < min_val or val > max_val:
                    errors.append(f"{key} must be {min_val}-{max_val}")
                    return
                self._raw_config.setdefault(section, {})[key] = val
            except ValueError:
                errors.append(f"{key} must be a number")

        def _float_field(field_id: str, key: str, section: str, min_val: float, max_val: float) -> None:
            try:
                val = float(self.query_one(f"#{field_id}", Input).value)
                if val < min_val or val > max_val:
                    errors.append(f"{key} must be {min_val}-{max_val}")
                    return
                self._raw_config.setdefault(section, {})[key] = val
            except ValueError:
                errors.append(f"{key} must be a number")

        _int_field("cfg-daily-limit", "daily_comment_limit", "limits", 1, 100)
        _int_field("cfg-min-delay", "min_delay_seconds", "limits", 5, 300)
        _int_field("cfg-max-delay", "max_delay_seconds", "limits", 10, 600)
        _int_field("cfg-min-reactions", "min_reactions", "limits", 0, 1000)
        _int_field("cfg-min-comments", "min_comments", "limits", 0, 100)
        _float_field("cfg-temperature", "temperature", "ai", 0.0, 2.0)

        model = self.query_one("#cfg-model", Input).value.strip()
        if model:
            self._raw_config.setdefault("ai", {})["model_name"] = model

        return errors
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_config_editor.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/screens/config_editor.py tests/unit/test_config_editor.py
git commit -m "feat: add ConfigEditor screen with form-based config editing"
```

---

### Task 13: Create Activity Log Screen

**Files:**
- Create: `src/tui/screens/activity_log.py`
- Create: `tests/unit/test_activity_log_screen.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_activity_log_screen.py
"""Tests for the ActivityLog screen."""
from __future__ import annotations

import pytest
from textual.app import App

from src.tui.screens.activity_log import ActivityLogScreen


class LogApp(App):
    BINDINGS = []

    def on_mount(self) -> None:
        self.push_screen(ActivityLogScreen(db_path=":memory:"))


class TestActivityLogScreen:
    @pytest.mark.asyncio
    async def test_screen_renders(self):
        async with LogApp().run_test() as pilot:
            screen = pilot.app.query_one(ActivityLogScreen)
            assert screen is not None

    @pytest.mark.asyncio
    async def test_escape_pops_screen(self):
        async with LogApp().run_test() as pilot:
            await pilot.press("escape")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_activity_log_screen.py -v
```

Expected: FAIL

**Step 3: Write the ActivityLog screen**

```python
# src/tui/screens/activity_log.py
"""Activity log screen showing historical comment data."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from src.storage.activity_log import ActivityLog


class ActivityLogScreen(Screen):
    """Displays historical activity from the SQLite database."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("f", "filter_toggle", "Filter", show=True),
    ]

    DEFAULT_CSS = """
    ActivityLogScreen {
        layout: vertical;
    }
    #log-title {
        dock: top;
        width: 100%;
        height: 3;
        text-style: bold;
        content-align: center middle;
        background: $primary;
    }
    #log-summary {
        height: 1;
        padding: 0 2;
        background: $surface;
    }
    DataTable {
        height: 1fr;
    }
    #log-status {
        dock: bottom;
        width: 100%;
        height: 1;
        background: $surface;
        padding: 0 2;
    }
    """

    def __init__(self, db_path: str = "data/activity.db", **kwargs) -> None:
        super().__init__(**kwargs)
        self._db_path = db_path
        self._filter_status: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("ACTIVITY LOG", id="log-title")
        yield Static("", id="log-summary")
        yield DataTable(id="log-table")
        yield Static("Esc:Back  Up/Down:Scroll  Enter:Details  f:Filter", id="log-status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.add_columns("#", "STATUS", "TIME (UTC)", "POST URL", "COMMENT")
        self._load_data()

    def _load_data(self) -> None:
        try:
            log = ActivityLog(db_path=self._db_path)
            records = log.get_recent(limit=100)
            stats = log.get_daily_stats()
        except Exception:
            return

        summary = self.query_one("#log-summary", Static)
        summary.update(
            f"  Today: {stats.successful} posted, {stats.failed} failed | "
            f"Total shown: {len(records)}"
        )

        table = self.query_one("#log-table", DataTable)
        table.clear()

        for record in records:
            if self._filter_status and record.status != self._filter_status:
                continue
            status_text = "OK" if record.status == "success" else "FAIL"
            time_str = record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            short_url = record.post_url[-40:] if len(record.post_url) > 40 else record.post_url
            preview = record.comment_text[:50].replace("\n", " ")
            table.add_row(
                str(record.id),
                status_text,
                time_str,
                short_url,
                preview,
                key=str(record.id),
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_filter_toggle(self) -> None:
        if self._filter_status is None:
            self._filter_status = "success"
        elif self._filter_status == "success":
            self._filter_status = "failed"
        else:
            self._filter_status = None

        status = self.query_one("#log-status", Static)
        filter_text = f" | Filter: {self._filter_status}" if self._filter_status else ""
        status.update(f"Esc:Back  Up/Down:Scroll  f:Filter{filter_text}")
        self._load_data()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_activity_log_screen.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/screens/activity_log.py tests/unit/test_activity_log_screen.py
git commit -m "feat: add ActivityLog screen with DataTable and filtering"
```

---

### Task 14: Create Main TUI App

**Files:**
- Create: `src/tui/app.py`
- Create: `tests/unit/test_tui_app.py`

This is the main `App` class that wires everything together: screen routing, bot worker lifecycle, and review decisions.

**Step 1: Write the failing test**

```python
# tests/unit/test_tui_app.py
"""Tests for the main TUI App."""
from __future__ import annotations

import pytest

from src.tui.app import LinkedInAutoCommenterApp


class TestApp:
    @pytest.mark.asyncio
    async def test_app_launches(self):
        app = LinkedInAutoCommenterApp()
        async with app.run_test() as pilot:
            assert pilot.app is not None

    @pytest.mark.asyncio
    async def test_app_shows_dashboard_by_default(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            from src.tui.screens.dashboard import DashboardScreen
            assert isinstance(pilot.app.screen, DashboardScreen)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_tui_app.py -v
```

Expected: FAIL

**Step 3: Write the main App**

```python
# src/tui/app.py
"""Main Textual application for LinkedIn Auto-Commenter."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static

from src.tui.screens.activity_log import ActivityLogScreen
from src.tui.screens.config_editor import ConfigEditorScreen
from src.tui.screens.dashboard import DashboardScreen
from src.tui.screens.onboarding import OnboardingScreen
from src.tui.widgets.comment_review import ReviewDecision
from src.tui.workers.bot_worker import BotWorkerCallbacks

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LinkedInAutoCommenterApp(App):
    """LinkedIn Auto-Commenter TUI Application."""

    TITLE = "LinkedIn Auto-Commenter"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def __init__(self, skip_onboarding: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._skip_onboarding = skip_onboarding
        self._worker_callbacks: BotWorkerCallbacks | None = None

    def on_mount(self) -> None:
        if self._skip_onboarding or self._onboarding_complete():
            self.push_screen(DashboardScreen())
        else:
            self.push_screen(OnboardingScreen())

    def _onboarding_complete(self) -> bool:
        """Check if onboarding has been completed (API key exists and config exists)."""
        env_path = Path(".env")
        config_path = Path("config.yaml")
        if not env_path.exists() or not config_path.exists():
            return False
        env_text = env_path.read_text()
        return "GEMINI_API_KEY=" in env_text and len(
            env_text.split("GEMINI_API_KEY=")[1].split("\n")[0].strip()
        ) > 0

    def on_onboarding_screen_onboarding_complete(
        self, event: OnboardingScreen.OnboardingComplete
    ) -> None:
        self.pop_screen()
        self.push_screen(DashboardScreen())

    # --- Bot control actions (called by DashboardScreen) ---

    def action_start_bot(self) -> None:
        self._run_bot()

    def action_pause_bot(self) -> None:
        if self._worker_callbacks:
            if self._worker_callbacks.should_pause():
                self._worker_callbacks.request_resume()
            else:
                self._worker_callbacks.request_pause()

    def action_open_config(self) -> None:
        self.push_screen(ConfigEditorScreen())

    def action_open_log(self) -> None:
        from src.core.config import load_config
        try:
            config = load_config("config.yaml")
            db_path = config.db_path
        except Exception:
            db_path = "data/activity.db"
        self.push_screen(ActivityLogScreen(db_path=db_path))

    def handle_review_decision(self, decision: ReviewDecision, comment_text: str) -> None:
        if self._worker_callbacks:
            self._worker_callbacks.submit_approval(decision.value, comment_text)

    @work(thread=True)
    def _run_bot(self) -> None:
        """Run the bot pipeline in a background thread."""
        import asyncio as aio

        from src.ai.comment_generator import CommentGenerator
        from src.ai.gemini_client import GeminiClient
        from src.core.config import load_config
        from src.core.orchestrator import Orchestrator
        from src.core.rate_limiter import RateLimiter
        from src.executor.comment_poster import CommentPoster
        from src.executor.human_typer import HumanTyper
        from src.scraper.browser_factory import create_persistent_context
        from src.scraper.linkedin_scraper import LinkedInScraper
        from src.storage.activity_log import ActivityLog
        from src.tui.events import BotError, BotStarted, BotStopped

        self._worker_callbacks = BotWorkerCallbacks(app=self)

        self.call_from_thread(self.post_message, BotStarted())

        try:
            config = load_config("config.yaml")
            activity_log = ActivityLog(db_path=config.db_path)
            rate_limiter = RateLimiter(
                activity_log=activity_log,
                daily_limit=config.limits.daily_comment_limit,
            )

            status = rate_limiter.check_status()
            if status.limit_reached:
                self.call_from_thread(
                    self.post_message,
                    BotStopped(reason="Daily limit already reached"),
                )
                return

            human_typer = HumanTyper(
                min_wpm=config.limits.min_wpm,
                max_wpm=config.limits.max_wpm,
            )
            gemini_client = GeminiClient(
                model_name=config.ai.model_name,
                temperature=config.ai.temperature,
                max_output_tokens=config.ai.max_output_tokens,
            )
            comment_generator = CommentGenerator(client=gemini_client, config=config.ai)

            loop = aio.new_event_loop()
            aio.set_event_loop(loop)

            async def _run_pipeline() -> None:
                async with create_persistent_context(
                    user_data_dir=config.browser.user_data_dir,
                    headless=config.browser.headless,
                    viewport_width=config.browser.viewport_width,
                    viewport_height=config.browser.viewport_height,
                ) as (_, context):
                    scraper = LinkedInScraper(
                        context=context,
                        activity_log=activity_log,
                        min_reactions=config.limits.min_reactions,
                        min_comments=config.limits.min_comments,
                    )
                    comment_poster = CommentPoster(
                        context=context, human_typer=human_typer
                    )

                    orchestrator = Orchestrator(
                        config=config,
                        rate_limiter=rate_limiter,
                        scraper=scraper,
                        comment_generator=comment_generator,
                        comment_poster=comment_poster,
                        activity_log=activity_log,
                        callbacks=self._worker_callbacks,
                    )

                    await orchestrator.run()

            loop.run_until_complete(_run_pipeline())
            loop.close()

            self.call_from_thread(
                self.post_message,
                BotStopped(reason="Pipeline complete"),
            )

        except Exception as exc:
            logger.exception("Bot worker error")
            self.call_from_thread(
                self.post_message,
                BotError(error=str(exc)),
            )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_tui_app.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/app.py tests/unit/test_tui_app.py
git commit -m "feat: add main TUI App with screen routing and bot worker lifecycle"
```

---

### Task 15: Update Entry Point

**Files:**
- Modify: `main.py`

Replace the CLI entry point with the TUI app launcher, keeping `--report` as a fallback.

**Step 1: No test needed — this is a thin entry point**

**Step 2: Modify main.py**

Replace the `if __name__ == "__main__"` block and simplify. Keep the `show_report` function and `--report` flag. Replace the default behavior with the TUI:

```python
# At the bottom of main.py, replace lines 174-190 with:

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Auto-Commenter")
    parser.add_argument(
        "--report", action="store_true", help="Show activity log and exit"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of records to show in report (default 50)"
    )
    parser.add_argument(
        "--no-tui", action="store_true", help="Run without TUI (original CLI mode)"
    )
    args = parser.parse_args()

    if args.report:
        from src.core.config import load_config
        cfg = load_config("config.yaml")
        show_report(db_path=cfg.db_path, limit=args.limit)
    elif args.no_tui:
        asyncio.run(main())
    else:
        from src.tui.app import LinkedInAutoCommenterApp
        app = LinkedInAutoCommenterApp()
        app.run()
```

**Step 3: Test manually**

```bash
python main.py --help
```

Expected: Shows help with `--report`, `--limit`, and `--no-tui` flags.

```bash
python main.py
```

Expected: TUI launches.

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: replace CLI entry point with TUI, keep --no-tui fallback"
```

---

### Task 16: Add Manual Approval to Orchestrator

**Files:**
- Modify: `src/core/callbacks.py` (add `on_awaiting_approval` and `wait_for_approval` methods)
- Modify: `src/core/orchestrator.py` (add manual mode check after comment generation)
- Modify: `src/tui/workers/bot_worker.py` (implement manual approval flow)

**Step 1: Write the failing test**

```python
# tests/unit/test_manual_approval.py
"""Tests for manual approval flow in orchestrator."""
from __future__ import annotations

from src.core.callbacks import NullCallbacks


class TestManualApprovalCallbacks:
    def test_null_callbacks_on_awaiting_approval(self):
        cb = NullCallbacks()
        result = cb.on_awaiting_approval(
            post_url="url",
            author_name="name",
            post_preview="preview",
            comment_text="comment",
        )
        # NullCallbacks returns ("approve", original_text) by default
        assert result == ("approve", "comment")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_manual_approval.py -v
```

Expected: FAIL — `NullCallbacks` has no `on_awaiting_approval` method

**Step 3: Add `on_awaiting_approval` to callbacks**

In `src/core/callbacks.py`, add to the `OrchestratorCallbacks` protocol:

```python
def on_awaiting_approval(
    self,
    *,
    post_url: str,
    author_name: str,
    post_preview: str,
    comment_text: str,
) -> tuple[str, str]:
    """Called in manual mode. Returns (decision, comment_text).

    decision is one of: "approve", "skip", "regenerate"
    comment_text may be edited by the user.
    """
    ...
```

And add the implementation to `NullCallbacks`:

```python
def on_awaiting_approval(
    self,
    *,
    post_url: str,
    author_name: str,
    post_preview: str,
    comment_text: str,
) -> tuple[str, str]:
    return ("approve", comment_text)
```

**Step 4: Add manual mode check to orchestrator**

In `src/core/orchestrator.py`, after comment generation succeeds (after the `on_comment_generated` callback), add:

```python
# Manual approval check
decision, final_text = self._callbacks.on_awaiting_approval(
    post_url=post.post_url,
    author_name=post.author_name,
    post_preview=post.post_text[:100],
    comment_text=generate_result.comment.text,
)

if decision == "skip":
    logger.info("Comment skipped by user for %s", post.post_url)
    continue
elif decision == "regenerate":
    # Re-generate (simple retry; could loop but keep it simple)
    generate_result = self._generator.generate(post)
    if generate_result.error:
        raise RuntimeError(f"Regeneration failed: {generate_result.error}")
    final_text = generate_result.comment.text

# Use final_text (possibly edited) for posting
from dataclasses import replace as dc_replace
final_comment = dc_replace(generate_result.comment, text=final_text)
```

Then update the `post_comment` and `record_comment` calls to use `final_comment` instead of `generate_result.comment`.

**Step 5: Implement in BotWorkerCallbacks**

In `src/tui/workers/bot_worker.py`, add:

```python
def on_awaiting_approval(
    self,
    *,
    post_url: str,
    author_name: str,
    post_preview: str,
    comment_text: str,
) -> tuple[str, str]:
    if not self._manual_mode:
        return ("approve", comment_text)

    # Post the awaiting approval message to UI
    self._app.call_from_thread(
        self._app.post_message,
        CommentAwaitingApproval(
            post_url=post_url,
            author_name=author_name,
            post_preview=post_preview,
            comment_text=comment_text,
        ),
    )

    # Block until user decides
    decision, text = self.wait_for_approval()
    return (decision, text)
```

**Step 6: Run test to verify it passes**

```bash
pytest tests/unit/test_manual_approval.py -v
```

Expected: PASS

**Step 7: Run all tests**

```bash
pytest tests/ -v
```

Expected: all PASS

**Step 8: Commit**

```bash
git add src/core/callbacks.py src/core/orchestrator.py src/tui/workers/bot_worker.py tests/unit/test_manual_approval.py
git commit -m "feat: add manual approval flow through orchestrator callbacks"
```

---

### Task 17: Add Keybindings for Manual Review

**Files:**
- Modify: `src/tui/screens/dashboard.py` (add key bindings for a/x/e/r in review mode)

**Step 1: Write the failing test**

```python
# tests/unit/test_dashboard_keybindings.py
"""Tests for dashboard keybindings."""
from __future__ import annotations

import pytest
from textual.app import App

from src.tui.screens.dashboard import DashboardScreen
from src.tui.widgets.comment_review import CommentReview


class KeybindApp(App):
    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())


class TestDashboardKeybindings:
    @pytest.mark.asyncio
    async def test_m_toggles_mode(self):
        async with KeybindApp().run_test() as pilot:
            from src.tui.widgets.header_bar import HeaderBar, BotMode
            header = pilot.app.query_one(HeaderBar)
            assert header.mode == BotMode.AUTO
            await pilot.press("m")
            assert header.mode == BotMode.MANUAL
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_dashboard_keybindings.py -v
```

Expected: May pass or fail depending on binding wiring.

**Step 3: Add review-mode keybindings to DashboardScreen**

In `src/tui/screens/dashboard.py`, add these bindings:

```python
BINDINGS = [
    Binding("s", "start_bot", "Start", show=True),
    Binding("p", "pause_bot", "Pause", show=True),
    Binding("m", "toggle_mode", "Mode", show=True),
    Binding("c", "open_config", "Config", show=True),
    Binding("l", "open_log", "Log", show=True),
    Binding("q", "quit_app", "Quit", show=True),
    Binding("a", "approve_comment", "Approve", show=False),
    Binding("x", "skip_comment", "Skip", show=False),
    Binding("e", "edit_comment", "Edit", show=False),
    Binding("r", "regenerate_comment", "Regenerate", show=False),
]
```

And add the action methods:

```python
def action_approve_comment(self) -> None:
    review = self.query_one(CommentReview)
    if review.is_visible:
        review.post_message(
            CommentReview.Decided(
                decision=ReviewDecision.APPROVE,
                comment_text=review.current_comment,
            )
        )
        review.hide_review()

def action_skip_comment(self) -> None:
    review = self.query_one(CommentReview)
    if review.is_visible:
        review.post_message(
            CommentReview.Decided(
                decision=ReviewDecision.SKIP,
                comment_text=review.current_comment,
            )
        )
        review.hide_review()

def action_edit_comment(self) -> None:
    review = self.query_one(CommentReview)
    if review.is_visible:
        try:
            from textual.widgets import TextArea
            area = review.query_one("#review-comment-area", TextArea)
            area.read_only = False
            area.focus()
        except Exception:
            pass

def action_regenerate_comment(self) -> None:
    review = self.query_one(CommentReview)
    if review.is_visible:
        review.post_message(
            CommentReview.Decided(
                decision=ReviewDecision.REGENERATE,
                comment_text=review.current_comment,
            )
        )
        review.hide_review()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_dashboard_keybindings.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/tui/screens/dashboard.py tests/unit/test_dashboard_keybindings.py
git commit -m "feat: add keybindings for manual review mode (a/x/e/r)"
```

---

### Task 18: Wire Mode Toggle to Worker

**Files:**
- Modify: `src/tui/screens/dashboard.py`
- Modify: `src/tui/app.py`

When HeaderBar mode changes, update the worker's `is_manual_mode` flag.

**Step 1: Add handler in DashboardScreen**

In `src/tui/screens/dashboard.py`, add a handler for `HeaderBar.ModeChanged`:

```python
def on_header_bar_mode_changed(self, event: HeaderBar.ModeChanged) -> None:
    self.app.set_bot_mode(event.mode)
    mode_text = event.mode.value.upper()
    self._update_status(f"STATUS: Mode changed to {mode_text}")
```

**Step 2: Add `set_bot_mode` to App**

In `src/tui/app.py`, add:

```python
def set_bot_mode(self, mode: "BotMode") -> None:
    from src.tui.widgets.header_bar import BotMode
    if self._worker_callbacks:
        self._worker_callbacks.is_manual_mode = (mode == BotMode.MANUAL)
```

**Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: all PASS

**Step 4: Commit**

```bash
git add src/tui/screens/dashboard.py src/tui/app.py
git commit -m "feat: wire mode toggle to worker manual mode flag"
```

---

### Task 19: End-to-End Smoke Test

**Files:**
- Create: `tests/integration/test_tui_smoke.py`

A smoke test that launches the TUI app, verifies key screens render, and exits cleanly.

**Step 1: Write the smoke test**

```python
# tests/integration/test_tui_smoke.py
"""Smoke tests for the TUI application."""
from __future__ import annotations

import pytest

from src.tui.app import LinkedInAutoCommenterApp
from src.tui.screens.dashboard import DashboardScreen
from src.tui.widgets.header_bar import HeaderBar, BotMode
from src.tui.widgets.live_feed import LiveFeed
from src.tui.widgets.stats_panel import StatsPanel


class TestTUISmoke:
    @pytest.mark.asyncio
    async def test_app_starts_with_dashboard(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            assert isinstance(pilot.app.screen, DashboardScreen)
            assert len(pilot.app.query(StatsPanel)) == 1
            assert len(pilot.app.query(LiveFeed)) == 1
            assert len(pilot.app.query(HeaderBar)) == 1

    @pytest.mark.asyncio
    async def test_toggle_mode(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            header = pilot.app.query_one(HeaderBar)
            assert header.mode == BotMode.AUTO
            await pilot.press("m")
            assert header.mode == BotMode.MANUAL
            await pilot.press("m")
            assert header.mode == BotMode.AUTO

    @pytest.mark.asyncio
    async def test_open_config_and_back(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.press("c")
            from src.tui.screens.config_editor import ConfigEditorScreen
            assert isinstance(pilot.app.screen, ConfigEditorScreen)
            await pilot.press("escape")
            assert isinstance(pilot.app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_open_log_and_back(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.press("l")
            from src.tui.screens.activity_log import ActivityLogScreen
            assert isinstance(pilot.app.screen, ActivityLogScreen)
            await pilot.press("escape")
            assert isinstance(pilot.app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_quit(self):
        app = LinkedInAutoCommenterApp(skip_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.press("q")
```

**Step 2: Run the smoke tests**

```bash
pytest tests/integration/test_tui_smoke.py -v
```

Expected: all PASS

**Step 3: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all PASS

**Step 4: Commit**

```bash
git add tests/integration/test_tui_smoke.py
git commit -m "test: add TUI smoke tests for screen navigation and keybindings"
```

---

### Task 20: Final Verification and Cleanup

**Step 1: Run full test suite with coverage**

```bash
pytest tests/ -v --tb=short
```

Expected: all PASS

**Step 2: Verify the TUI launches**

```bash
python main.py
```

Expected: TUI renders with dashboard, stats panel, live feed, footer with keybindings.

**Step 3: Verify --no-tui still works**

```bash
python main.py --no-tui --help
```

Expected: Original CLI behavior.

**Step 4: Verify --report still works**

```bash
python main.py --report --limit 5
```

Expected: Shows activity report or "No activity recorded yet."

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup for TUI dashboard implementation"
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | Package setup | requirements.txt, src/tui/*/__init__.py |
| 2 | Custom events | src/tui/events.py |
| 3 | Callback protocol | src/core/callbacks.py |
| 4 | Orchestrator callbacks | src/core/orchestrator.py |
| 5 | Stats panel widget | src/tui/widgets/stats_panel.py |
| 6 | Live feed widget | src/tui/widgets/live_feed.py |
| 7 | Comment review widget | src/tui/widgets/comment_review.py |
| 8 | Header bar widget | src/tui/widgets/header_bar.py |
| 9 | Bot worker bridge | src/tui/workers/bot_worker.py |
| 10 | Dashboard screen | src/tui/screens/dashboard.py |
| 11 | Onboarding screen | src/tui/screens/onboarding.py |
| 12 | Config editor screen | src/tui/screens/config_editor.py |
| 13 | Activity log screen | src/tui/screens/activity_log.py |
| 14 | Main TUI app | src/tui/app.py |
| 15 | Entry point update | main.py |
| 16 | Manual approval flow | callbacks + orchestrator + worker |
| 17 | Review keybindings | src/tui/screens/dashboard.py |
| 18 | Mode toggle wiring | dashboard + app |
| 19 | Smoke tests | tests/integration/test_tui_smoke.py |
| 20 | Final verification | All files |
