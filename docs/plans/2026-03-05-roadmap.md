# Yappy Roadmap 🚀

This document outlines the future vision and planned evolution for Yappy.

---

## Phase 1: Background Automation & Core Actions
*   **OS-Native Scheduling:** Support for `cron` (Linux/macOS) and `launchd` (macOS) via a new `yap schedule` command.
*   **Headless Automation:** The `--automated` flag for graceful, non-interactive background execution.
*   **Expanded Actions:** Implementation of **Auto-Liking** (Reactions) to complement AI-generated comments.

## Phase 2: Granular Targeting & Intelligence
*   **Targeting Engine:** Filter posts by **Industry**, **Job Title**, or specific **Follow-lists**.
*   **Smart Filtering:** Improved logic to skip posts that are irrelevant to the user's professional niche.
*   **Multi-Account Support:** Namespaced browser profiles and configuration for managing multiple LinkedIn accounts.

## Phase 3: Personality & Voice Matching
*   **Personality Presets:** A library of AI personas (e.g., "Insightful Expert," "Supportive Peer," "Friendly Challenger").
*   **Custom Voice Tuning:** Allow users to provide sample text to refine the Gemini prompt for a perfect stylistic match.
*   **Platform Expansion:** Modular support for other professional networks (Twitter/X, Reddit, etc.) using the same core personality engine.

## Phase 4: Scaling & Connectivity
*   **Daemon Mode:** A persistent `yappyd` background service.
*   **Remote Control:** Allow the TUI/CLI to connect to a Yappy instance running on a remote VPS or home server.
