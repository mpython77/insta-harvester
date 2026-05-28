"""Instagram-specific CSS selectors.

Owned by: scrapers.

These are the *only* place where Instagram DOM details live.
When Instagram ships a redesign, this file is the single point
of change. Selectors are grouped by surface (profile, media, comments)
to keep cohesion high.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Shared signals
# ---------------------------------------------------------------------------

# Login / rate-limit indicators are shared across surfaces. Keeping them in
# one place avoids accidental drift between profile vs media detection.

_LOGIN_INDICATORS: tuple = (
    "/accounts/login",
    "/accounts/emailsignup",
)

_RATE_LIMIT_INDICATORS: tuple = (
    "Try Again Later",
    "Action Blocked",
    "We restrict certain activity",
    "/challenge/",
    "/action_blocked/",
)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProfileSelectors:
    """Selectors used by ``scrapers.profile``."""

    posts_count: str = 'header section ul li:nth-child(1)'
    followers_link: str = 'a[href$="/followers/"]'
    following_link: str = 'a[href$="/following/"]'
    verified_badge: str = 'svg[aria-label="Verified"]'
    private_icon: str = 'svg[aria-label="Private"]'
    bio_text: str = 'header section span[dir="auto"]'
    profile_category: str = 'header section div[class*="category"]'

    not_found_strings: tuple = (
        "Sorry, this page isn't available.",
        "The link you followed may be broken",
    )

    rate_limit_indicators: tuple = _RATE_LIMIT_INDICATORS
    login_required_indicators: tuple = _LOGIN_INDICATORS


# ---------------------------------------------------------------------------
# Media (post / reel)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MediaSelectors:
    """Selectors used by ``scrapers.media``.

    The DOM path is a fallback only — the API path is preferred and
    handles the bulk of cases. These selectors are deliberately broad
    because Instagram's post page rewrites are frequent.
    """

    article: str = "article[role='presentation']"
    image: str = "article img[srcset], article img[src]"
    video: str = "article video[src]"
    like_button_count: str = "section span"  # heuristic: like count near the heart icon
    caption: str = "h1, article div[role='button'] span"
    timestamp: str = "time[datetime]"
    owner_link: str = "article header a[role='link']"

    not_found_strings: tuple = (
        "Sorry, this page isn't available.",
        "The link you followed may be broken",
    )

    rate_limit_indicators: tuple = _RATE_LIMIT_INDICATORS
    login_required_indicators: tuple = _LOGIN_INDICATORS


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommentSelectors:
    """Selectors used by ``scrapers.comments``.

    Comments scraping in v3 is API-first; the DOM selectors are kept
    for the rare cases where the API path is unavailable (very old
    posts, aggressive rate-limiting). They mirror the same rate-limit
    and login indicators as the rest of the app.
    """

    comment_thread: str = 'ul[class*="comment"] > li'
    comment_text: str = 'span[dir="auto"]'
    comment_author_link: str = 'a[role="link"]'
    load_more_replies: str = 'button:has-text("View replies")'
    load_more_comments: str = 'button:has-text("View more comments"), button[aria-label*="Load more"]'

    rate_limit_indicators: tuple = _RATE_LIMIT_INDICATORS
    login_required_indicators: tuple = _LOGIN_INDICATORS


# ---------------------------------------------------------------------------
# Top-level container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectorConfig:
    """Top-level selector container.

    Compose more sub-groups here as scrapers are migrated.
    """

    profile: ProfileSelectors = field(default_factory=ProfileSelectors)
    media: MediaSelectors = field(default_factory=MediaSelectors)
    comments: CommentSelectors = field(default_factory=CommentSelectors)
