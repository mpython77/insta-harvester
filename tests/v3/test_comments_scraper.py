"""Tests for CommentScraper — pagination, replies, error handling."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.selectors import CommentSelectors
from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.scrapers.comments import CommentScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scraper(http: FakeHttpClient) -> CommentScraper:
    return CommentScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
        selectors=CommentSelectors(),
    )


_INFO_URL = "https://i.instagram.com/api/v1/media/ABC1234/info/"
_COMMENTS_URL = "https://i.instagram.com/api/v1/media/9999/comments/"
_REPLIES_URL_PREFIX = "https://i.instagram.com/api/v1/media/9999/comments/"


def _info_response() -> FakeHttpResponse:
    """A minimal /info response that resolves the media to id 9999."""
    return FakeHttpResponse(
        status_code=200,
        json_data={"items": [{"pk": 9999, "id": "9999"}]},
    )


def _comment(pk: str, text: str = "hi", reply_count: int = 0) -> Dict[str, Any]:
    return {
        "pk": pk,
        "text": text,
        "user": {"pk": 1, "username": "bob"},
        "created_at": 1_700_000_000,
        "comment_like_count": 0,
        "child_comment_count": reply_count,
    }


class _PaginatedResponder:
    """Returns a different response per call to a single URL.

    Lets us simulate Instagram's paginated comments API without
    monkey-patching :class:`FakeHttpClient`.
    """

    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self._pages = pages
        self._next = 0

    def __call__(self) -> FakeHttpResponse:
        if self._next >= len(self._pages):
            return FakeHttpResponse(status_code=200, json_data={"comments": []})
        page = self._pages[self._next]
        self._next += 1
        return FakeHttpResponse(status_code=200, json_data=page)


def _install_paginated(
    http: FakeHttpClient,
    url_prefix: str,
    pages: List[Dict[str, Any]],
) -> None:
    """Wire ``http._lookup`` to return successive ``pages`` for ``url_prefix``."""
    responder = _PaginatedResponder(pages)
    original_get = http.get

    def get(url: str, *, params=None, headers=None):
        if url.startswith(url_prefix):
            http.calls.append({"method": "GET", "url": url, "params": dict(params) if params else None})
            return responder()
        return original_get(url, params=params, headers=headers)

    http.get = get  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Top-level scrape
# ---------------------------------------------------------------------------


class TestSingleScrape:
    def test_one_page_returned(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1"), _comment("2")], "next_min_id": None},
        ])

        page = _make_scraper(http).scrape("ABC1234", include_replies=False)
        assert page.media_shortcode == "ABC1234"
        assert page.total_returned == 2
        assert page.has_more is False
        assert [c.id for c in page.comments] == ["1", "2"]

    def test_pagination_walks_until_cursor_none(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1"), _comment("2")], "next_min_id": "cursor_1"},
            {"comments": [_comment("3")], "next_min_id": "cursor_2"},
            {"comments": [_comment("4")], "next_min_id": None},
        ])

        page = _make_scraper(http).scrape("ABC1234", include_replies=False)
        assert [c.id for c in page.comments] == ["1", "2", "3", "4"]
        assert page.has_more is False

    def test_max_comments_caps_collection(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment(str(i)) for i in range(50)], "next_min_id": "k"},
            {"comments": [_comment(str(i)) for i in range(50, 100)], "next_min_id": None},
        ])

        page = _make_scraper(http).scrape(
            "ABC1234", max_comments=30, include_replies=False
        )
        assert page.total_returned == 30
        assert page.has_more is True

    def test_negative_max_comments_rejected(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        with pytest.raises(ValueError):
            _make_scraper(http).scrape("ABC1234", max_comments=-1)

    def test_url_input_accepted(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1")], "next_min_id": None},
        ])
        page = _make_scraper(http).scrape(
            "https://www.instagram.com/p/ABC1234/",
            include_replies=False,
        )
        assert page.media_shortcode == "ABC1234"


# ---------------------------------------------------------------------------
# Replies
# ---------------------------------------------------------------------------


class TestReplies:
    def test_skipped_when_include_replies_false(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1", reply_count=5)], "next_min_id": None},
        ])

        page = _make_scraper(http).scrape("ABC1234", include_replies=False)
        assert page.comments[0].replies == ()

    def test_skipped_when_reply_count_zero(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1", reply_count=0)], "next_min_id": None},
        ])

        # If the scraper tried to fetch replies, the call would fail
        # because no _REPLIES_URL_PREFIX responder is wired up.
        page = _make_scraper(http).scrape("ABC1234", include_replies=True)
        assert page.comments[0].replies == ()

    def test_fetched_when_present(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1", reply_count=2)], "next_min_id": None},
        ])

        # Replies live under /comments/<comment_id>/child_comments/.
        # _install_paginated overrides http.get by URL prefix, so the
        # second call here installs the replies responder on top.
        replies_url = f"{_REPLIES_URL_PREFIX}1/child_comments/"
        _install_paginated(http, replies_url, [
            {
                "child_comments": [
                    _comment("1a"),
                    _comment("1b"),
                ],
                "next_min_id": None,
            },
        ])

        page = _make_scraper(http).scrape("ABC1234", include_replies=True)
        assert len(page.comments) == 1
        assert len(page.comments[0].replies) == 2
        assert page.comments[0].replies[0].parent_id == "1"

    def test_reply_failure_keeps_parent(self):
        """If replies fetch raises NetworkError, parent comment still appears."""
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()
        _install_paginated(http, _COMMENTS_URL, [
            {"comments": [_comment("1", reply_count=2)], "next_min_id": None},
        ])

        # Wire the replies URL to raise.
        replies_url = f"{_REPLIES_URL_PREFIX}1/child_comments/"
        original_get = http.get

        def get(url: str, *, params=None, headers=None):
            if url.startswith(replies_url):
                raise NetworkError("simulated", url=url)
            return original_get(url, params=params, headers=headers)

        http.get = get  # type: ignore[assignment]

        page = _make_scraper(http).scrape("ABC1234", include_replies=True)
        # Parent survived; replies are empty.
        assert len(page.comments) == 1
        assert page.comments[0].replies == ()


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestErrors:
    def test_info_lookup_5xx_raises_network_error(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=500)
        with pytest.raises(NetworkError):
            _make_scraper(http).scrape("ABC1234", include_replies=False)

    def test_info_lookup_invalid_json_raises_parse_error(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=200, text="not json")
        with pytest.raises(ParseError):
            _make_scraper(http).scrape("ABC1234", include_replies=False)

    def test_partial_results_when_pagination_5xxs(self):
        """Mid-walk 5xx returns the comments collected so far with has_more=True."""
        http = FakeHttpClient()
        http.responses[_INFO_URL] = _info_response()

        # First page ok, second page 5xx.
        responses = [
            FakeHttpResponse(
                status_code=200,
                json_data={"comments": [_comment("1"), _comment("2")], "next_min_id": "cursor"},
            ),
            FakeHttpResponse(status_code=503),
        ]
        idx = [0]
        original_get = http.get

        def get(url: str, *, params=None, headers=None):
            if url.startswith(_COMMENTS_URL):
                http.calls.append({"method": "GET", "url": url, "params": params})
                resp = responses[idx[0]]
                idx[0] += 1
                return resp
            return original_get(url, params=params, headers=headers)

        http.get = get  # type: ignore[assignment]

        page = _make_scraper(http).scrape("ABC1234", include_replies=False)
        assert page.total_returned == 2
        assert page.has_more is True
        assert page.next_cursor == "cursor"
