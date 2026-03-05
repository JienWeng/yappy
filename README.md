# Yappy

AI-powered LinkedIn engagement assistant. Automatically discovers LinkedIn posts and leaves thoughtful, AI-generated comments.

## Install

### pip (recommended)

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

### From source

```bash
git clone https://github.com/jienweng/yappy.git
cd yappy
pip install -e .
yap
```

## First run

On first run, `yap` will:

1. Install the Playwright Chromium browser (if not present)
2. Create a default config at `~/.config/yappy/config.yaml`
3. Launch the onboarding wizard to set up your Gemini API key and LinkedIn login

## Usage

```bash
yap              # Launch TUI dashboard
yap --no-tui     # Run in headless CLI mode
yap --report     # Show activity report
yap --help       # Show all options
```

## Configuration

Config file: `~/.config/yappy/config.yaml`

Environment variables: `~/.config/yappy/.env`

```yaml
targets:
  - type: feed
    max_posts: 15
  - type: connections
    max_posts: 5
  - type: keyword
    value: "AI startup"
    max_posts: 5

browser:
  headless: false
  viewport_width: 1920
  viewport_height: 1080

ai:
  model_name: gemini-3-flash-preview
  temperature: 0.85
  max_output_tokens: 150

limits:
  daily_comment_limit: 20
  min_delay_seconds: 15
  max_delay_seconds: 55
```

## Data locations

| File | Path |
|------|------|
| Config | `~/.config/yappy/config.yaml` |
| API key | `~/.config/yappy/.env` |
| Activity DB | `~/Library/Application Support/yappy/activity.db` (macOS) |
| Browser profile | `~/Library/Application Support/yappy/browser_profile/` (macOS) |
| Logs | `~/Library/Application Support/yappy/logs/` (macOS) |

On Linux, data files use `~/.local/share/yappy/` instead.

## Requirements

- Python 3.11+
- A [Gemini API key](https://aistudio.google.com/apikey)

## License

MIT
