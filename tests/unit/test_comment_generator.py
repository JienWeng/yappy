from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.ai.comment_generator import CommentGenerator
from src.ai.models import GeneratedComment
from src.scraper.models import LinkedInPost


def make_post(text: str = "We just closed our Series A round.") -> LinkedInPost:
    return LinkedInPost(
        post_url="https://linkedin.com/feed/update/urn:li:activity:123",
        author_name="Jane Doe",
        author_profile_url="https://linkedin.com/in/janedoe",
        post_text=text,
        scraped_at=datetime.now(timezone.utc),
        source_target="AI startup fundraising",
    )


def make_generator(response: str) -> CommentGenerator:
    client = MagicMock()
    client.generate.return_value = response
    config = MagicMock()
    config.model_name = "gemini-3-flash-preview"
    return CommentGenerator(client=client, config=config)


class TestCommentGenerator:
    def test_successful_generation(self) -> None:
        gen = make_generator("Congrats on the Series A — what sectors are you targeting with the capital?")
        result = gen.generate(make_post())
        assert result.error is None
        assert result.comment is not None
        assert isinstance(result.comment, GeneratedComment)
        assert "Series A" in result.comment.text or len(result.comment.text) > 20

    def test_returns_error_on_banned_phrase(self) -> None:
        gen = make_generator("Great post! This is a game-changer for sure.")
        result = gen.generate(make_post())
        assert result.comment is None
        assert result.error is not None
        assert "banned phrase" in result.error.lower()

    def test_returns_error_on_ai_indicator(self) -> None:
        gen = make_generator("As an AI, I think this fundraising is impressive.")
        result = gen.generate(make_post())
        assert result.comment is None
        assert result.error is not None

    def test_returns_error_on_too_short_response(self) -> None:
        gen = make_generator("ok")
        result = gen.generate(make_post())
        assert result.comment is None
        assert result.error is not None

    def test_gemini_exception_propagates_as_error(self) -> None:
        client = MagicMock()
        client.generate.side_effect = RuntimeError("API timeout")
        config = MagicMock()
        config.model_name = "gemini-3-flash-preview"
        gen = CommentGenerator(client=client, config=config)
        result = gen.generate(make_post())
        assert result.comment is None
        assert "API timeout" in (result.error or "")

    def test_comment_metadata(self) -> None:
        gen = make_generator("Congrats on the milestone — what's the growth plan for the next 18 months?")
        post = make_post()
        result = gen.generate(post)
        assert result.comment is not None
        assert result.comment.post_url == post.post_url
        assert result.comment.model_used == "gemini-3-flash-preview"
        assert isinstance(result.comment.generated_at, datetime)
