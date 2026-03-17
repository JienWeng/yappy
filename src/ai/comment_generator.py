from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.ai.banned_phrases import ALL_BANNED_PHRASES
from src.ai.models import GeneratedComment, GenerateResult

if TYPE_CHECKING:
    from src.ai.gemini_client import GeminiClient
    from src.core.config import AIConfig
    from src.scraper.models import LinkedInPost

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
{persona_block}

POST:
{post_text}
{existing_comments_block}
YOUR TASK:
Write ONE comment that is specific to this post. Pick the angle that feels most earned given what they actually wrote:

- Make a precise observation about something specific (a number, a decision, a tension, an implication they didn't mention)
- OR share a brief relevant experience or data point that adds to what they said
- OR respectfully challenge one specific claim with a counter-perspective
- OR ask ONE question about a detail only someone who read carefully would notice

NEVER start with "Curious" — that opener is overused and sounds robotic. Use a different entry every time.

GOOD OPENER STYLES (pick what fits, do not copy verbatim):
- "The [specific detail] stands out because..."
- "I've seen the opposite in [context], where..."
- "That [specific number/claim] is more interesting than it looks..."
- "What strikes me is the tension between..."
- "Honestly, the [X] part is what most people miss..."
- "I'd push back slightly on the [specific claim]..."
- "The [specific decision] makes sense if [assumption], but..."
- "Most people focus on [X], but the [Y] point is actually..."

STYLE (HARD LIMITS):
- MAXIMUM 2 sentences. One sentence is often better. Never three.
- Total length: 20 to 120 characters. Short beats long.
- Contractions throughout: it's, I've, that's, didn't, we've, I'd
- Write like a message to a smart peer, not a LinkedIn reply
- Do not name {author_name} at the start
- No compliments before the point
- No corporate language, no buzzwords
{no_repeat_rule}
PUNCTUATION (hard rules):
- NEVER use an em-dash ({emdash}) or en-dash ({endash})
- Use a comma or period instead
- No trailing ellipsis (...)
- Exclamation marks only if the content genuinely warrants it

BANNED PHRASES:
{banned_phrases}

Output ONLY the comment text. Nothing else.
"""

_EXISTING_COMMENTS_BLOCK = """\
EXISTING COMMENTS (match the register, do NOT repeat these ideas or openers):
{comments}

"""

_NO_REPEAT_RULE = "- Do NOT repeat any idea, phrasing, or question already in the existing comments\n"


class CommentGenerator:
    def __init__(self, client: GeminiClient, config: AIConfig) -> None:
        self._client = client
        self._config = config

    def generate(self, post: LinkedInPost) -> GenerateResult:
        try:
            prompt = self._build_prompt(post)
            raw_text = self._client.generate(prompt)
            validated_text = self._validate(raw_text)
            comment = GeneratedComment(
                text=validated_text,
                post_url=post.post_url,
                generated_at=datetime.now(UTC),
                model_used=self._config.model_name,
            )
            return GenerateResult(comment=comment, error=None)
        except Exception as exc:
            logger.error("Comment generation failed for %s: %s", post.post_url, exc)
            return GenerateResult(comment=None, error=str(exc))

    def _build_prompt(self, post: LinkedInPost) -> str:
        banned_list = "\n".join(f"- {phrase}" for phrase in ALL_BANNED_PHRASES)
        author = post.author_name or "the author"

        if post.existing_comments:
            numbered = "\n".join(
                f'{i+1}. "{c}"' for i, c in enumerate(post.existing_comments)
            )
            existing_block = _EXISTING_COMMENTS_BLOCK.format(comments=numbered)
            no_repeat_rule = _NO_REPEAT_RULE
        else:
            existing_block = ""
            no_repeat_rule = ""

        # Construct persona block
        if self._config.personality_prefix:
            persona_block = self._config.personality_prefix
        else:
            persona_block = f"You are leaving a LinkedIn comment as a sharp, thoughtful professional. Your comment will be read by {author} and their audience."

        return _PROMPT_TEMPLATE.format(
            persona_block=persona_block,
            author_name=author,
            post_text=post.post_text,
            existing_comments_block=existing_block,
            no_repeat_rule=no_repeat_rule,
            banned_phrases=banned_list,
            emdash="\u2014",
            endash="\u2013",
        )

    def _validate(self, text: str) -> str:
        """Sanitize punctuation then raise ValueError if any banned phrase remains."""
        # Replace em-dash and en-dash (with any surrounding whitespace) with a comma
        text = re.sub(r"\s*[\u2014\u2013]\s*", ", ", text)
        # Collapse multiple spaces and clean up any ", ," artifacts
        text = re.sub(r",\s*,", ",", text)
        text = re.sub(r"  +", " ", text).strip()

        text_lower = text.lower()

        # Ban "Curious" as an opener — overused, sounds robotic
        if text_lower.startswith("curious"):
            raise ValueError(
                "Comment starts with 'Curious' — banned opener. Regeneration required."
            )
        for phrase in ALL_BANNED_PHRASES:
            # Skip the raw punctuation chars — they're handled by sanitization above
            if phrase in ("\u2014", "\u2013", " - - "):
                continue
            if phrase.lower() in text_lower:
                raise ValueError(
                    f"Generated comment contains banned phrase: {phrase!r}. "
                    "Regeneration required."
                )
        if len(text) < 20:
            raise ValueError(f"Generated comment too short ({len(text)} chars).")
        if len(text) > 220:
            raise ValueError(
                f"Generated comment too long ({len(text)} chars, max 220). "
                "Regeneration required."
            )
        return text
