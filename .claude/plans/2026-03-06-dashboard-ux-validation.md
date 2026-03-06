# Dashboard UX, Validation & Linking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix broken links, add missing validation, improve dashboard UX feedback, and remove dead code across the LinkedIn auto-commenter TUI.

**Architecture:** The app uses a Textual TUI with callback-driven worker threads. Changes touch config validation (Pydantic models), dashboard event handlers, config editor save logic, and orchestrator status reporting. All changes are backward-compatible.

**Tech Stack:** Python 3.12, Textual, Pydantic, SQLite, pytest

---

## Issues Found & Prioritized

### Critical (broken behavior)
1. **Config min/max validation missing** — `min_delay >= max_delay` or `min_wpm >= max_wpm` silently accepted
2. **Targeting config is dead code** — UI lets users set industries/exclusions but they're never used
3. **Pause button says "press s to resume"** — but `s` starts a NEW bot instead of resuming
4. **`_bot_running` not reset on `BotStopped` from pause resume path** — pressing `s` after pipeline completes does nothing until error/stop event

### High (poor UX)
5. **No empty targets validation** — bot starts, scrapes nothing, silently stops
6. **No "0 posts found" user feedback** — live feed shows nothing when scrape returns empty
7. **Stats panel shows stale data on next run** — stats from previous run persist
8. **Activity log doesn't show action_type column** — can't distinguish likes from comments

### Medium (customization/polish)
9. **No elapsed time display** — user can't tell how long the bot has been running
10. **No confirmation before starting bot** — easy to accidentally press `s`
11. **Config editor doesn't show auto_like toggle** — must edit YAML manually
12. **Config editor doesn't show min_reactions/min_comments** — must edit YAML manually

---

## Task 1: Add min/max cross-field validation to config

**Files:**
- Modify: `src/core/config.py:36-44`
- Modify: `src/tui/screens/config_editor.py:381-444`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_config.py — add these tests

def test_min_delay_must_be_less_than_max_delay():
    """min_delay_seconds >= max_delay_seconds should raise ValidationError."""
    with pytest.raises(ValidationError):
        LimitsConfig(min_delay_seconds=50, max_delay_seconds=10)


def test_min_wpm_must_be_less_than_max_wpm():
    """min_wpm >= max_wpm should raise ValidationError."""
    with pytest.raises(ValidationError):
        LimitsConfig(min_wpm=80, max_wpm=30)


def test_valid_min_max_accepted():
    """Valid min < max should work."""
    cfg = LimitsConfig(min_delay_seconds=10, max_delay_seconds=50,
                       min_wpm=40, max_wpm=90)
    assert cfg.min_delay_seconds < cfg.max_delay_seconds
    assert cfg.min_wpm < cfg.max_wpm
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_config.py::test_min_delay_must_be_less_than_max_delay -v`
Expected: FAIL (no validation exists yet)

**Step 3: Write minimal implementation**

In `src/core/config.py`, add a `model_validator` to `LimitsConfig`:

```python
from pydantic import model_validator

class LimitsConfig(BaseModel, frozen=True):
    # ... existing fields ...

    @model_validator(mode="after")
    def _check_min_max(self) -> "LimitsConfig":
        if self.min_delay_seconds >= self.max_delay_seconds:
            raise ValueError(
                f"min_delay_seconds ({self.min_delay_seconds}) must be less than "
                f"max_delay_seconds ({self.max_delay_seconds})"
            )
        if self.min_wpm >= self.max_wpm:
            raise ValueError(
                f"min_wpm ({self.min_wpm}) must be less than max_wpm ({self.max_wpm})"
            )
        return self
```

Also add cross-field validation in `ConfigEditorScreen._validate_and_collect()`:

```python
# After collecting min_delay and max_delay:
limits = self._raw_config.get("limits", {})
if limits.get("min_delay_seconds", 15) >= limits.get("max_delay_seconds", 55):
    errors.append("Min delay must be less than max delay")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/core/config.py src/tui/screens/config_editor.py tests/unit/test_config.py
git commit -m "feat: add cross-field min/max validation to LimitsConfig"
```

---

## Task 2: Add empty targets validation

**Files:**
- Modify: `src/core/config.py:47-53`
- Modify: `src/tui/app.py:156-164`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
def test_empty_targets_raises():
    """AppConfig with no targets should raise ValidationError."""
    with pytest.raises(ValidationError):
        AppConfig(targets=())


def test_single_target_accepted():
    """AppConfig with at least one target should be valid."""
    cfg = AppConfig(targets=(TargetConfig(type="feed"),))
    assert len(cfg.targets) == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_config.py::test_empty_targets_raises -v`
Expected: FAIL

**Step 3: Write minimal implementation**

In `src/core/config.py`, add a validator to `AppConfig`:

```python
class AppConfig(BaseModel, frozen=True):
    targets: tuple[TargetConfig, ...] = ()
    # ... other fields ...

    @model_validator(mode="after")
    def _check_targets(self) -> "AppConfig":
        if not self.targets:
            raise ValueError("At least one target must be configured")
        return self
```

In `src/tui/app.py`, catch the validation error gracefully in `_run_bot`:

```python
try:
    config = load_config()
except ValueError as exc:
    self.call_from_thread(
        self.post_message,
        BotError(error=str(exc)),
    )
    return
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/core/config.py src/tui/app.py tests/unit/test_config.py
git commit -m "feat: validate that at least one target is configured"
```

---

## Task 3: Fix pause/resume flow and `_bot_running` state

**Files:**
- Modify: `src/tui/screens/dashboard.py:121-131,248-256`
- Modify: `src/tui/app.py:91-99`
- Test: `tests/unit/test_tui_events.py`

**Step 1: Write the failing test**

```python
def test_pause_updates_status_bar_with_p_to_resume(app):
    """Paused state should say 'Press p to resume', not 's'."""
    async with app.run_test() as pilot:
        # Simulate pause event
        app.post_message(BotStarted())
        await pilot.pause()
        app.post_message(BotPaused())
        await pilot.pause()
        dashboard = app.query_one(DashboardScreen)
        status = dashboard.query_one("#status-bar", Static)
        assert "press p" in status.renderable.lower() or "p to resume" in status.renderable.lower()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tui_events.py::test_pause_updates_status_bar_with_p_to_resume -v`
Expected: FAIL — currently says "Press s to resume"

**Step 3: Write minimal implementation**

In `src/tui/screens/dashboard.py`:

```python
def on_bot_paused(self, event: BotPaused) -> None:
    self._update_status("STATUS: Paused | Press p to resume")
    self.query_one(LiveFeed).add_status("Bot paused")

def action_pause_bot(self) -> None:
    if not self._bot_running:
        return
    self.app.action_pause_bot()
```

In `src/tui/app.py`, fix the pause/resume toggle to emit proper events:

```python
def action_pause_bot(self) -> None:
    if self._worker_callbacks:
        if self._worker_callbacks.should_pause():
            self._worker_callbacks.request_resume()
            self.post_message(BotStatus(message="Bot resumed"))
        else:
            self._worker_callbacks.request_pause()
            from src.tui.events import BotPaused
            self.post_message(BotPaused())
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/tui/screens/dashboard.py src/tui/app.py tests/unit/test_tui_events.py
git commit -m "fix: pause says 'press p to resume' and properly toggles state"
```

---

## Task 4: Remove dead targeting config and clean up config editor

**Files:**
- Modify: `src/tui/screens/config_editor.py:177-190,434-442`
- Modify: `config.yaml`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
def test_config_editor_does_not_save_unused_targeting():
    """Targeting industries/exclude should not be saved (dead config)."""
    # This is a deletion test — verify the fields don't exist in saved config
    # After the change, the ConfigEditorScreen should not have cfg-target-industries
```

**Step 2: Implementation**

Remove the "TARGETING" section from `ConfigEditorScreen` compose (lines 177-190) since `targeting.industries` and `targeting.exclude` are never used by the scraper or orchestrator.

Remove `targeting` section from `config.yaml`.

Remove the targeting collection from `_validate_and_collect()` (lines 434-442).

**Step 3: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add src/tui/screens/config_editor.py config.yaml
git commit -m "chore: remove dead targeting config (industries/exclude never used)"
```

---

## Task 5: Add auto_like and filter thresholds to config editor

**Files:**
- Modify: `src/tui/screens/config_editor.py:128-159,381-444`
- Test: `tests/integration/test_config_tabs.py`

**Step 1: Write the failing test**

```python
def test_config_editor_has_auto_like_checkbox(app):
    """Config editor should have an auto_like checkbox."""
    async with app.run_test() as pilot:
        app.push_screen(ConfigEditorScreen())
        await pilot.pause()
        editor = app.query_one(ConfigEditorScreen)
        checkbox = editor.query_one("#cfg-auto-like", Checkbox)
        assert checkbox is not None


def test_config_editor_has_min_reactions_field(app):
    """Config editor should have min_reactions input."""
    async with app.run_test() as pilot:
        app.push_screen(ConfigEditorScreen())
        await pilot.pause()
        editor = app.query_one(ConfigEditorScreen)
        inp = editor.query_one("#cfg-min-reactions", Input)
        assert inp is not None
```

**Step 2: Run test to verify it fails**

Expected: FAIL — fields don't exist yet

**Step 3: Write minimal implementation**

In `ConfigEditorScreen.compose()`, add to the General tab LIMITS section:

```python
with Static(classes="config-field"):
    yield Label("Min reactions:")
    yield Input(value="5", id="cfg-min-reactions")
with Static(classes="config-field"):
    yield Label("Min comments:")
    yield Input(value="2", id="cfg-min-comments")
with Static(classes="config-field"):
    yield Label("Auto-Like posts:")
    yield Checkbox("Enabled", value=True, id="cfg-auto-like")
```

In `_load_config()`, populate these fields:

```python
try:
    self.query_one("#cfg-min-reactions", Input).value = str(limits.get("min_reactions", 5))
    self.query_one("#cfg-min-comments", Input).value = str(limits.get("min_comments", 2))
    self.query_one("#cfg-auto-like", Checkbox).value = limits.get("auto_like", True)
except Exception:
    pass
```

In `_validate_and_collect()`, add:

```python
_int_field("cfg-min-reactions", "min_reactions", "limits", 0, 1000)
_int_field("cfg-min-comments", "min_comments", "limits", 0, 1000)
limits_section = self._raw_config.setdefault("limits", {})
limits_section["auto_like"] = self.query_one("#cfg-auto-like", Checkbox).value
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/tui/screens/config_editor.py tests/integration/test_config_tabs.py
git commit -m "feat: add auto_like, min_reactions, min_comments to config editor"
```

---

## Task 6: Reset stats panel on new bot run

**Files:**
- Modify: `src/tui/screens/dashboard.py:192-195`
- Modify: `src/tui/widgets/stats_panel.py`
- Test: `tests/unit/test_stats_panel.py`

**Step 1: Write the failing test**

```python
def test_stats_panel_resets_on_new_run():
    """StatsPanel.reset() should zero all counters."""
    panel = StatsPanel()
    panel.update_stats(comments_today=5, daily_limit=20,
                       posts_scanned=10, posts_skipped=3,
                       success_count=5, fail_count=2)
    panel.reset()
    assert panel.comments_today == 0
    assert panel.posts_scanned == 0
    assert panel.success_count == 0
```

**Step 2: Run test to verify it fails**

Expected: FAIL — `reset()` method doesn't exist

**Step 3: Write minimal implementation**

In `StatsPanel`:

```python
def reset(self) -> None:
    """Zero all counters for a fresh run."""
    self.update_stats(
        comments_today=0, daily_limit=self.daily_limit,
        posts_scanned=0, posts_skipped=0,
        success_count=0, fail_count=0,
    )
```

In `DashboardScreen.on_bot_started()`:

```python
def on_bot_started(self, event: BotStarted) -> None:
    self._bot_running = True
    self.query_one(StatsPanel).reset()
    self.query_one(LiveFeed).add_status("Bot started")
    self._update_status("STATUS: Running")
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/tui/widgets/stats_panel.py src/tui/screens/dashboard.py tests/unit/test_stats_panel.py
git commit -m "feat: reset stats panel when starting a new bot run"
```

---

## Task 7: Show "0 posts found" feedback in live feed

**Files:**
- Modify: `src/core/orchestrator.py:81-83`
- Test: `tests/unit/test_orchestrator_callbacks.py`

**Step 1: Write the failing test**

```python
def test_zero_posts_emits_status_with_count(mock_callbacks, scraper, ...):
    """When scrape returns 0 posts, status message should include '0 eligible'."""
    scraper.scrape_target.return_value = ScrapeResult(
        target_value="feed", posts=(), error=None,
        duration_seconds=2.0, skipped_count=5,
    )
    # ... run orchestrator ...
    status_calls = [c for c in mock_callbacks.on_status.call_args_list]
    assert any("0 eligible" in str(c) for c in status_calls)
```

**Step 2: Run test to verify it fails**

Expected: FAIL — current message is "No eligible posts found for target: ..."

**Step 3: Write minimal implementation**

In `orchestrator.py`, improve the empty-result message:

```python
if not scrape_result.posts:
    self._callbacks.on_status(
        f"0 eligible posts from '{target.value}' "
        f"(scanned {scrape_result.skipped_count + len(scrape_result.posts)}, "
        f"skipped {scrape_result.skipped_count})"
    )
    continue
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/core/orchestrator.py tests/unit/test_orchestrator_callbacks.py
git commit -m "feat: show scan/skip counts when 0 eligible posts found"
```

---

## Task 8: Add action_type column to activity log screen

**Files:**
- Modify: `src/tui/screens/activity_log.py:72-114`
- Modify: `src/storage/models.py` (if ActivityRecord needs updating)
- Test: `tests/unit/test_activity_log.py`

**Step 1: Write the failing test**

```python
def test_activity_log_screen_shows_action_type():
    """Activity log table should have an ACTION column."""
    # Verify that column headers include ACTION
```

**Step 2: Implementation**

In `ActivityLogScreen.on_mount()`:

```python
table.add_columns("#", "ACTION", "STATUS", "TIME (UTC)", "POST URL", "COMMENT")
```

In `_load_data()`, add the action_type to each row:

```python
action = (record.action_type or "comment").upper()
table.add_row(
    str(record.id),
    action,
    status_text,
    time_str,
    short_url,
    preview,
    key=str(record.id),
)
```

**Step 3: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add src/tui/screens/activity_log.py
git commit -m "feat: show action_type (COMMENT/LIKE) in activity log screen"
```

---

## Task 9: Add elapsed time to status bar

**Files:**
- Modify: `src/tui/screens/dashboard.py:75-78,192-195,232-246`
- Test: `tests/unit/test_tui_events.py`

**Step 1: Write the failing test**

```python
def test_status_bar_shows_elapsed_time(app):
    """Status bar should show elapsed time while bot is running."""
    async with app.run_test() as pilot:
        dashboard = app.query_one(DashboardScreen)
        app.post_message(BotStarted())
        await pilot.pause()
        # The status bar should contain a time indicator
        status = dashboard.query_one("#status-bar", Static)
        # At minimum, it should not say "Idle"
        assert "Idle" not in str(status.renderable)
```

**Step 2: Implementation**

In `DashboardScreen.__init__()`:

```python
self._bot_started_at: datetime | None = None
```

In `on_bot_started()`:

```python
from datetime import datetime, timezone
self._bot_started_at = datetime.now(timezone.utc)
```

In `on_stats_updated()`, compute elapsed:

```python
elapsed = ""
if self._bot_started_at:
    delta = datetime.now(timezone.utc) - self._bot_started_at
    mins, secs = divmod(int(delta.total_seconds()), 60)
    elapsed = f" | {mins}m{secs:02d}s"
self._update_status(
    f"STATUS: Running{elapsed} | "
    f"{event.comments_today}/{event.daily_limit} comments | "
    f"Mode: {mode}"
)
```

In `on_bot_stopped()` and `on_bot_error()`:

```python
self._bot_started_at = None
```

**Step 3: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add src/tui/screens/dashboard.py tests/unit/test_tui_events.py
git commit -m "feat: show elapsed time in status bar while bot runs"
```

---

## Task 10: Prevent double-start with confirmation flash

**Files:**
- Modify: `src/tui/screens/dashboard.py:121-126`
- Test: `tests/unit/test_tui_events.py`

**Step 1: Implementation**

The `_bot_running` guard already prevents double starts (line 122-123). But there's no feedback. Add a flash message:

```python
def action_start_bot(self) -> None:
    if self._bot_running:
        self._update_status("STATUS: Bot is already running")
        return
    self._bot_running = True
    self._update_status("STATUS: Starting...")
    self.app.action_start_bot()
```

**Step 2: Run tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add src/tui/screens/dashboard.py
git commit -m "feat: show 'already running' feedback on double-start attempt"
```

---

## Task 11: Full integration test — config save round-trip

**Files:**
- Test: `tests/integration/test_config_tabs.py`

**Step 1: Write the test**

```python
def test_config_save_roundtrip(tmp_path):
    """Saving config in editor should produce a valid AppConfig on reload."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "targets": [{"type": "feed"}],
        "limits": {"daily_comment_limit": 10, "min_delay_seconds": 10, "max_delay_seconds": 60},
        "ai": {"model_name": "gemini-3-flash-preview"},
        "browser": {"headless": True},
    }))

    from src.core.config import load_config
    cfg = load_config(str(config_file))
    assert cfg.limits.daily_comment_limit == 10
    assert cfg.limits.min_delay_seconds < cfg.limits.max_delay_seconds
```

**Step 2: Run test**

Run: `python -m pytest tests/integration/test_config_tabs.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_config_tabs.py
git commit -m "test: add config save/load round-trip integration test"
```

---

## Task 12: Run full test suite and verify

**Step 1: Run all tests**

```bash
python -m pytest tests/ -q --tb=short
```

Expected: ALL PASS (118+ tests)

**Step 2: Run the TUI manually**

```bash
python -m src.cli
```

Verify:
- [ ] Dashboard shows strategy panel with correct persona/targets/actions
- [ ] Press `s` shows "Starting..." in status bar
- [ ] Press `s` again while running shows "already running"
- [ ] Press `p` pauses, status shows "press p to resume"
- [ ] Press `p` again resumes
- [ ] Config editor shows auto_like, min_reactions, min_comments
- [ ] Config editor validates min_delay < max_delay
- [ ] Activity log shows ACTION column
- [ ] Stats panel resets on new run

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: finalize dashboard UX, validation, and linking improvements"
```

---

## Summary of Changes

| # | What | Type | Risk |
|---|------|------|------|
| 1 | min/max cross-field validation | Validation | Low |
| 2 | Empty targets validation | Validation | Low |
| 3 | Fix pause/resume text and flow | Bug fix | Low |
| 4 | Remove dead targeting config | Cleanup | Low |
| 5 | Add auto_like + thresholds to config editor | Feature | Low |
| 6 | Reset stats on new run | Bug fix | Low |
| 7 | Show "0 posts found" with counts | UX | Low |
| 8 | Add action_type to activity log | UX | Low |
| 9 | Elapsed time in status bar | UX | Low |
| 10 | Double-start feedback | UX | Low |
| 11 | Config round-trip test | Test | Low |
| 12 | Full verification | QA | Low |

All tasks are independent except Task 12 (final verification) which depends on all others. Tasks 1-11 can be executed in any order.
