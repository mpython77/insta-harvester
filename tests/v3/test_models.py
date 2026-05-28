"""Tests for v3 Pydantic models (Profile, BioLink, BusinessInfo)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from instaharvest._v3 import BioLink, BusinessInfo, Profile


class TestProfile:
    def test_minimal_valid(self):
        p = Profile(username="alice", posts=10, followers=20, following=5)
        assert p.username == "alice"
        assert p.is_verified is False
        assert p.data_source == "api"
        assert p.bio_links == []

    def test_negative_counts_rejected(self):
        with pytest.raises(ValidationError):
            Profile(username="x", posts=-1, followers=0, following=0)

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            Profile(username="", posts=0, followers=0, following=0)

    def test_invalid_data_source_rejected(self):
        with pytest.raises(ValidationError):
            Profile(
                username="x",
                posts=0,
                followers=0,
                following=0,
                data_source="cache",
            )

    def test_is_frozen(self):
        p = Profile(username="x", posts=0, followers=0, following=0)
        with pytest.raises(ValidationError):
            p.followers = 9999  # type: ignore[misc]

    def test_unknown_fields_ignored_not_errored(self):
        # Future-proofing: when Instagram adds a new bio field, an old
        # client should keep working. ``extra="ignore"`` makes that safe.
        p = Profile(
            username="x",
            posts=0,
            followers=0,
            following=0,
            mystery_future_field="???",  # type: ignore[call-arg]
        )
        assert not hasattr(p, "mystery_future_field")


class TestBioLink:
    def test_valid_url(self):
        link = BioLink(url="https://example.com/foo")
        assert str(link.url) == "https://example.com/foo"

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            BioLink(url="not a url")

    def test_title_optional(self):
        link = BioLink(url="https://example.com/")
        assert link.title is None


class TestBusinessInfo:
    def test_default_all_off(self):
        info = BusinessInfo()
        assert info.is_business is False
        assert info.is_professional is False
        assert info.email is None

    def test_full_construction(self):
        info = BusinessInfo(
            is_business=True,
            category="Restaurant",
            email="hi@example.com",
            phone="+1-555",
            address="1 Main St, City",
        )
        assert info.is_business is True
        assert info.category == "Restaurant"
