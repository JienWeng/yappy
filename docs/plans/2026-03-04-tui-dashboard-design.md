# LinkedIn Auto-Commenter TUI Dashboard Design

Date: 2026-03-04

## Goal

Replace the CLI (`python main.py`) with a full Textual-based TUI that provides onboarding, a live dashboard, config editing, and activity log viewing. Support both automatic and manual comment approval modes.

## Architecture: Textual with Worker Threads

Single Textual app. The bot pipeline runs in a Textual `Worker` (background thread). The worker pushes events to the UI via Textual's message system. The UI remains responsive at all times.

Existing modules (`src/core`, `src/scraper`, `src/ai`, `src/executor`, `src/storage`) stay untouched. A new `src/tui` layer wraps them.

### File Structure

```
src/tui/
  app.py               # Main Textual App, screen routing
  screens/
    onboarding.py      # Multi-step wizard (5 steps)
    dashboard.py       # Main dashboard with live feed
    config_editor.py   # Edit targets, limits, AI params
    activity_log.py    # Historical activity viewer
  widgets/
    live_feed.py       # Real-time post processing log
    stats_panel.py     # Today's stats, rate limit bar
    comment_review.py  # Manual approval widget
    header_bar.py      # App header with status indicators
  workers/
    bot_worker.py      # Background worker running bot pipeline
  events.py            # Custom Textual messages
  styles.py            # TCSS stylesheets
```

### Orchestrator Modification

The orchestrator gets a thin callback interface (`on_post_found()`, `on_comment_generated()`, etc.). The worker translates callbacks into Textual messages. The orchestrator does not depend on Textual.

## Onboarding Wizard (5 Steps)

1. **Welcome** -- App title, description, "Get Started" button
2. **API Key Setup** -- Input field, validates via test API call, writes to `.env`
3. **LinkedIn Login** -- Launches headful browser, instructions to log in, "I'm logged in" button, verifies feed elements
4. **Target Configuration** -- Source selection (feed, connections, keyword), max_posts per target, engagement thresholds
5. **Dry Run Preview** -- Runs scraper in worker, shows table of posts it would comment on, generates sample comments without posting, save or go back

A flag in config marks onboarding as complete. Skipped on subsequent launches.

## Main Dashboard Layout

```
+-------------------------------------------------------------+
|  LinkedIn Auto-Commenter       [Auto] [Manual]  [Config]    |
+----------------------------+--------------------------------+
|  TODAY'S STATS             |  LIVE FEED                     |
|  ----------------          |  ----------------              |
|  Comments: 7/20            |  12:30 OK  Posted on @JaneDoe |
|  Success Rate: 85%         |       "Great point about..."   |
|  Posts Scanned: 42         |  12:28 SKIP Skipped (job post) |
|  Posts Skipped: 35         |  12:25 OK  Posted on @JohnSmith|
|                            |       "Interesting take on..." |
|  ----------------          |  12:22 ...  Generating...      |
|  Rate Limit: [####--] 35% |                                |
|                            |                                |
|  [> Start] [|| Pause]     |                                |
|  [Activity Log]            |                                |
+----------------------------+--------------------------------+
|  STATUS: Running | Next: 32s | Mode: Auto                  |
|  s:Start  p:Pause  m:Mode  c:Config  l:Log  q:Quit         |
+-------------------------------------------------------------+
```

### Mode Toggle

- **Auto mode**: Bot runs autonomously. Live feed shows real-time processing.
- **Manual mode**: On comment generation, worker pauses and shows review widget.

### Manual Review Widget

```
+-- REVIEW COMMENT -----------------------------------+
| Post by @JaneDoe: "Excited to announce our..."      |
|                                                      |
| Generated comment:                                   |
| +--------------------------------------------------+|
| | Congrats on the launch! The focus on             ||
| | developer experience really stands out.          ||
| +--------------------------------------------------+|
|                                                      |
|  [Approve]  [Skip]  [Edit]  [Regenerate]            |
+-----------------------------------------------------+
```

## Keybindings

### Dashboard

| Key | Action |
|-----|--------|
| s | Start bot |
| p | Pause bot |
| q | Quit app |
| m | Toggle Auto/Manual mode |
| c | Open config editor |
| l | Open activity log |
| Tab | Switch focus between panels |

### Manual Review

| Key | Action |
|-----|--------|
| Enter / a | Approve comment |
| x | Skip |
| e | Edit comment |
| r | Regenerate comment |

### Config Editor

| Key | Action |
|-----|--------|
| Escape | Back to dashboard |
| Enter | Edit selected field |
| Ctrl+S | Save config |

### Activity Log

| Key | Action |
|-----|--------|
| Escape | Back to dashboard |
| Up/Down | Scroll |
| Enter | View details |
| f | Filter |

## Events (Worker <-> UI Communication)

### Worker -> UI

- `BotStarted` -- Pipeline began
- `PostFound` -- Post discovered (url, author, preview)
- `PostSkipped` -- Post filtered (url, reason)
- `CommentGenerated` -- Comment ready (url, author, text)
- `CommentAwaitingApproval` -- Manual mode: waiting for user
- `CommentPosted` -- Successfully posted (url, text)
- `CommentFailed` -- Failed (url, error)
- `StatsUpdated` -- Updated counts
- `BotPaused` -- Paused by user
- `BotStopped` -- Finished or stopped
- `BotError` -- Unrecoverable error

### UI -> Worker

- `ApproveComment` -- User approved
- `SkipComment` -- User skipped
- `EditComment` -- User edited (new_text)
- `RegenerateComment` -- Regenerate
- `PauseBot` -- Pause pipeline
- `ResumeBot` -- Resume pipeline

## Config Editor Screen

Form-based editor for `config.yaml` organized by section (Targets, Limits, AI Settings). Validates inputs inline before saving. Writes to `config.yaml` on Ctrl+S.

## Activity Log Screen

DataTable pulling from SQLite `activity_log`. Shows status, timestamp, author, comment preview. Enter to expand full details. Filter by date or status.

## Error Handling

- API key invalid: Inline error in onboarding, re-enter
- LinkedIn not logged in: Modal with instructions
- Browser crash: `BotError` event, auto-pause, error in live feed
- Rate limit reached: `BotStopped`, stats highlighted, start disabled
- Network errors: Logged as FAIL in feed, bot continues
- Config validation: Inline errors, save blocked

## Dependencies

```
textual>=3.0
```

Single new dependency. Textual includes Rich.

## Testing

- Unit tests: Widget isolation (stats panel, review widget)
- Integration tests: Worker <-> UI message flow
- Snapshot tests: Textual pilot-based screen rendering
- Existing tests: Unchanged (core modules untouched)

## Design Constraints

- No emoji in UI -- use text labels (OK, FAIL, SKIP, etc.)
- All keybindings shown in footer bar
- Immutable data models throughout (frozen dataclasses)
- Max 800 lines per file
