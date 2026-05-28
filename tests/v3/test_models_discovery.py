"""Tests for Hashtag / Location / MediaFeed / SearchResult models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from instaharvest._v3.core.models import (
    FeedSource,
    Hashtag,
    Location,
    Media,
    MediaFeed,
    MediaKind,
    MediaOwner,
    SearchHashtagHit,
    SearchPlaceHit,
    SearchResult,
    SearchUserHit,
)


def _media(shortcode: str = "ABC123") -> Media:
    return Media(
        shortcode=shortcode,
        url=f"https://www.instagram.com/p/{shortcode}/",
        kind=MediaKind.IMAGE,
        owner=MediaOwner(username="alice"),
        taken_at=1_700_000_000,
        like_count=10,
        comment_count=2,
    )


# ---------------------------------------------------------------------------
# Hashtag
# ---------------------------------------------------------------------------


class TestHashtag:
    def test_minimal(self):
        h = Hashtag(name="fashionweek")
        assert h.media_count == 0
        assert h.allow_following is True
        assert h.is_following is False

    def test_negative_media_count_rejected(self):
        with pytest.raises(ValidationError):
            Hashtag(name="x", media_count=-1)

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Hashtag(name="")

    def test_is_frozen(self):
        h = Hashtag(name="x")
        with pytest.raises(ValidationError):
            h.is_following = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


class TestLocation:
    def test_minimal(self):
        loc = Location(pk="42", name="Tashkent")
        assert loc.lat is None and loc.lng is None
        assert loc.media_count == 0

    def test_empty_pk_rejected(self):
        with pytest.raises(ValidationError):
            Location(pk="", name="Tashkent")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Location(pk="1", name="")


# ---------------------------------------------------------------------------
# MediaFeed
# ---------------------------------------------------------------------------


class TestMediaFeed:
    def test_minimal(self):
        f = MediaFeed(
            source=FeedSource.HASHTAG_RECENT,
            source_id="fashionweek",
            total_returned=0,
        )
        assert f.has_more is False
        assert f.next_cursor is None
        assert f.media == ()

    def test_total_must_match_len(self):
        # Mirrors the CommentsPage / FollowList invariant.
        with pytest.raises(ValidationError):
            MediaFeed(
                source=FeedSource.HASHTAG_RECENT,
                source_id="fashionweek",
                media=(_media("A"), _media("B")),
                total_returned=5,
            )

    def test_empty_source_id_rejected(self):
        with pytest.raises(ValidationError):
            MediaFeed(
                source=FeedSource.EXPLORE, source_id="", total_returned=0,
            )

    def test_feed_source_enum_values(self):
        # Document the wire-format names — callers can serialise
        # a MediaFeed to JSON without surprises.
        names = {s.value for s in FeedSource}
        assert names == {
            "hashtag_top",
            "hashtag_recent",
            "location_recent",
            "location_ranked",
            "explore",
        }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearchResult:
    def test_minimal(self):
        r = SearchResult(query="fashion")
        assert r.users == ()
        assert r.hashtags == ()
        assert r.places == ()

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            SearchResult(query="")

    def test_with_hits(self):
        r = SearchResult(
            query="fashion",
            users=(SearchUserHit(username="alice"),),
            hashtags=(SearchHashtagHit(name="fashionweek", media_count=1),),
            places=(SearchPlaceHit(pk="42", name="Tashkent"),),
        )
        assert len(r.users) == 1
        assert r.hashtags[0].media_count == 1


class TestSearchHits:
    def test_user_hit_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            SearchUserHit(username="")

    def test_hashtag_hit_negative_count_rejected(self):
        with pytest.raises(ValidationError):
            SearchHashtagHit(name="x", media_count=-1)

    def test_place_hit_empty_pk_rejected(self):
        with pytest.raises(ValidationError):
            SearchPlaceHit(pk="", name="x")
