# Yappy Architecture 🏗️

Yappy is a modular LinkedIn engagement bot designed to balance powerful automation with high-quality, human-like interaction. This document explains the internal design and data flow.

---

## 🧩 High-Level Design

Yappy is built around a decoupled architecture consisting of three main parts:

1.  **The Brain (Orchestrator):** Coordinates the high-level workflow.
2.  **The Body (Pipeline):** Handles scraping, AI generation, and posting.
3.  **The Head (Interfaces):** Provides the TUI dashboard and CLI.

---

## 🧠 Core Engine: The Orchestrator

The `Orchestrator` (`src/core/orchestrator.py`) is the central hub. It doesn't know about TUI or CLI specifically—it just manages the execution loop:
1.  **Targets:** Fetches goals from configuration (feed, keyword, connections).
2.  **Loop:** Iterates through targets, calling the Scraper.
3.  **Decision:** Decides whether a post is worth commenting on.
4.  **Action:** Triggers the Comment Generator and then the Executor.

### 🔌 Callback System
To keep the engine decoupled, the Orchestrator uses a **callback architecture** (`src/core/callbacks.py`).
-   The **TUI App** implements these callbacks to update the live feed and stats.
-   The **Headless CLI** implements these callbacks to log status to the terminal.

---

## 🛠️ The Pipeline Components

### 🕵️ Scraper (`src/scraper/`)
Uses **Playwright** and **Chromium** to navigate LinkedIn. It handles:
-   Scroll-to-load behavior.
-   Post data extraction (text, author, existing comments).
-   Privacy by using local browser profiles and persisting sessions.

### 🤖 AI Comment Generator (`src/ai/`)
The `CommentGenerator` uses Google's **Gemini API** with heavy prompt engineering.
-   **Context Awareness:** It feeds the post content AND existing comments into the prompt to ensure the AI doesn't duplicate what others have said.
-   **No-Bot Filtering:** A built-in list of "banned phrases" prevents the AI from using generic buzzwords or sounding like a bot.
-   **Validation:** Comments are strictly validated for quality before they are passed to the next stage.

### ✍️ Executor (`src/executor/`)
The final step in the chain. The `HumanTyper` mimics human behavior:
-   **Natural Typing:** Instead of "pasting" text, it types character-by-character.
-   **Variable Speed:** It uses a Words-Per-Minute (WPM) model with random jitter.
-   **Natural Pauses:** It adds slightly longer pauses between words and sentences.

---

## 💾 Data & Persistence

### 🗄️ SQLite Storage (`src/storage/`)
Yappy uses a local SQLite database to log every activity. This enables:
-   Daily limit enforcement (preventing account flags).
-   Activity reporting (`yap --report`).
-   History tracking to avoid duplicate comments on the same post.

### 🍪 Browser Profiles (`data/browser_profile/`)
Instead of logging in every time, Yappy persists your browser profile locally. This keeps you logged in securely and avoids triggering LinkedIn's suspicious login alerts.

---

## 🖥️ Textual TUI (`src/tui/`)

The Dashboard is built using the **Textual** framework. It is composed of:
-   **Screens:** `Dashboard`, `Onboarding`, and `ConfigEditor`.
-   **Widgets:** Custom UI elements like `LiveFeed` (scrolling events) and `StatsPanel` (real-time graphs).
-   **Workers:** Background threads (`src/tui/workers/bot_worker.py`) that run the Orchestrator without freezing the UI.

---

## 🛡️ Safety Systems

-   **Rate Limiter:** `src/core/rate_limiter.py` enforces global and per-session cooldowns.
-   **Banned Phrases:** `src/ai/banned_phrases.py` maintains the list of AI-isms to avoid.
-   **Stealth:** Uses `playwright-stealth` to minimize browser automation fingerprints.
