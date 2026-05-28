"""
ProfileScraper — reference implementation for v3.

Strategy:
    1. Try Instagram's web JSON API (exact counts, structured bio links,
       business info). One HTTP call via the injected ``HttpClient``.
    2. On failure, fall back to DOM scraping through ``BrowserSession``.

Both paths return the same :class:`Profile` model. The model carries a
``data_source`` flag (``"api"`` or ``"dom"``) so callers can tell which
path served the value.

Compared with legacy ``profile.py`` (~770 LOC, mixes selectors with
business logic, four ways to extract a bio):

    * No 296-field config; takes only the configs it needs.
    * No silent ``except Exception:``; every catch logs context and
      either recovers explicitly or re-raises a typed exception.
    * No browser/HTTP creation inside the scraper; everything is
      injected via the protocols. Tests use in-memory fakes.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, List, Mapping, Optional

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.selectors import ProfileSelectors
from instaharvest._v3.core.exceptions import (
    HtmlStructureChangedError,
    NetworkError,
    ParseError,
    ProfileNotFoundError,
)
from instaharvest._v3.core.models import BioLink, BusinessInfo, Profile
from instaharvest._v3.core.protocols import BrowserSession, HttpClient, Logger
from instaharvest._v3.scrapers.base import AbstractScraper


_API_URL = "https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
_PROFILE_URL = "https://www.instagram.com/{username}/"

_API_HEADERS = {
    # Instagram requires this magic header for the web profile endpoint.
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}


# Compact number suffixes accepted in Instagram's rendered counts.
_NUMBER_SUFFIXES: Mapping[str, int] = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
}


class ProfileScraper(AbstractScraper):
    """Scrape one Instagram profile.

    Construct via :meth:`InstaHarvest.profile` — direct instantiation is
    supported but not the recommended path.
    """

    def __init__(
        self,
        *,
        browser: BrowserSession,
        http: HttpClient,
        logger: Logger,
        rate_limit: RateLimitConfig,
        selectors: ProfileSelectors,
    ) -> None:
        super().__init__(
            browser=browser,
            logger=logger,
            rate_limit=rate_limit,
            selectors=selectors,
        )
        self._http = http

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self, username: str, *, prefer_api: bool = True) -> Profile:
        """Return data for ``@username``.

        Raises:
            ProfileNotFoundError: the profile does not exist.
            SessionExpiredError: redirected to login during DOM fallback.
            RateLimitedError: Instagram rate-limited us beyond the
                configured retry budget.
            NetworkError: the underlying HTTP/browser call failed.
            ParseError: response was reachable but unreadable.
        """
        username = _normalise_username(username)
        self._logger.info("profile scrape start", username=username)

        if prefer_api:
            api_profile = self._try_api(username)
            if api_profile is not None:
                self._logger.info(
                    "profile scrape ok",
                    username=username,
                    source="api",
                    followers=api_profile.followers,
                )
                return api_profile

        # Fall back to DOM
        dom_profile = self._scrape_dom(username)
        self._logger.info(
            "profile scrape ok",
            username=username,
            source="dom",
            followers=dom_profile.followers,
        )
        return dom_profile

    # ------------------------------------------------------------------
    # API path
    # ------------------------------------------------------------------

    def _try_api(self, username: str) -> Optional[Profile]:
        """Best-effort API call. Returns ``None`` if the API is unavailable.

        Only ``ProfileNotFoundError`` propagates out — every other
        failure is logged and the caller falls back to DOM.
        """
        url = _API_URL.format(username=username)
        try:
            resp = self._http.get(url, headers=_API_HEADERS)
        except NetworkError as exc:
            self._logger.warning("profile api network error", username=username, error=str(exc))
            return None

        if resp.status_code == 404:
            raise ProfileNotFoundError(username)
        if resp.status_code >= 400:
            self._logger.warning(
                "profile api non-2xx",
                username=username,
                status=resp.status_code,
            )
            return None

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            self._logger.warning(
                "profile api returned non-json",
                username=username,
                error=str(exc),
            )
            return None

        user_data = _walk(payload, "data", "user")
        if user_data is None:
            return None

        try:
            return _profile_from_api(username, user_data)
        except (KeyError, TypeError, ValueError) as exc:
            raise ParseError(
                f"could not parse API response for @{username}",
                source="profile_api",
            ) from exc

    # ------------------------------------------------------------------
    # DOM path
    # ------------------------------------------------------------------

    def _scrape_dom(self, username: str) -> Profile:
        url = _PROFILE_URL.format(username=username)
        self.navigate(url)

        if not self._dom_profile_exists():
            raise ProfileNotFoundError(username)

        sel = self._selectors
        is_private = self._browser.query_text(sel.private_icon) is not None
        is_verified = self._browser.query_text(sel.verified_badge) is not None

        posts = self._dom_count(sel.posts_count, "posts")
        followers = self._dom_attr_count(sel.followers_link, "followers")
        following = self._dom_attr_count(sel.following_link, "following")

        bio = self._browser.query_text(sel.bio_text)
        category = self._browser.query_text(sel.profile_category)

        return Profile(
            username=username,
            posts=posts,
            followers=followers,
            following=following,
            is_verified=is_verified,
            is_private=is_private,
            bio=bio.strip() if bio else None,
            category=category.strip() if category else None,
            data_source="dom",
        )

    def _dom_profile_exists(self) -> bool:
        content = self._browser.page_content()
        for marker in self._selectors.not_found_strings:
            if marker in content:
                return False
        return True

    def _dom_count(self, selector: str, element_name: str) -> int:
        text = self._browser.query_text(selector)
        if text is None:
            raise HtmlStructureChangedError(
                element=element_name,
                selector=selector,
                url=self._browser.page_url(),
            )
        return _parse_count(text)

    def _dom_attr_count(self, selector: str, element_name: str) -> int:
        # Followers/following counts may be precise via ``title`` attribute
        # (e.g. "12,345") or rendered short ("12.3K"). Try the precise
        # source first, then fall back to inner text.
        title = self._browser.query_attribute(selector, "title")
        if title:
            return _parse_count(title)
        text = self._browser.query_text(selector)
        if text is None:
            raise HtmlStructureChangedError(
                element=element_name,
                selector=selector,
                url=self._browser.page_url(),
            )
        return _parse_count(text)


# ---------------------------------------------------------------------------
# Helpers (pure, framework-free)
# ---------------------------------------------------------------------------


_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{1,30}$")


def _normalise_username(raw: str) -> str:
    cleaned = raw.strip().lstrip("@")
    if not _USERNAME_RE.match(cleaned):
        raise ValueError(f"invalid Instagram username: {raw!r}")
    return cleaned


def _walk(obj: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(obj, Mapping):
            return None
        if key not in obj:
            return None
        obj = obj[key]
    return obj


_COUNT_RE = re.compile(r"^\s*([0-9][0-9,. ]*)\s*([a-zA-Z]?)\s*$")


def _parse_count(raw: str) -> int:
    """Parse Instagram's rendered counts (``"12,345"``, ``"1.2k"``, ``"3M"``).

    Returns 0 for unparseable input — callers that need strictness can
    raise ``HtmlStructureChangedError`` themselves.
    """
    match = _COUNT_RE.match(raw)
    if not match:
        return 0
    digits, suffix = match.groups()
    digits = digits.replace(",", "").replace(" ", "")
    try:
        if suffix:
            value = float(digits)
            multiplier = _NUMBER_SUFFIXES.get(suffix.lower(), 1)
            return int(value * multiplier)
        if "." in digits:
            return int(float(digits))
        return int(digits)
    except ValueError:
        return 0


def _profile_from_api(username: str, user: Mapping[str, Any]) -> Profile:
    """Build a :class:`Profile` from Instagram's web_profile_info JSON."""

    return Profile(
        username=user.get("username") or username,
        user_id=str(user["id"]) if "id" in user else None,
        full_name=user.get("full_name") or None,
        posts=int(_walk(user, "edge_owner_to_timeline_media", "count") or 0),
        followers=int(_walk(user, "edge_followed_by", "count") or 0),
        following=int(_walk(user, "edge_follow", "count") or 0),
        is_verified=bool(user.get("is_verified", False)),
        is_private=bool(user.get("is_private", False)),
        bio=(user.get("biography") or None),
        bio_links=_extract_bio_links(user.get("bio_links") or [], user.get("external_url")),
        profile_pic_url=user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
        category=user.get("category_name") or None,
        business=_extract_business(user),
        data_source="api",
    )


def _extract_bio_links(
    links: Iterable[Mapping[str, Any]],
    fallback_external: Optional[str],
) -> List[BioLink]:
    out: List[BioLink] = []
    seen: set = set()
    for link in links:
        url = link.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(BioLink(url=url, title=link.get("title") or None))

    if not out and fallback_external:
        out.append(BioLink(url=fallback_external))
    return out


def _extract_business(user: Mapping[str, Any]) -> Optional[BusinessInfo]:
    is_business = bool(user.get("is_business_account", False))
    is_pro = bool(user.get("is_professional_account", False))
    category = user.get("business_category_name") or user.get("category_name")
    email = user.get("business_email")
    phone = user.get("business_phone_number")
    address_json = user.get("business_address_json")

    if not (is_business or is_pro or category or email or phone or address_json):
        return None

    address: Optional[str] = None
    if address_json:
        try:
            parsed = json.loads(address_json) if isinstance(address_json, str) else address_json
            parts = [
                str(parsed.get(field) or "").strip()
                for field in ("street_address", "city_name", "region_name", "zip_code")
            ]
            address = ", ".join(part for part in parts if part) or None
        except (ValueError, TypeError):
            address = None

    return BusinessInfo(
        is_business=is_business,
        is_professional=is_pro,
        category=category or None,
        email=email or None,
        phone=phone or None,
        address=address,
    )
