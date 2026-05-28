"""Tests for v3 Media-related models (Media, MediaKind, CarouselItem, MediaOwner)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from instaharvest.core.models import (
    CarouselItem,
    Media,
    MediaKind,
    MediaLocation,
    MediaOwner,
)


def _owner() -> MediaOwner:
    return MediaOwner(username="alice")


def _media(**overrides) -> Media:
    base = dict(
        shortcode="ABC123",
        url="https://www.instagram.com/p/ABC123/",
        kind=MediaKind.IMAGE,
        owner=_owner(),
        taken_at=1_700_000_000,
        like_count=10,
        comment_count=2,
    )
    base.update(overrides)
    return Media(**base)


class TestMediaCore:
    def test_minimal_image_media(self):
        m = _media()
        assert m.kind == MediaKind.IMAGE
        assert m.owner.username == "alice"
        assert m.taken_at.tzinfo == timezone.utc
        assert m.data_source == "api"

    def test_negative_like_count_rejected(self):
        with pytest.raises(ValidationError):
            _media(like_count=-1)

    def test_invalid_data_source_rejected(self):
        with pytest.raises(ValidationError):
            _media(data_source="cache")

    def test_taken_at_int_normalised_to_utc(self):
        m = _media(taken_at=1_700_000_000)
        assert m.taken_at.year == 2023
        assert m.taken_at.tzinfo is timezone.utc

    def test_taken_at_naive_datetime_normalised_to_utc(self):
        naive = datetime(2024, 1, 1, 12, 0, 0)
        m = _media(taken_at=naive)
        assert m.taken_at.tzinfo is timezone.utc

    def test_is_frozen(self):
        m = _media()
        with pytest.raises(ValidationError):
            m.like_count = 9999  # type: ignore[misc]

    def test_unknown_fields_ignored_not_errored(self):
        m = _media(future_field="???")  # type: ignore[call-arg]
        assert not hasattr(m, "future_field")


class TestMediaCarousel:
    def _slide(self, index: int, kind: MediaKind = MediaKind.IMAGE) -> CarouselItem:
        return CarouselItem(index=index, kind=kind, width=100, height=100)

    def test_valid_carousel_passes(self):
        m = _media(
            kind=MediaKind.CAROUSEL,
            carousel=(self._slide(0), self._slide(1, MediaKind.VIDEO), self._slide(2)),
        )
        assert len(m.carousel) == 3

    def test_carousel_index_gap_rejected(self):
        with pytest.raises(ValidationError):
            _media(
                kind=MediaKind.CAROUSEL,
                carousel=(self._slide(0), self._slide(2)),
            )

    def test_carousel_index_duplicate_rejected(self):
        with pytest.raises(ValidationError):
            _media(
                kind=MediaKind.CAROUSEL,
                carousel=(self._slide(0), self._slide(0)),
            )

    def test_carousel_item_kind_must_be_atomic(self):
        with pytest.raises(ValidationError):
            CarouselItem(index=0, kind=MediaKind.CAROUSEL, width=10, height=10)
        with pytest.raises(ValidationError):
            CarouselItem(index=0, kind=MediaKind.REEL, width=10, height=10)


class TestMediaOwner:
    def test_minimal(self):
        o = MediaOwner(username="alice")
        assert o.is_verified is False

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            MediaOwner(username="")


class TestMediaLocation:
    def test_minimal(self):
        loc = MediaLocation(name="Tashkent")
        assert loc.latitude is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            MediaLocation(name="")
