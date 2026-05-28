"""
MediaScraper — one scraper for posts and reels.

Instagram represents posts and reels with the same JSON shape; only
``media_type`` and ``product_type`` differ. v3 reflects that with a
single :class:`MediaScraper` returning a :class:`Media` whose
:attr:`Media.kind` is one of :class:`MediaKind`. This replaces the
legacy ``post_data.PostDataScraper`` (1,870 LOC) and
``reel_data.ReelDataScraper`` (720 LOC), which duplicated 80% of each
other.

Strategy:

  1. Resolve the input (URL or bare shortcode) to a shortcode.
  2. Try Instagram's ``api/v1/media/{shortcode}/info`` style endpoint
     via :class:`HttpClient`. One call, structured JSON, exact counts.
  3. On API failure, fall back to navigating the post page through
     :class:`BrowserSession` and parsing the shared-data JSON that
     Instagram embeds in ``<script>``.

Both paths yield the same :class:`Media`. ``data_source`` records which
path served the value.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.selectors import MediaSelectors
from instaharvest._v3.core.exceptions import (
    NetworkError,
    ParseError,
    ProfileNotFoundError,
)
from instaharvest._v3.core.models import (
    CarouselItem,
    Media,
    MediaKind,
    MediaLocation,
    MediaOwner,
)
from instaharvest._v3.core.protocols import BrowserSession, HttpClient, Logger
from instaharvest._v3.scrapers._parsing import (
    build_media_url,
    extract_shortcode,
    infer_media_kind,
)
from instaharvest._v3.scrapers.base import AbstractScraper


_API_URL = "https://i.instagram.com/api/v1/media/{shortcode}/info/"

_API_HEADERS = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

# Instagram embeds the rendered post payload in a ``<script>`` block on the
# DOM-rendered page. We grep for the ``"shortcode_media":`` key and then
# walk the following JSON object with a brace-balancing parser; vanilla
# regex cannot match nested braces, so a regex-only approach trips on the
# inner ``"user": {…}`` object before reaching the outer ``}``.
_DOM_JSON_KEY_RE = re.compile(r'"shortcode_media"\s*:\s*\{')


# --- MediaNotFoundError reuses ProfileNotFoundError-ish semantics, but for
# media the canonical "doesn't exist" response is also a 404 from the same
# subdomain. We keep ProfileNotFoundError for the profile case and define a
# narrow alias here so callers can disambiguate without catching everything.
class MediaNotFoundError(ProfileNotFoundError):
    """The requested media (post / reel) does not exist or is unavailable.

    Subclassing :class:`ProfileNotFoundError` keeps a single "not found on
    Instagram" exception type that callers can catch generically while
    still allowing precise dispatch when needed.
    """

    def __init__(self, shortcode: str):
        # Bypass ProfileNotFoundError's username-flavoured message.
        Exception.__init__(self, f"Media not found: {shortcode}")
        self.username = shortcode  # legacy compat: ProfileNotFoundError uses .username
        self.shortcode = shortcode


class MediaScraper(AbstractScraper):
    """Scrape one Instagram post or reel.

    Construct via :attr:`InstaHarvest.media`; direct instantiation is
    supported but not the recommended path.
    """

    def __init__(
        self,
        *,
        browser: BrowserSession,
        http: HttpClient,
        logger: Logger,
        rate_limit: RateLimitConfig,
        selectors: MediaSelectors,
    ) -> None:
        # The base class wants a ProfileSelectors-shaped object only for its
        # rate_limit_indicators / login_required_indicators tuples. The
        # MediaSelectors dataclass has the same field names, so the shared
        # detection code works as-is via duck typing.
        super().__init__(
            browser=browser,
            logger=logger,
            rate_limit=rate_limit,
            selectors=selectors,  # type: ignore[arg-type]
        )
        self._http = http
        self._media_selectors = selectors

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self, url_or_shortcode: str, *, prefer_api: bool = True) -> Media:
        """Return :class:`Media` for the post or reel.

        ``url_or_shortcode`` may be:

          * a full URL (``https://www.instagram.com/p/<code>/``),
          * a reel URL (``https://www.instagram.com/reel/<code>/``),
          * a legacy IGTV URL (``/tv/<code>/``),
          * or just a bare shortcode (``<code>``).

        Raises:
            ValueError: input is not a recognisable URL or shortcode.
            MediaNotFoundError: the post does not exist.
            SessionExpiredError: DOM fallback was redirected to login.
            RateLimitedError: cooldown budget exhausted.
            NetworkError: the underlying HTTP/browser call kept failing.
            ParseError: the response was reachable but unreadable.
        """
        shortcode = extract_shortcode(url_or_shortcode)
        self._logger.info("media scrape start", shortcode=shortcode)

        if prefer_api:
            api_media = self._try_api(shortcode)
            if api_media is not None:
                self._logger.info(
                    "media scrape ok",
                    shortcode=shortcode,
                    source="api",
                    kind=api_media.kind.value,
                )
                return api_media

        dom_media = self._scrape_dom(shortcode)
        self._logger.info(
            "media scrape ok",
            shortcode=shortcode,
            source="dom",
            kind=dom_media.kind.value,
        )
        return dom_media

    # ------------------------------------------------------------------
    # API path
    # ------------------------------------------------------------------

    def _try_api(self, shortcode: str) -> Optional[Media]:
        """Best-effort API call.

        Only :class:`MediaNotFoundError` propagates out; every other
        failure is logged and the caller falls back to DOM.
        """
        url = _API_URL.format(shortcode=shortcode)
        try:
            resp = self._http.get(url, headers=_API_HEADERS)
        except NetworkError as exc:
            self._logger.warning(
                "media api network error", shortcode=shortcode, error=str(exc)
            )
            return None

        if resp.status_code == 404:
            raise MediaNotFoundError(shortcode)
        if resp.status_code >= 400:
            self._logger.warning(
                "media api non-2xx",
                shortcode=shortcode,
                status=resp.status_code,
            )
            return None

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            self._logger.warning(
                "media api returned non-json",
                shortcode=shortcode,
                error=str(exc),
            )
            return None

        item = _first_item(payload)
        if item is None:
            return None

        try:
            return _media_from_api(shortcode, item, source="api")
        except (KeyError, TypeError, ValueError) as exc:
            raise ParseError(
                f"could not parse API media response for {shortcode!r}",
                source="media_api",
            ) from exc

    # ------------------------------------------------------------------
    # DOM path
    # ------------------------------------------------------------------

    def _scrape_dom(self, shortcode: str) -> Media:
        url = build_media_url(shortcode)
        self.navigate(url)

        content = self._browser.page_content()
        for marker in self._media_selectors.not_found_strings:
            if marker in content:
                raise MediaNotFoundError(shortcode)

        match = _DOM_JSON_KEY_RE.search(content)
        if not match:
            # Without the embedded JSON we cannot guarantee correct
            # counts, so we surface ParseError instead of returning a
            # half-built Media. Callers can retry or escalate.
            raise ParseError(
                f"could not locate shortcode_media JSON in DOM for {shortcode!r}",
                source="media_dom",
            )

        try:
            item = _extract_balanced_object(content, match.end() - 1)
            return _media_from_api(shortcode, item, source="dom")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ParseError(
                f"could not parse DOM media JSON for {shortcode!r}",
                source="media_dom",
            ) from exc


# ---------------------------------------------------------------------------
# Helpers (pure, framework-free)
# ---------------------------------------------------------------------------


def _first_item(payload: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """The Instagram media API returns ``{"items": [<media_dict>]}``."""
    items = payload.get("items") if isinstance(payload, Mapping) else None
    if isinstance(items, list) and items and isinstance(items[0], Mapping):
        return items[0]
    return None


def _extract_balanced_object(text: str, start: int) -> Mapping[str, Any]:
    """Parse the JSON object that begins at ``text[start]`` (which must be ``{``).

    Walks forward counting brace depth, with awareness of string literals
    and backslash escapes, until the matching closing ``}`` is found.
    Returns the decoded object.

    Raises:
        ValueError: ``text[start]`` is not ``{`` or the object never closes.
        json.JSONDecodeError: the substring is not valid JSON.
    """
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"expected '{{' at offset {start}")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise ValueError("unterminated JSON object")


def _media_from_api(
    shortcode: str,
    item: Mapping[str, Any],
    *,
    source: str,
) -> Media:
    """Build a :class:`Media` from one Instagram media JSON object."""

    media_type = item.get("media_type")
    product_type = item.get("product_type")
    kind = infer_media_kind(media_type=media_type, product_type=product_type)

    owner = _owner_from_api(item.get("user") or item.get("owner") or {})
    location = _location_from_api(item.get("location"))
    caption_text = _caption_text(item.get("caption"))
    width, height = _dimensions(item)

    image_url, video_url, video_duration, has_audio, accessibility = _top_level_media(item)

    carousel = _carousel_from_api(item.get("carousel_media") or [])
    if kind == MediaKind.CAROUSEL and not carousel:
        # Some endpoints return ``media_type=8`` without expanding the
        # carousel children. Treat that as a parse failure rather than
        # silently dropping the slides.
        raise ValueError("carousel media_type but no carousel_media items")

    tagged = tuple(_extract_tagged_users(item.get("usertags")))

    taken_at = item.get("taken_at")
    if taken_at is None:
        # DOM payloads sometimes call this ``date`` or ``timestamp``.
        taken_at = item.get("timestamp") or item.get("date") or 0

    return Media(
        shortcode=shortcode,
        url=build_media_url(shortcode, kind=kind),
        kind=kind,
        owner=owner,
        taken_at=taken_at,
        caption=caption_text,
        like_count=int(item.get("like_count") or 0),
        comment_count=int(item.get("comment_count") or 0),
        image_url=image_url,
        video_url=video_url,
        video_duration=video_duration,
        has_audio=bool(has_audio),
        width=width,
        height=height,
        accessibility_caption=accessibility,
        location=location,
        tagged_usernames=tagged,
        carousel=carousel,
        data_source=source,
    )


def _owner_from_api(user: Mapping[str, Any]) -> MediaOwner:
    return MediaOwner(
        username=str(user.get("username") or "unknown"),
        user_id=str(user["pk"]) if user.get("pk") is not None else (
            str(user["id"]) if user.get("id") is not None else None
        ),
        full_name=user.get("full_name") or None,
        is_verified=bool(user.get("is_verified", False)),
        profile_pic_url=user.get("profile_pic_url") or None,
    )


def _location_from_api(loc: Optional[Mapping[str, Any]]) -> Optional[MediaLocation]:
    if not loc or not loc.get("name"):
        return None
    return MediaLocation(
        name=loc["name"],
        pk=str(loc["pk"]) if loc.get("pk") is not None else None,
        latitude=loc.get("lat") or loc.get("latitude"),
        longitude=loc.get("lng") or loc.get("longitude"),
    )


def _caption_text(caption: Any) -> Optional[str]:
    if isinstance(caption, Mapping):
        text = caption.get("text")
        return text if isinstance(text, str) and text else None
    if isinstance(caption, str) and caption:
        return caption
    return None


def _dimensions(item: Mapping[str, Any]) -> Tuple[int, int]:
    """API returns ``original_width`` / ``original_height``; DOM uses ``dimensions``."""
    if "original_width" in item and "original_height" in item:
        return int(item["original_width"]), int(item["original_height"])
    dims = item.get("dimensions") or {}
    if isinstance(dims, Mapping):
        return int(dims.get("width", 0) or 0), int(dims.get("height", 0) or 0)
    return 0, 0


def _top_level_media(
    item: Mapping[str, Any],
) -> Tuple[Optional[str], Optional[str], Optional[float], bool, Optional[str]]:
    """Extract image/video URL, duration, audio flag, accessibility caption."""
    image_url = _first_image_url(item)
    video_url = _first_video_url(item)
    duration = item.get("video_duration")
    if duration is not None:
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = None
    has_audio = bool(item.get("has_audio", False))
    accessibility = item.get("accessibility_caption") or None
    return image_url, video_url, duration, has_audio, accessibility


def _first_image_url(item: Mapping[str, Any]) -> Optional[str]:
    candidates = (item.get("image_versions2") or {}).get("candidates") or []
    if isinstance(candidates, list):
        for cand in candidates:
            if isinstance(cand, Mapping) and cand.get("url"):
                return cand["url"]
    # DOM-style payload
    if isinstance(item.get("display_url"), str):
        return item["display_url"]
    return None


def _first_video_url(item: Mapping[str, Any]) -> Optional[str]:
    versions = item.get("video_versions") or []
    if isinstance(versions, list):
        for v in versions:
            if isinstance(v, Mapping) and v.get("url"):
                return v["url"]
    if isinstance(item.get("video_url"), str):
        return item["video_url"]
    return None


def _carousel_from_api(items: List[Mapping[str, Any]]) -> Tuple[CarouselItem, ...]:
    out: List[CarouselItem] = []
    for index, child in enumerate(items):
        if not isinstance(child, Mapping):
            continue
        kind = infer_media_kind(
            media_type=child.get("media_type"),
            product_type=child.get("product_type"),
        )
        # CarouselItem requires atomic kind (image/video).
        if kind == MediaKind.REEL:
            kind = MediaKind.VIDEO
        elif kind == MediaKind.CAROUSEL:
            kind = MediaKind.IMAGE
        width, height = _dimensions(child)
        image_url = _first_image_url(child)
        video_url = _first_video_url(child)
        video_duration = child.get("video_duration")
        try:
            video_duration = float(video_duration) if video_duration is not None else None
        except (TypeError, ValueError):
            video_duration = None
        out.append(
            CarouselItem(
                index=index,
                kind=kind,
                width=width,
                height=height,
                image_url=image_url,
                video_url=video_url,
                video_duration=video_duration,
                has_audio=bool(child.get("has_audio", False)),
                accessibility_caption=child.get("accessibility_caption") or None,
                tagged_usernames=tuple(_extract_tagged_users(child.get("usertags"))),
            )
        )
    return tuple(out)


def _extract_tagged_users(tags: Any) -> List[str]:
    """Pull ``["username", ...]`` out of the various Instagram tag shapes."""
    out: List[str] = []
    if not tags:
        return out
    container = tags
    if isinstance(tags, Mapping):
        # API: ``{"in": [{"user": {"username": ...}}]}``
        container = tags.get("in") or tags.get("edges") or []
    if not isinstance(container, list):
        return out
    seen: set = set()
    for entry in container:
        if not isinstance(entry, Mapping):
            continue
        user = (entry.get("user") or entry.get("node") or {})
        if isinstance(user, Mapping):
            username = user.get("username")
            if isinstance(username, str) and username and username not in seen:
                seen.add(username)
                out.append(username)
    return out


__all__ = ["MediaScraper", "MediaNotFoundError"]
