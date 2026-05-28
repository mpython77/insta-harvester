"""
Immutable Pydantic models returned by v3 scrapers.

Design rules:
    * All scraper-output models are Pydantic v2 with ``model_config =
      ConfigDict(frozen=True)``. Users cannot mutate them after the
      scraper returns.
    * Models are pure data: no methods that touch I/O, no log calls.
    * Models converge on ``Profile`` etc.; v3 does not duplicate
      "WebProfileData vs ProfileData" the way legacy did.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class _FrozenModel(BaseModel):
    """Internal base — frozen, ignore unknown fields by default."""

    model_config = ConfigDict(frozen=True, extra="ignore")


class BioLink(_FrozenModel):
    """One external link from a profile bio."""

    url: HttpUrl
    title: Optional[str] = None


class BusinessInfo(_FrozenModel):
    """Optional business-account metadata."""

    is_business: bool = False
    is_professional: bool = False
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class Profile(_FrozenModel):
    """Public-facing data for an Instagram profile.

    Returned by :meth:`instaharvest._v3.scrapers.ProfileScraper.scrape`.

    ``data_source`` distinguishes between values pulled from Instagram's
    JSON Web API (exact) and values scraped from the rendered DOM
    (approximate, e.g. ``"1.2M"``).
    """

    username: str = Field(min_length=1)
    user_id: Optional[str] = None
    full_name: Optional[str] = None

    posts: int = Field(ge=0)
    followers: int = Field(ge=0)
    following: int = Field(ge=0)

    is_verified: bool = False
    is_private: bool = False

    bio: Optional[str] = None
    bio_links: List[BioLink] = Field(default_factory=list)
    profile_pic_url: Optional[HttpUrl] = None
    category: Optional[str] = None

    business: Optional[BusinessInfo] = None

    data_source: str = Field(default="api", pattern="^(api|dom)$")
