# Yappy 🐶

AI-powered LinkedIn engagement assistant. Automatically discover LinkedIn posts and leave thoughtful, unique, AI-generated comments that actually sound like you.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Yappy is a powerful terminal-based tool that uses **Google's Gemini AI** and **Playwright** browser automation to help you stay active on LinkedIn without the mindless scrolling.

---

## 🚀 Quickstart

Install Yappy using your favorite package manager:

### pip (Recommended)
```bash
pip install yappy
yap
```

### Homebrew (macOS)
```bash
brew tap jienweng/tap
brew install yappy
yap
```

---

## ✨ Getting Started (Your First Run)

The first time you run `yap`, Yappy will launch a friendly **onboarding wizard** to help you get set up in minutes.

1.  **Automatic Setup:** Yappy will automatically install the necessary Playwright browser and create your configuration files.
2.  **Your AI "Brain":** You'll need a Google Gemini API key. They are currently free to get from [Google AI Studio](https://aistudio.google.com/apikey).
3.  **Secure Login:** Yappy will open a browser window for you to log in to LinkedIn. **Your password is never seen or stored by Yappy.** It securely saves your session "cookie" locally on your computer, so you stay logged in for future runs.
4.  **Ready to Go:** Once connected, Yappy is ready to start finding posts for you!

---

## 📺 Managing Your Bot

Yappy offers two ways to run, depending on whether you want to watch the magic happen or let it run quietly in the background.

### 1. The Yappy Dashboard (TUI)
Just run `yap` to open the interactive dashboard.
*   **Live Feed:** Watch in real-time as Yappy discovers posts and drafts thoughtful comments.
*   **Stats Panel:** Keep an eye on your daily progress and account health.
*   **Configuration Editor:** Tweak your settings directly from within the terminal.

### 2. Background Mode (CLI)
If you prefer to let Yappy work while you focus on other things:
```bash
yap --no-tui
```
You can check on its progress anytime by running a report:
```bash
yap --report
```

---

## 🛡️ Built for Quality & Safety

Yappy isn't just another "bot"—it's designed to be a thoughtful assistant that protects your professional reputation.

*   **The "No-Bot" Promise:** Yappy has a built-in list of "banned phrases" (like *"Great post!"* or *"Thanks for sharing!"*). It strictly avoids generic AI-isms, ensuring your comments are unique and add value to the conversation.
*   **Context Aware:** Yappy reads the post *and* existing comments to make sure it doesn't repeat what's already been said.
*   **Human-Like Behavior:** To stay within LinkedIn's safety boundaries, Yappy:
    *   **"Types"** comments character-by-character with natural delays.
    *   **Takes breaks** between posts.
    *   **Strictly follows** daily comment limits that you control.
*   **Privacy First:** Your API keys, LinkedIn session, and activity logs stay **100% on your local machine**. Nothing is ever sent to our servers.

---

## ⚙️ Customization

Configuration is stored at `~/.config/yappy/config.yaml`. You can customize your targets:

```yaml
targets:
  - type: feed          # Your home feed
    max_posts: 15
  - type: keyword       # Specific topics
    value: "AI startups"
    max_posts: 5
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Yappy is an independent project and is not affiliated with, authorized, maintained, sponsored, or endorsed by LinkedIn Corporation.*
