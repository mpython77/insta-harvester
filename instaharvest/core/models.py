"""
Immutable Pydantic models returned by v3 scrapers.

Design rules:
    * All scraper-output models are Pydantic v2 with ``model_config =
      ConfigDict(frozen=True)``. Users cannot mutate them after the
      scraper returns.
    * Models are pure data: no methods that touch I/O, no log calls.
    * Models converge on ``Profile``, ``Media``, ``Comment``; v3 does
      not duplicate "WebProfileData vs ProfileData" the way legacy did.
    * Where Instagram exposes both an exact value (API) and a
      rendered string (DOM), we model the exact form and let scrapers
      parse the rendered form into it. ``data_source`` records which
      path the value came from.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


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

    Returned by :meth:`instaharvest.scrapers.ProfileScraper.scrape`.

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



# ---------------------------------------------------------------------------
# Media (posts, reels — Instagram models them with the same shape)
# ---------------------------------------------------------------------------


class MediaKind(str, Enum):
    """What kind of media this is.

    Instagram's internal API uses two fields to encode this:

      * ``media_type`` — int: ``1`` image, ``2`` video, ``8`` carousel.
      * ``product_type`` — str: ``"clips"`` for reels, ``"feed"`` for
        regular feed posts, ``"carousel_container"`` etc.

    v3 collapses the two into a single enum. ``REEL`` wins over
    ``VIDEO`` when both apply (i.e. a video with ``product_type=clips``
    is a reel).
    """

    IMAGE = "image"
    VIDEO = "video"
    REEL = "reel"
    CAROUSEL = "carousel"


class MediaOwner(_FrozenModel):
    """Author of a post/reel."""

    username: str = Field(min_length=1)
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    is_verified: bool = False
    profile_pic_url: Optional[HttpUrl] = None


class MediaLocation(_FrozenModel):
    """Tagged location."""

    name: str = Field(min_length=1)
    pk: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CarouselItem(_FrozenModel):
    """One slide of a multi-image/video carousel post."""

    index: int = Field(ge=0)
    kind: MediaKind
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    image_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    video_duration: Optional[float] = Field(default=None, ge=0)
    has_audio: bool = False
    accessibility_caption: Optional[str] = None
    tagged_usernames: Tuple[str, ...] = ()

    @field_validator("kind")
    @classmethod
    def _kind_must_be_atomic(cls, value: MediaKind) -> MediaKind:
        # A carousel slide is always a single image or video; it cannot
        # itself be a carousel or a reel.
        if value in (MediaKind.CAROUSEL, MediaKind.REEL):
            raise ValueError(
                f"CarouselItem.kind must be IMAGE or VIDEO, got {value}"
            )
        return value


class Media(_FrozenModel):
    """A post or a reel.

    Returned by :class:`instaharvest.scrapers.MediaScraper`.

    A few invariants:

      * ``shortcode`` and ``url`` always agree — the URL is derived
        from the shortcode by the scraper; users do not construct
        ``Media`` directly in normal use.
      * ``kind == CAROUSEL`` iff ``carousel`` is non-empty.
      * For non-carousel video/reel media, ``video_url`` is set.
    """

    shortcode: str = Field(min_length=1)
    url: HttpUrl
    kind: MediaKind

    owner: MediaOwner
    taken_at: datetime
    caption: Optional[str] = None

    like_count: int = Field(ge=0)
    comment_count: int = Field(ge=0)

    # Top-level media (None for carousels — see ``carousel`` instead)
    image_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    video_duration: Optional[float] = Field(default=None, ge=0)
    has_audio: bool = False
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    accessibility_caption: Optional[str] = None

    # Optional structured side-data
    location: Optional[MediaLocation] = None
    tagged_usernames: Tuple[str, ...] = ()
    carousel: Tuple[CarouselItem, ...] = ()

    data_source: str = Field(default="api", pattern="^(api|dom)$")

    # ----- invariants ----------------------------------------------------

    @field_validator("taken_at", mode="before")
    @classmethod
    def _coerce_taken_at(cls, value):
        # Instagram returns Unix epoch seconds; accept that and bare
        # datetimes interchangeably, normalise to UTC.
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @field_validator("carousel")
    @classmethod
    def _carousel_indices_unique_and_dense(
        cls,
        value: Tuple[CarouselItem, ...],
    ) -> Tuple[CarouselItem, ...]:
        if not value:
            return value
        indices = sorted(item.index for item in value)
        if indices != list(range(len(indices))):
            raise ValueError(
                "CarouselItem.index values must form 0..n-1 with no gaps "
                f"or duplicates, got {indices}"
            )
        return value


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class CommentAuthor(_FrozenModel):
    """Author of a comment or reply."""

    username: str = Field(min_length=1)
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    is_verified: bool = False
    profile_pic_url: Optional[HttpUrl] = None


class Comment(_FrozenModel):
    """A single comment.

    Replies are themselves ``Comment`` objects nested under
    :attr:`replies`. Top-level comments have :attr:`parent_id` set to
    ``None``; replies set it to the id of their parent comment.

    The replies tree is at most one level deep — Instagram only
    supports comment → reply, not reply → reply — but the model itself
    permits arbitrary nesting so future product changes do not require
    a model change.
    """

    id: str = Field(min_length=1)
    text: str
    author: CommentAuthor
    created_at: datetime
    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    parent_id: Optional[str] = None
    replies: Tuple["Comment", ...] = ()

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_created_at(cls, value):
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# Allow the recursive ``replies: Tuple[Comment, ...]`` self-reference.
Comment.model_rebuild()


class CommentsPage(_FrozenModel):
    """Result of one comment-scrape call.

    Pagination is fully-resolved by ``CommentScraper.scrape`` — by the
    time you see this object, ``comments`` already contains every
    comment requested (up to ``max_comments``). ``has_more`` indicates
    whether Instagram had additional comments beyond the cap.
    """

    media_shortcode: str = Field(min_length=1)
    comments: Tuple[Comment, ...] = ()
    total_returned: int = Field(ge=0)
    has_more: bool = False
    next_cursor: Optional[str] = None

    @field_validator("total_returned")
    @classmethod
    def _total_matches_len(cls, value: int, info) -> int:
        comments = info.data.get("comments")
        if comments is not None and value != len(comments):
            raise ValueError(
                f"total_returned={value} disagrees with len(comments)={len(comments)}"
            )
        return value



# ---------------------------------------------------------------------------
# Followers / Following (read-only)
# ---------------------------------------------------------------------------


class FollowEntry(_FrozenModel):
    """One user in a followers / following list.

    A trimmed-down :class:`MediaOwner`-shaped record. We keep it
    separate so that follower lists do not have to invent values for
    media-only fields (and so the type system distinguishes "user
    inside a follower list" from "user who owns a media item").
    """

    username: str = Field(min_length=1)
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    is_verified: bool = False
    is_private: bool = False
    profile_pic_url: Optional[HttpUrl] = None


class FollowList(_FrozenModel):
    """One page of followers or following.

    Pagination is fully resolved by :class:`FollowersScraper` before
    this object is returned: ``users`` already contains every user
    requested (up to ``max_users``). ``has_more`` indicates whether
    Instagram had additional users beyond the cap.

    ``kind`` distinguishes a followers list from a following list so
    the same model can serve both, with type-system protection
    against accidental confusion.
    """

    target_user_id: str = Field(min_length=1)
    kind: str = Field(pattern="^(followers|following)$")
    users: Tuple[FollowEntry, ...] = ()
    total_returned: int = Field(ge=0)
    has_more: bool = False
    next_cursor: Optional[str] = None

    @field_validator("total_returned")
    @classmethod
    def _total_matches_len(cls, value: int, info) -> int:
        users = info.data.get("users")
        if users is not None and value != len(users):
            raise ValueError(
                f"total_returned={value} disagrees with len(users)={len(users)}"
            )
        return value


class FriendshipStatus(_FrozenModel):
    """The viewer's relationship with another user.

    "Viewer" is the account whose session we hold. All booleans are
    from that perspective: ``is_following`` means the viewer follows
    ``user_id``, not vice versa.
    """

    user_id: str = Field(min_length=1)
    is_following: bool = False
    is_followed_by: bool = False
    is_blocking: bool = False
    is_muting: bool = False
    has_outgoing_request: bool = False
    has_incoming_request: bool = False


# ---------------------------------------------------------------------------
# Actions (write operations — see _v3.actions)
# ---------------------------------------------------------------------------


class ActionStatus(str, Enum):
    """Outcome of one mutation attempt."""

    OK = "ok"
    ALREADY_DONE = "already_done"     # follow → already following, etc.
    NOT_APPLICABLE = "not_applicable" # unfollow → was not following
    DRY_RUN = "dry_run"               # actions disabled or dry-run on
    ERROR = "error"


class ActionResult(_FrozenModel):
    """Structured outcome of a single mutation.

    Returned by every method on the :mod:`instaharvest.actions`
    namespace. Callers should inspect :attr:`status` rather than
    relying on truthiness; an :attr:`ActionStatus.ALREADY_DONE` is
    semantically a success, but ``status != ActionStatus.OK``.
    """

    action: str = Field(min_length=1)        # e.g. "follow", "send_message"
    target: str = Field(min_length=1)         # username or user_id we acted on
    status: ActionStatus
    message: str = ""
    extra: Optional[dict] = None              # provider/api response details

    @property
    def succeeded(self) -> bool:
        """True for OK, ALREADY_DONE, NOT_APPLICABLE, and DRY_RUN.

        ``ERROR`` is the only failing status — everything else means
        Instagram is in the state the caller wanted, even if we did
        not have to do anything to get there.
        """
        return self.status != ActionStatus.ERROR



# ---------------------------------------------------------------------------
# Discovery (hashtag, location, search, explore)
# ---------------------------------------------------------------------------


class Hashtag(_FrozenModel):
    """Metadata for an Instagram hashtag (``#fashionweek``).

    Returned by :meth:`HashtagScraper.lookup`. Does not include the
    media feed — request that separately via
    :meth:`HashtagScraper.recent` / :meth:`HashtagScraper.top`.
    """

    name: str = Field(min_length=1)
    media_count: int = Field(default=0, ge=0)
    formatted_media_count: Optional[str] = None  # e.g. "1.2M"
    profile_pic_url: Optional[HttpUrl] = None
    is_top_media_only: bool = False
    allow_following: bool = True
    is_following: bool = False


class Location(_FrozenModel):
    """Metadata for a tagged Instagram location.

    Returned by :meth:`LocationScraper.lookup`. Like :class:`Hashtag`,
    media feeds are fetched separately.
    """

    pk: str = Field(min_length=1)
    name: str = Field(min_length=1)
    slug: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    short_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    media_count: int = Field(default=0, ge=0)


class FeedSource(str, Enum):
    """Where a :class:`MediaFeed` came from.

    ``MediaFeed`` is reused across hashtag, location, and explore so
    callers know in one type-checked field which API populated it.
    """

    HASHTAG_TOP = "hashtag_top"
    HASHTAG_RECENT = "hashtag_recent"
    LOCATION_RECENT = "location_recent"
    LOCATION_RANKED = "location_ranked"
    EXPLORE = "explore"


class MediaFeed(_FrozenModel):
    """A paginated list of :class:`Media`.

    Used by hashtag/location/explore scrapers. ``source_id`` is the
    tag name, location pk, or the literal ``"explore"`` depending on
    :attr:`source`.
    """

    source: FeedSource
    source_id: str = Field(min_length=1)
    media: Tuple[Media, ...] = ()
    total_returned: int = Field(ge=0)
    has_more: bool = False
    next_cursor: Optional[str] = None

    @field_validator("total_returned")
    @classmethod
    def _total_matches_len(cls, value: int, info) -> int:
        media = info.data.get("media")
        if media is not None and value != len(media):
            raise ValueError(
                f"total_returned={value} disagrees with len(media)={len(media)}"
            )
        return value


# Search ----------------------------------------------------------------


class SearchUserHit(_FrozenModel):
    """A user appearing in :class:`SearchResult.users`."""

    username: str = Field(min_length=1)
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    is_verified: bool = False
    is_private: bool = False
    profile_pic_url: Optional[HttpUrl] = None
    follower_count: int = Field(default=0, ge=0)


class SearchHashtagHit(_FrozenModel):
    """A hashtag appearing in :class:`SearchResult.hashtags`."""

    name: str = Field(min_length=1)
    media_count: int = Field(default=0, ge=0)
    formatted_media_count: Optional[str] = None


class SearchPlaceHit(_FrozenModel):
    """A place / location appearing in :class:`SearchResult.places`."""

    pk: str = Field(min_length=1)
    name: str = Field(min_length=1)
    short_name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class SearchResult(_FrozenModel):
    """Aggregated topsearch result.

    Mirrors Instagram's ``topsearch_flat`` response: three buckets of
    typed hits keyed by category, plus the original query text for
    diagnostics.
    """

    query: str = Field(min_length=1)
    users: Tuple[SearchUserHit, ...] = ()
    hashtags: Tuple[SearchHashtagHit, ...] = ()
    places: Tuple[SearchPlaceHit, ...] = ()


# ---------------------------------------------------------------------------
# Stories
# ---------------------------------------------------------------------------


class StorySlide(_FrozenModel):
    """One slide of an active Instagram story."""

    id: str = Field(min_length=1)
    user_id: str
    username: str = Field(min_length=1)
    taken_at: datetime
    expiring_at: datetime
    media_type: str = Field(pattern="^(image|video)$")
    image_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    video_duration: Optional[float] = Field(default=None, ge=0)
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    has_audio: bool = False
    mentions: Tuple[str, ...] = ()
    link_stickers: Tuple[str, ...] = ()
    is_reel_mention: bool = False

    @field_validator("taken_at", "expiring_at", mode="before")
    @classmethod
    def _coerce_timestamps(cls, value):
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class StoryFeed(_FrozenModel):
    """All active story slides for a user."""

    user_id: str = Field(min_length=1)
    username: str = Field(min_length=1)
    slides: Tuple[StorySlide, ...] = ()
    total_returned: int = Field(ge=0)
    has_expired: bool = False

    @field_validator("total_returned")
    @classmethod
    def _total_matches_len(cls, value: int, info) -> int:
        slides = info.data.get("slides")
        if slides is not None and value != len(slides):
            raise ValueError(
                f"total_returned={value} disagrees with len(slides)={len(slides)}"
            )
        return value


# ---------------------------------------------------------------------------
# Highlights
# ---------------------------------------------------------------------------


class Highlight(_FrozenModel):
    """Metadata for a single highlight reel."""

    pk: str = Field(min_length=1)
    title: str = Field(min_length=1)
    cover_url: Optional[HttpUrl] = None
    created_at: Optional[datetime] = None
    media_count: int = Field(default=0, ge=0)

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_created_at(cls, value):
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class HighlightSlide(_FrozenModel):
    """One slide within a highlight reel."""

    id: str = Field(min_length=1)
    user_id: str
    username: str = Field(min_length=1)
    taken_at: datetime
    expiring_at: datetime
    media_type: str = Field(pattern="^(image|video)$")
    image_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    video_duration: Optional[float] = Field(default=None, ge=0)
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    has_audio: bool = False
    mentions: Tuple[str, ...] = ()
    link_stickers: Tuple[str, ...] = ()
    is_reel_mention: bool = False
    highlight_pk: str = Field(min_length=1)

    @field_validator("taken_at", "expiring_at", mode="before")
    @classmethod
    def _coerce_timestamps(cls, value):
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class HighlightsList(_FrozenModel):
    """All highlights for a user."""

    user_id: str = Field(min_length=1)
    highlights: Tuple[Highlight, ...] = ()
    total_returned: int = Field(ge=0)

    @field_validator("total_returned")
    @classmethod
    def _total_matches_len(cls, value: int, info) -> int:
        highlights = info.data.get("highlights")
        if highlights is not None and value != len(highlights):
            raise ValueError(
                f"total_returned={value} disagrees with len(highlights)={len(highlights)}"
            )
        return value


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationType(str, Enum):
    """Category of an Instagram notification."""

    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    MENTION = "mention"
    COMMENT_LIKE = "comment_like"
    FOLLOW_REQUEST = "follow_request"
    OTHER = "other"


class Notification(_FrozenModel):
    """A single notification entry."""

    id: str = Field(min_length=1)
    notification_type: NotificationType
    text: str
    timestamp: datetime
    usernames: Tuple[str, ...] = ()
    profile_pic_url: Optional[HttpUrl] = None
    media_shortcode: Optional[str] = None
    is_grouped: bool = False
    group_count: int = Field(default=0, ge=0)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _coerce_timestamp(cls, value):
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class NotificationFeed(_FrozenModel):
    """Paginated notification feed."""

    notifications: Tuple[Notification, ...] = ()
    total_returned: int = Field(ge=0)
    has_more: bool = False
    next_cursor: Optional[str] = None

    @field_validator("total_returned")
    @classmethod
    def _total_matches_len(cls, value: int, info) -> int:
        notifications = info.data.get("notifications")
        if notifications is not None and value != len(notifications):
            raise ValueError(
                f"total_returned={value} disagrees with len(notifications)={len(notifications)}"
            )
        return value
