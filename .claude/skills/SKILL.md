# LinkedIn Auto-Commenter — Project Standards

## Comment Quality

### Tone
- Conversational and direct — write like a knowledgeable peer, not a marketing department
- 2–4 sentences per comment
- Use contractions naturally (it's, I'm, that's, we've, etc.)
- Reference specific details from the post — generic comments are not acceptable
- Add value: a question, a relevant experience, a constructive perspective

### Prohibited Content
- Never start a comment with a compliment about the post ("Great post!", "So insightful!")
- Never include any phrase from src/ai/banned_phrases.py
- Never reveal AI, automated, or generated origins
- No corporate buzzwords: leverage, synergy, paradigm shift, game-changer, etc.

## Operational Limits

### Daily Cap
- Hard limit: 20 comments per UTC day
- Enforced by RateLimiter.assert_can_post() before every comment attempt
- DailyLimitExceededError is raised — do not bypass or catch and ignore

### Timing
- Minimum delay between comments: 15 seconds
- Maximum delay between comments: 45 seconds
- Typing speed: 55–80 WPM with +/-30% per-character jitter

## Architecture Constraints

### Stealth Requirements
- Browser must run headful (headless=False) — LinkedIn detects headless via GPU/font fingerprinting
- stealth_async(context) must be called AFTER launch_persistent_context() returns
- Use STEALTH_BROWSER_ARGS from browser_factory.py — do not modify without testing

### Data Immutability
- All models use frozen=True (@dataclass(frozen=True) or Pydantic frozen=True)
- Never mutate model instances — create new ones instead

### Duplicate Prevention
- ActivityLog.was_commented(post_url) is checked before adding any post to the scrape results
- Do not comment on the same post URL twice across sessions

### Persistent Session
- Browser profile stored at data/browser_profile/ (gitignored)
- First run: log into LinkedIn manually in the opened browser
- Subsequent runs: session is restored automatically — no re-login needed

## File Organization
- Max 800 lines per file, target 200–400 lines
- One concern per module — no mega-files
- All error handling must be explicit — never swallow exceptions silently
