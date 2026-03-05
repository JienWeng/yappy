# Design: Developer Documentation Suite for Yappy

**Date:** 2026-03-05
**Status:** Approved
**Target Audience:** Open Source Contributors & Developers

## Overview
Create a comprehensive suite of developer documentation to facilitate open-source contributions. This includes a `CONTRIBUTING.md` for onboarding and an `ARCHITECTURE.md` for understanding the system's internal design.

## Section 1: CONTRIBUTING.md (Onboarding Developers)
*   **Approach:** Standard Python (`pip`, `venv`, `pytest`).
*   **Local Setup:**
    *   Git clone and virtual environment creation.
    *   Dependency installation (`pip install -r requirements.txt`).
    *   Playwright browser setup (`playwright install chromium`).
*   **Development Workflow:**
    *   Running the test suite with `pytest`.
    *   Code style and linting expectations.
*   **Contribution Process:**
    *   Branching strategy (`feat/`, `fix/`, `docs/`).
    *   PR requirements (automated tests, descriptive summaries).

## Section 2: ARCHITECTURE.md (Internal Design)
*   **Core Engine (The "Brain"):**
    *   **Orchestrator:** Central coordination of the pipeline.
    *   **Callback System:** Decoupling the business logic from the TUI and CLI.
*   **The Pipeline (The "Body"):**
    *   **Scraper:** Playwright-based extraction of LinkedIn posts.
    *   **AI Generator:** Context-aware, "No-Bot" comment generation using Gemini.
    *   **Executor:** Human-mimicking posting logic (`HumanTyper`).
*   **Data & State (Persistence):**
    *   **SQLite Storage:** Activity logging and local history.
    *   **Browser Profiles:** Local session persistence for secure logins.
*   **User Interface (The "Head"):**
    *   **Textual TUI:** Overview of screens (Dashboard, Onboarding) and custom widgets.
