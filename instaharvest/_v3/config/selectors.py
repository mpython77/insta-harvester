"""Instagram-specific CSS selectors.

Owned by: scrapers.

These are the *only* place where Instagram DOM details live.
When Instagram ships a redesign, this file is the single point
of change. Selectors are grouped by surface (profile, post, etc.)
to keep cohesion high.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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

    rate_limit_indicators: tuple = (
        "Try Again Later",
        "Action Blocked",
        "We restrict certain activity",
        "/challenge/",
        "/action_blocked/",
    )

    login_required_indicators: tuple = (
        '/accounts/login',
        '/accounts/emailsignup',
    )


@dataclass(frozen=True)
class SelectorConfig:
    """Top-level selector container.

    Compose more sub-groups here as scrapers are migrated.
    """

    profile: ProfileSelectors = field(default_factory=ProfileSelectors)
