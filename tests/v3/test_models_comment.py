"""Tests for Comment / CommentAuthor / CommentsPage models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from instaharvest._v3.core.models import (
    Comment,
    CommentAuthor,
    CommentsPage,
)


def _author(username: str = "bob") -> CommentAuthor:
    return CommentAuthor(username=username)


def _comment(**overrides) -> Comment:
    base = dict(
        id="42",
        text="hello",
        author=_author(),
        created_at=1_700_000_000,
    )
    base.update(overrides)
    return Comment(**base)


class TestCommentCore:
    def test_minimal(self):
        c = _comment()
        assert c.like_count == 0
        assert c.reply_count == 0
        assert c.replies == ()
        assert c.parent_id is None
        assert c.created_at.tzinfo is timezone.utc

    def test_negative_counts_rejected(self):
        with pytest.raises(ValidationError):
            _comment(like_count=-1)
        with pytest.raises(ValidationError):
            _comment(reply_count=-1)

    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError):
            _comment(id="")

    def test_is_frozen(self):
        c = _comment()
        with pytest.raises(ValidationError):
            c.like_count = 9999  # type: ignore[misc]

    def test_text_can_be_empty_string(self):
        # Instagram allows blank-text "comments" for some sticker reactions.
        # Empty text is meaningful, just rare; accept it.
        c = _comment(text="")
        assert c.text == ""


class TestCommentReplies:
    def test_nested_replies(self):
        replies = (
            _comment(id="42a", parent_id="42", text="reply 1"),
            _comment(id="42b", parent_id="42", text="reply 2"),
        )
        c = _comment(reply_count=2, replies=replies)
        assert len(c.replies) == 2
        assert c.replies[0].parent_id == "42"

    def test_replies_are_immutable(self):
        c = _comment(replies=(_comment(id="x"),))
        with pytest.raises(TypeError):
            c.replies[0] = _comment(id="y")  # type: ignore[index]

    def test_model_copy_replaces_replies(self):
        # Used by CommentScraper after fetching child comments.
        parent = _comment(id="42", reply_count=1)
        new = parent.model_copy(update={"replies": (_comment(id="42a", parent_id="42"),)})
        assert new is not parent
        assert len(new.replies) == 1
        assert parent.replies == ()  # original untouched


class TestCommentsPage:
    def test_total_must_match_len(self):
        comments = (_comment(id="1"), _comment(id="2"))
        page = CommentsPage(
            media_shortcode="ABC",
            comments=comments,
            total_returned=2,
        )
        assert page.total_returned == 2

    def test_total_disagree_with_len_rejected(self):
        with pytest.raises(ValidationError):
            CommentsPage(
                media_shortcode="ABC",
                comments=(_comment(id="1"),),
                total_returned=5,
            )

    def test_empty_page_ok(self):
        page = CommentsPage(media_shortcode="ABC", comments=(), total_returned=0)
        assert page.has_more is False
        assert page.next_cursor is None

    def test_empty_shortcode_rejected(self):
        with pytest.raises(ValidationError):
            CommentsPage(media_shortcode="", total_returned=0)
