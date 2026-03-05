# Design: Comprehensive User-Friendly README for Yappy

**Date:** 2026-03-05
**Status:** Approved
**Target Audience:** Beginner-friendly (Approachable, step-by-step)

## Overview
Transform the current README into a comprehensive guide that welcomes new users, explains the automated "onboarding wizard," and details the balance between AI power and account safety.

## Section 1: Header, Elevator Pitch & Quickstart
*   **Header:** Project name (Yappy), CI/CD status, PyPI version, License (MIT).
*   **Elevator Pitch:** An approachable introduction to Yappy as an "AI-powered LinkedIn engagement assistant" that handles the tedious parts of social networking.
*   **Quickstart:** Minimal 3-line install/run block (`pip install yappy`, `yap`).

## Section 2: Getting Started (Your First Run)
*   **Onboarding Wizard:** Explain how `yap` automatically handles browser installation and configuration on the first run.
*   **AI Setup:** Step-by-step guide to obtaining a free Gemini API key.
*   **LinkedIn Connection:** Explain the secure, local-only login process that saves sessions without storing passwords.
*   **First Task:** A simple "Hello World" example (e.g., 5 comments on the home feed).

## Section 3: Managing Your Bot (Dashboard vs. Background Mode)
*   **Yappy Dashboard (TUI):**
    *   **Live Feed:** Visualizing the bot's discovery and drafting process.
    *   **Stats Panel:** Tracking daily progress and account health.
*   **Background Mode (CLI):** Using `yap --no-tui` for quiet operation.
*   **Reporting:** Accessing the activity history with `yap --report`.

## Section 4: Customizing Your AI & Safety
*   **Personalization:** Using `config.yaml` to define topics and targets.
*   **Quality Control:** The "No-Bot" Promise—explaining built-in phrase banning and redundancy checks to ensure thoughtful comments.
*   **Safety Features:**
    *   **Daily Limits:** Automatic cut-offs to stay within LinkedIn's social boundaries.
    *   **Human Mimicry:** Variable typing speeds and random delays between posts.
*   **Privacy:** Emphasize that all data (sessions, keys) stays local to the user's machine.
