"""Tests for the CommentReview widget."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.tui.widgets.comment_review import CommentReview, ReviewDecision


class ReviewApp(App):
    def compose(self) -> ComposeResult:
        yield CommentReview()


class TestCommentReview:
    @pytest.mark.asyncio
    async def test_show_review_sets_content(self):
        async with ReviewApp().run_test() as pilot:
            widget = pilot.app.query_one(CommentReview)
            widget.show_review(
                author="@JaneDoe",
                post_preview="Excited to announce...",
                comment_text="Congrats!",
            )
            assert widget.current_comment == "Congrats!"
            assert widget.is_visible is True

    @pytest.mark.asyncio
    async def test_hide_review(self):
        async with ReviewApp().run_test() as pilot:
            widget = pilot.app.query_one(CommentReview)
            widget.show_review(
                author="@JaneDoe",
                post_preview="Post",
                comment_text="Comment",
            )
            widget.hide_review()
            assert widget.current_comment == ""


class TestReviewDecision:
    def test_approve_value(self):
        assert ReviewDecision.APPROVE == "approve"

    def test_skip_value(self):
        assert ReviewDecision.SKIP == "skip"

    def test_edit_value(self):
        assert ReviewDecision.EDIT == "edit"

    def test_regenerate_value(self):
        assert ReviewDecision.REGENERATE == "regenerate"
