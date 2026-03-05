"""Comment review widget for manual approval mode."""
from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Static, TextArea


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    SKIP = "skip"
    EDIT = "edit"
    REGENERATE = "regenerate"


class CommentReview(Widget):
    """Widget for reviewing and approving/rejecting generated comments."""

    DEFAULT_CSS = """
    CommentReview {
        width: 100%;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        display: none;
    }
    CommentReview.visible {
        display: block;
    }
    CommentReview .review-title {
        text-style: bold;
        margin-bottom: 1;
    }
    CommentReview .review-post-preview {
        margin-bottom: 1;
        color: $text-muted;
    }
    CommentReview TextArea {
        height: 4;
        margin-bottom: 1;
    }
    CommentReview .review-buttons {
        layout: horizontal;
        height: 3;
    }
    CommentReview Button {
        margin-right: 1;
    }
    """

    class Decided(Message):
        """User made a review decision."""

        def __init__(self, decision: ReviewDecision, comment_text: str) -> None:
            super().__init__()
            self.decision = decision
            self.comment_text = comment_text

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._current_comment = ""

    @property
    def current_comment(self) -> str:
        return self._current_comment

    @property
    def is_visible(self) -> bool:
        return self.has_class("visible")

    def compose(self) -> ComposeResult:
        yield Static("REVIEW COMMENT", classes="review-title")
        yield Label("", id="review-post-info", classes="review-post-preview")
        yield Static("Generated comment:")
        yield TextArea("", id="review-comment-area", read_only=True)
        with Static(classes="review-buttons"):
            yield Button("Approve [a]", id="btn-approve", variant="success")
            yield Button("Skip [x]", id="btn-skip", variant="default")
            yield Button("Edit [e]", id="btn-edit", variant="warning")
            yield Button("Regenerate [r]", id="btn-regenerate", variant="primary")

    def show_review(
        self, *, author: str, post_preview: str, comment_text: str
    ) -> None:
        self._current_comment = comment_text
        self.add_class("visible")
        try:
            self.query_one("#review-post-info", Label).update(
                f'Post by {author}: "{post_preview[:80]}"'
            )
            self.query_one("#review-comment-area", TextArea).load_text(
                comment_text
            )
        except Exception:
            pass

    def hide_review(self) -> None:
        self._current_comment = ""
        self.remove_class("visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        decision_map = {
            "btn-approve": ReviewDecision.APPROVE,
            "btn-skip": ReviewDecision.SKIP,
            "btn-edit": ReviewDecision.EDIT,
            "btn-regenerate": ReviewDecision.REGENERATE,
        }
        button_id = event.button.id or ""
        decision = decision_map.get(button_id)
        if decision is None:
            return

        if decision == ReviewDecision.EDIT:
            try:
                area = self.query_one("#review-comment-area", TextArea)
                area.read_only = False
                area.focus()
            except Exception:
                pass
            return

        comment_text = self._current_comment
        try:
            area = self.query_one("#review-comment-area", TextArea)
            comment_text = area.text
        except Exception:
            pass

        self.post_message(
            self.Decided(decision=decision, comment_text=comment_text)
        )
        self.hide_review()
