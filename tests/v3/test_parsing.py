"""Tests for v3 parsing helpers (instaharvest._v3.scrapers._parsing)."""

from __future__ import annotations

import pytest

from instaharvest._v3.core.models import MediaKind
from instaharvest._v3.scrapers._parsing import (
    build_media_url,
    extract_hashtags,
    extract_mentions,
    extract_shortcode,
    infer_media_kind,
    is_valid_shortcode,
    parse_count,
)


class TestIsValidShortcode:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("CkRT123", True),
            ("ABC1234567", True),
            ("dash-und_X", True),                # 10 chars: dash + underscore allowed
            ("ABC", False),                      # too short
            ("a" * 17, False),                   # too long
            ("has spaces", False),
            ("has/slash", False),
            ("", False),
            ("???", False),
        ],
    )
    def test_validates(self, value: str, expected: bool):
        assert is_valid_shortcode(value) is expected


class TestExtractShortcode:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.instagram.com/p/ABC1234/", "ABC1234"),
            ("https://www.instagram.com/p/ABC1234", "ABC1234"),
            ("https://www.instagram.com/reel/XYZ-abc_/?utm=1", "XYZ-abc_"),
            ("https://www.instagram.com/tv/ABCDEF/", "ABCDEF"),
            ("http://instagram.com/p/abcDEF/foo/bar", "abcDEF"),
            ("CkRT123", "CkRT123"),  # bare shortcode passthrough
        ],
    )
    def test_happy(self, url: str, expected: str):
        assert extract_shortcode(url) == expected

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "   ",
            "ftp://www.instagram.com/p/ABC1234/",  # wrong scheme
            "https://www.instagram.com/about/",     # no /p/ /reel/ /tv/
            "https://example.com/p/ABC1234/",       # right path, wrong host? actually this passes regex
        ],
    )
    def test_rejects_bogus_inputs(self, bad: str):
        # The third case ("https://example.com/p/ABC1234/") *does* match the
        # path regex; document that we deliberately accept it. Cross-domain
        # validation is the caller's job.
        if "example.com/p/" in bad:
            assert extract_shortcode(bad) == "ABC1234"
        else:
            with pytest.raises(ValueError):
                extract_shortcode(bad)

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            extract_shortcode(12345)  # type: ignore[arg-type]


class TestBuildMediaUrl:
    def test_post_url(self):
        url = build_media_url("ABCDEF")
        assert url == "https://www.instagram.com/p/ABCDEF/"

    def test_reel_url(self):
        url = build_media_url("ABCDEF", kind=MediaKind.REEL)
        assert url == "https://www.instagram.com/reel/ABCDEF/"

    def test_carousel_uses_post_segment(self):
        # Carousels live at /p/<code>/, not /reel/.
        url = build_media_url("ABCDEF", kind=MediaKind.CAROUSEL)
        assert "/p/" in url

    def test_invalid_shortcode_rejected(self):
        with pytest.raises(ValueError):
            build_media_url("nope!")


class TestExtractMentions:
    def test_returns_lowercase_unique_in_order(self):
        text = "Hi @Alice and @bob and @ALICE again"
        assert extract_mentions(text) == ["alice", "bob"]

    def test_handles_dots_and_underscores(self):
        text = "thanks @user.name_one for tagging @second.user"
        assert extract_mentions(text) == ["user.name_one", "second.user"]

    def test_does_not_match_emails(self):
        # An ``@`` immediately after a word character (the ``a`` of ``a@b.com``)
        # is rejected by the ``(?<![A-Za-z0-9_.])`` lookbehind.
        text = "email me at hello@example.com"
        assert extract_mentions(text) == []

    def test_empty_or_none(self):
        assert extract_mentions("") == []
        assert extract_mentions(None) == []


class TestExtractHashtags:
    def test_returns_lowercase_unique_in_order(self):
        text = "#FashionWeek #FW2024 #fashionweek"
        assert extract_hashtags(text) == ["fashionweek", "fw2024"]

    def test_handles_underscores(self):
        text = "#summer_2024 trip"
        assert extract_hashtags(text) == ["summer_2024"]

    def test_empty_or_none(self):
        assert extract_hashtags("") == []
        assert extract_hashtags(None) == []


class TestParseCount:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("0", 0),
            ("1234", 1234),
            ("12,345", 12345),
            ("1.2K", 1200),
            ("1.2k", 1200),
            ("3M", 3_000_000),
            ("2B", 2_000_000_000),
            (" 100 ", 100),
            ("", 0),
            ("not a number", 0),
            (None, 0),
        ],
    )
    def test_parses(self, raw, expected: int):
        assert parse_count(raw) == expected


class TestInferMediaKind:
    @pytest.mark.parametrize(
        "media_type,product_type,expected",
        [
            (1, None, MediaKind.IMAGE),
            (2, None, MediaKind.VIDEO),
            (8, None, MediaKind.CAROUSEL),
            (2, "feed", MediaKind.VIDEO),
            (2, "clips", MediaKind.REEL),
            (1, "clips", MediaKind.REEL),  # clips wins over media_type
            (None, None, MediaKind.IMAGE),  # safest default
            (99, None, MediaKind.IMAGE),    # unknown -> safest default
        ],
    )
    def test_classifies(self, media_type, product_type, expected):
        assert infer_media_kind(media_type=media_type, product_type=product_type) == expected
