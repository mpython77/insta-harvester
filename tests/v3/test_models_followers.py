"""Tests for FollowEntry / FollowList / FriendshipStatus models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from instaharvest._v3.core.models import (
    FollowEntry,
    FollowList,
    FriendshipStatus,
)


def _entry(username: str = "alice") -> FollowEntry:
    return FollowEntry(username=username)


class TestFollowEntry:
    def test_minimal(self):
        e = _entry()
        assert e.is_verified is False
        assert e.is_private is False

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            FollowEntry(username="")

    def test_is_frozen(self):
        e = _entry()
        with pytest.raises(ValidationError):
            e.is_verified = True  # type: ignore[misc]


class TestFollowList:
    def test_followers_list(self):
        users = (_entry("alice"), _entry("bob"))
        fl = FollowList(
            target_user_id="123",
            kind="followers",
            users=users,
            total_returned=2,
        )
        assert fl.kind == "followers"
        assert fl.has_more is False
        assert len(fl.users) == 2

    def test_following_list(self):
        fl = FollowList(
            target_user_id="123", kind="following", total_returned=0,
        )
        assert fl.kind == "following"

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            FollowList(
                target_user_id="123", kind="friends", total_returned=0,
            )

    def test_total_must_match_len(self):
        # Mirrors the CommentsPage invariant — defends against
        # silently-clipped lists where total_returned drifts from
        # actual content.
        with pytest.raises(ValidationError):
            FollowList(
                target_user_id="123",
                kind="followers",
                users=(_entry("alice"),),
                total_returned=5,
            )

    def test_empty_target_user_id_rejected(self):
        with pytest.raises(ValidationError):
            FollowList(target_user_id="", kind="followers", total_returned=0)


class TestFriendshipStatus:
    def test_default_all_false(self):
        s = FriendshipStatus(user_id="1")
        assert s.is_following is False
        assert s.is_followed_by is False
        assert s.is_blocking is False
        assert s.is_muting is False
        assert s.has_outgoing_request is False
        assert s.has_incoming_request is False

    def test_full_construction(self):
        s = FriendshipStatus(
            user_id="42",
            is_following=True,
            is_followed_by=True,
            is_muting=False,
        )
        assert s.is_following is True
        assert s.is_followed_by is True

    def test_is_frozen(self):
        s = FriendshipStatus(user_id="1")
        with pytest.raises(ValidationError):
            s.is_following = True  # type: ignore[misc]

    def test_empty_user_id_rejected(self):
        with pytest.raises(ValidationError):
            FriendshipStatus(user_id="")
