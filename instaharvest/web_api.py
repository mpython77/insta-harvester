"""
Instagram Web API Client — Full JSON data extraction via Playwright

Uses page.evaluate(fetch()) to call Instagram's internal API endpoints
from within an authenticated browser context.

Supported Endpoints (16+):
    - Profile: web_profile_info, users/{id}/info
    - Social: followers, following, friendship status
    - Feed: user feed, media info, comments, likers
    - Content: stories, highlights, reels
    - Discovery: search, hashtags, locations, tagged posts
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

from .config import ScraperConfig
from .logging_config import get_logger
from .exceptions import WebAPIError


# ═══════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════

@dataclass
class WebProfileData:
    """Complete profile data from Instagram Web API."""
    username: str = ''
    full_name: str = ''
    user_id: str = ''
    fbid: str = ''
    biography: str = ''
    follower_count: int = 0
    following_count: int = 0
    media_count: int = 0
    is_verified: bool = False
    is_private: bool = False
    is_business_account: bool = False
    is_professional_account: bool = False
    category_name: Optional[str] = None
    category_enum: Optional[str] = None
    external_url: Optional[str] = None
    bio_links: List[Dict[str, str]] = field(default_factory=list)
    profile_pic_url: str = ''
    profile_pic_url_hd: str = ''
    business_address: Optional[Dict[str, Any]] = None
    business_email: Optional[str] = None
    business_phone: Optional[str] = None
    business_category_name: Optional[str] = None
    highlight_reel_count: int = 0
    has_clips: bool = False
    has_guides: bool = False
    has_channel: bool = False
    is_joined_recently: bool = False
    pronouns: List[str] = field(default_factory=list)
    mutual_followers_count: int = 0
    followed_by_viewer: bool = False
    follows_viewer: bool = False
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self); d.pop('_raw', None); return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @property
    def is_business(self) -> bool:
        return self.is_business_account or self.is_professional_account

    @property
    def website(self) -> Optional[str]:
        return self.external_url

    @property
    def has_business_contact(self) -> bool:
        return bool(self.business_email or self.business_phone)


@dataclass
class SearchUserResult:
    """Single user from search results."""
    username: str = ''
    full_name: str = ''
    user_id: str = ''
    is_verified: bool = False
    is_private: bool = False
    profile_pic_url: str = ''
    follower_count: int = 0
    mutual_followers_count: int = 0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class WebSearchResult:
    """Search results container."""
    query: str = ''
    users: List[SearchUserResult] = field(default_factory=list)
    total_found: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'query': self.query, 'users': [u.to_dict() for u in self.users], 'total_found': self.total_found}


@dataclass
class FollowUserItem:
    """Single user in followers/following list."""
    username: str = ''
    full_name: str = ''
    user_id: str = ''
    is_verified: bool = False
    is_private: bool = False
    profile_pic_url: str = ''
    has_anonymous_profile_picture: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class FollowListResult:
    """Paginated followers/following result."""
    users: List[FollowUserItem] = field(default_factory=list)
    next_max_id: Optional[str] = None
    has_more: bool = False
    total_count: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'users': [u.to_dict() for u in self.users], 'next_max_id': self.next_max_id, 'has_more': self.has_more, 'total_count': self.total_count}


@dataclass
class FriendshipStatus:
    """Friendship status between viewer and target user."""
    following: bool = False
    followed_by: bool = False
    blocking: bool = False
    muting: bool = False
    is_private: bool = False
    incoming_request: bool = False
    outgoing_request: bool = False
    is_restricted: bool = False
    is_feed_favorite: bool = False
    user_id: str = ''
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class FeedPost:
    """Single post from user feed."""
    media_id: str = ''
    shortcode: str = ''
    media_type: int = 0  # 1=photo, 2=video, 8=carousel
    caption: str = ''
    like_count: int = 0
    comment_count: int = 0
    view_count: int = 0
    timestamp: int = 0
    image_url: str = ''
    video_url: Optional[str] = None
    is_video: bool = False
    location: Optional[Dict[str, Any]] = None
    usertags: List[str] = field(default_factory=list)
    carousel_media: List[Dict[str, Any]] = field(default_factory=list)
    is_paid_partnership: bool = False
    is_pinned: bool = False
    owner_username: str = ''
    owner_id: str = ''
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class UserFeedResult:
    """Paginated user feed result."""
    posts: List[FeedPost] = field(default_factory=list)
    next_max_id: Optional[str] = None
    has_more: bool = False
    total_count: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'posts': [p.to_dict() for p in self.posts], 'next_max_id': self.next_max_id, 'has_more': self.has_more, 'total_count': self.total_count}


@dataclass
class MediaInfo:
    """Detailed media/post information."""
    media_id: str = ''
    shortcode: str = ''
    media_type: int = 0
    caption: str = ''
    like_count: int = 0
    comment_count: int = 0
    view_count: int = 0
    play_count: int = 0
    timestamp: int = 0
    image_versions: List[Dict[str, Any]] = field(default_factory=list)
    video_versions: List[Dict[str, Any]] = field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    usertags: List[str] = field(default_factory=list)
    is_paid_partnership: bool = False
    owner_username: str = ''
    owner_id: str = ''
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self); d.pop('_raw', None); return d


@dataclass
class CommentItem:
    """Single comment on a post."""
    comment_id: str = ''
    text: str = ''
    username: str = ''
    user_id: str = ''
    timestamp: int = 0
    like_count: int = 0
    reply_count: int = 0
    is_verified: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class CommentsResult:
    """Paginated comments result."""
    comments: List[CommentItem] = field(default_factory=list)
    next_min_id: Optional[str] = None
    has_more: bool = False
    total_count: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'comments': [c.to_dict() for c in self.comments], 'next_min_id': self.next_min_id, 'has_more': self.has_more, 'total_count': self.total_count}


@dataclass
class LikerItem:
    """Single user who liked a post."""
    username: str = ''
    full_name: str = ''
    user_id: str = ''
    is_verified: bool = False
    profile_pic_url: str = ''
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class LikersResult:
    """Post likers result."""
    likers: List[LikerItem] = field(default_factory=list)
    total_count: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'likers': [l.to_dict() for l in self.likers], 'total_count': self.total_count}


@dataclass
class StoryMediaItem:
    """Single story media item."""
    story_id: str = ''
    media_type: int = 0
    image_url: str = ''
    video_url: Optional[str] = None
    timestamp: int = 0
    expiring_at: int = 0
    has_audio: bool = False
    owner_username: str = ''
    owner_id: str = ''
    # Story tag/mention ma'lumotlari
    reel_mentions: List[str] = field(default_factory=list)  # @mention qilingan userlar
    story_hashtags: List[str] = field(default_factory=list)  # #hashtag lar
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class StoriesTrayResult:
    """Stories tray result (all visible stories)."""
    stories: List[Dict[str, Any]] = field(default_factory=list)
    total_users: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'stories': self.stories, 'total_users': self.total_users}


@dataclass
class HighlightInfo:
    """Single highlight reel info."""
    highlight_id: str = ''
    title: str = ''
    cover_url: str = ''
    media_count: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class HighlightsResult:
    """User highlights result."""
    highlights: List[HighlightInfo] = field(default_factory=list)
    total_count: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {'highlights': [h.to_dict() for h in self.highlights], 'total_count': self.total_count}


@dataclass
class ReelItem:
    """Single reel/clip."""
    media_id: str = ''
    shortcode: str = ''
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    video_url: str = ''
    thumbnail_url: str = ''
    caption: str = ''
    timestamp: int = 0
    owner_username: str = ''
    owner_id: str = ''
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class ReelsResult:
    """Reels result."""
    reels: List[ReelItem] = field(default_factory=list)
    paging_token: Optional[str] = None
    has_more: bool = False
    def to_dict(self) -> Dict[str, Any]:
        return {'reels': [r.to_dict() for r in self.reels], 'paging_token': self.paging_token, 'has_more': self.has_more}


@dataclass
class HashtagSection:
    """Hashtag feed result."""
    tag_name: str = ''
    media_count: int = 0
    posts: List[Dict[str, Any]] = field(default_factory=list)
    next_max_id: Optional[str] = None
    has_more: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


@dataclass
class LocationSection:
    """Location feed result."""
    location_name: str = ''
    location_id: str = ''
    posts: List[Dict[str, Any]] = field(default_factory=list)
    next_max_id: Optional[str] = None
    has_more: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


# ═══════════════════════════════════════════════════════════════
# CORE API CLIENT
# ═══════════════════════════════════════════════════════════════

class InstagramWebAPI:
    """
    Instagram Web API client — Full JSON data extraction via Playwright.

    16+ endpoints for profiles, followers, posts, comments, stories, etc.
    Uses page.evaluate(fetch()) from authenticated browser session.

    Example:
        >>> api = InstagramWebAPI(page=playwright_page)
        >>> profile = api.get_profile('mondayswimwear')
        >>> followers = api.get_followers(profile.user_id, count=50)
        >>> feed = api.get_user_feed(profile.user_id, count=12)
    """

    IG_APP_ID = '936619743392459'
    BASE_API = 'https://www.instagram.com/api/v1'

    def __init__(self, page=None, config: Optional[ScraperConfig] = None, logger: Optional[logging.Logger] = None):
        self.page = page
        self.config = config or ScraperConfig()
        self.logger = logger or get_logger('WebAPI')
        self._request_count = 0
        self._last_request_time = 0.0

    # ══════════════════════════════════════════════════════════
    # PROFILE ENDPOINTS
    # ══════════════════════════════════════════════════════════

    def get_profile(self, username: str) -> Optional[WebProfileData]:
        """Get complete profile data via web_profile_info API."""
        username = username.strip().lstrip('@')
        self.logger.info(f"🔍 WebAPI: Fetching profile for @{username}")
        data = self._fetch_api(f'{self.BASE_API}/users/web_profile_info/', {'username': username})
        if not data: return None
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            self.logger.warning(f"⚠️ No user data for @{username}")
            return None
        return self._parse_profile(user)

    def get_user_info(self, user_id: str) -> Optional[WebProfileData]:
        """Get profile data by user ID."""
        self.logger.info(f"🔍 WebAPI: User info ID={user_id}")
        data = self._fetch_api(f'{self.BASE_API}/users/{user_id}/info/')
        if not data: return None
        user = data.get('user')
        return self._parse_profile(user) if user else None

    # ══════════════════════════════════════════════════════════
    # SOCIAL ENDPOINTS (Followers/Following/Friendship)
    # ══════════════════════════════════════════════════════════

    def get_followers(self, user_id: str, count: int = 50, max_id: Optional[str] = None) -> FollowListResult:
        """Get followers list (paginated)."""
        self.logger.info(f"👥 WebAPI: Followers for ID={user_id} (count={count})")
        params = {'count': str(count), 'search_surface': 'follow_list_page'}
        if max_id: params['max_id'] = max_id
        data = self._fetch_api(f'{self.BASE_API}/friendships/{user_id}/followers/', params)
        if not data: return FollowListResult()
        return self._parse_follow_list(data)

    def get_following(self, user_id: str, count: int = 50, max_id: Optional[str] = None) -> FollowListResult:
        """Get following list (paginated)."""
        self.logger.info(f"👥 WebAPI: Following for ID={user_id} (count={count})")
        params = {'count': str(count)}
        if max_id: params['max_id'] = max_id
        data = self._fetch_api(f'{self.BASE_API}/friendships/{user_id}/following/', params)
        if not data: return FollowListResult()
        return self._parse_follow_list(data)

    def get_all_followers(self, user_id: str, max_pages: int = 10) -> List[FollowUserItem]:
        """Get all followers with auto-pagination."""
        all_users = []
        max_id = None
        for page in range(max_pages):
            result = self.get_followers(user_id, count=100, max_id=max_id)
            all_users.extend(result.users)
            self.logger.info(f"📄 Page {page+1}: +{len(result.users)} (total: {len(all_users)})")
            if not result.has_more: break
            max_id = result.next_max_id
            time.sleep(1.5)
        return all_users

    def get_all_following(self, user_id: str, max_pages: int = 10) -> List[FollowUserItem]:
        """Get all following with auto-pagination."""
        all_users = []
        max_id = None
        for page in range(max_pages):
            result = self.get_following(user_id, count=100, max_id=max_id)
            all_users.extend(result.users)
            self.logger.info(f"📄 Page {page+1}: +{len(result.users)} (total: {len(all_users)})")
            if not result.has_more: break
            max_id = result.next_max_id
            time.sleep(1.5)
        return all_users

    def get_friendship_status(self, user_id: str) -> FriendshipStatus:
        """Check friendship status with a user."""
        self.logger.info(f"🤝 WebAPI: Friendship status ID={user_id}")
        data = self._fetch_api(f'{self.BASE_API}/friendships/show/{user_id}/')
        if not data: return FriendshipStatus(user_id=user_id)
        return self._parse_friendship(data, user_id)

    # ══════════════════════════════════════════════════════════
    # FEED/POST ENDPOINTS
    # ══════════════════════════════════════════════════════════

    def get_user_feed(self, user_id: str, count: int = 12, max_id: Optional[str] = None) -> UserFeedResult:
        """Get user's posts feed (paginated)."""
        self.logger.info(f"📸 WebAPI: Feed for ID={user_id} (count={count})")
        params = {'count': str(count)}
        if max_id: params['max_id'] = max_id
        data = self._fetch_api(f'{self.BASE_API}/feed/user/{user_id}/', params)
        if not data: return UserFeedResult()
        return self._parse_user_feed(data)

    def get_media_info(self, media_id: str) -> Optional[MediaInfo]:
        """Get detailed info about a specific post/media."""
        self.logger.info(f"📋 WebAPI: Media info ID={media_id}")
        data = self._fetch_api(f'{self.BASE_API}/media/{media_id}/info/')
        if not data: return None
        items = data.get('items', [])
        return self._parse_media_info(items[0]) if items else None

    def get_media_comments(self, media_id: str, count: int = 20, min_id: Optional[str] = None) -> CommentsResult:
        """Get comments on a post (paginated)."""
        self.logger.info(f"💬 WebAPI: Comments for media={media_id}")
        params = {'can_support_threading': 'true', 'permalink_enabled': 'false'}
        if min_id: params['min_id'] = min_id
        data = self._fetch_api(f'{self.BASE_API}/media/{media_id}/comments/', params)
        if not data: return CommentsResult()
        return self._parse_comments(data)

    def get_media_likers(self, media_id: str) -> LikersResult:
        """Get users who liked a post."""
        self.logger.info(f"❤️ WebAPI: Likers for media={media_id}")
        data = self._fetch_api(f'{self.BASE_API}/media/{media_id}/likers/')
        if not data: return LikersResult()
        return self._parse_likers(data)

    # ══════════════════════════════════════════════════════════
    # STORIES & HIGHLIGHTS ENDPOINTS
    # ══════════════════════════════════════════════════════════

    def get_stories(self, user_id: str) -> List[StoryMediaItem]:
        """Get user's active stories."""
        self.logger.info(f"📖 WebAPI: Stories for ID={user_id}")
        data = self._fetch_api(f'{self.BASE_API}/feed/user/{user_id}/story/')
        if not data: return []
        reel = data.get('reel')
        if not reel: return []
        return self._parse_story_items(reel.get('items', []), reel.get('user', {}))

    def get_stories_tray(self) -> StoriesTrayResult:
        """Get stories tray (all visible stories from followed users)."""
        self.logger.info("📖 WebAPI: Stories tray")
        data = self._fetch_api(f'{self.BASE_API}/feed/reels_tray/')
        if not data: return StoriesTrayResult()
        tray = data.get('tray', [])
        stories = []
        for item in tray:
            user = item.get('user', {})
            stories.append({
                'user_id': str(user.get('pk', '')),
                'username': user.get('username', ''),
                'has_items': bool(item.get('items')),
                'reel_count': len(item.get('items', [])),
                'latest_reel_media': item.get('latest_reel_media', 0),
            })
        return StoriesTrayResult(stories=stories, total_users=len(stories))

    def get_highlights(self, user_id: str) -> HighlightsResult:
        """Get user's highlight reels."""
        self.logger.info(f"✨ WebAPI: Highlights for ID={user_id}")
        data = self._fetch_api(f'{self.BASE_API}/highlights/{user_id}/highlights_tray/')
        if not data: return HighlightsResult()
        return self._parse_highlights(data)

    # ══════════════════════════════════════════════════════════
    # REELS ENDPOINTS
    # ══════════════════════════════════════════════════════════

    def get_reels(self, user_id: str, max_id: Optional[str] = None) -> ReelsResult:
        """Get user's reels/clips (POST endpoint)."""
        self.logger.info(f"🎬 WebAPI: Reels for ID={user_id}")
        body = {'target_user_id': user_id, 'page_size': 12, 'include_feed_video': True}
        if max_id: body['max_id'] = max_id
        data = self._post_api(f'{self.BASE_API}/clips/user/', body)
        if not data: return ReelsResult()
        return self._parse_reels(data)

    # ══════════════════════════════════════════════════════════
    # DISCOVERY ENDPOINTS (Search/Hashtag/Location)
    # ══════════════════════════════════════════════════════════

    def search(self, query: str, limit: int = 20) -> WebSearchResult:
        """Search for users, hashtags, and places."""
        query = query.strip()
        self.logger.info(f"🔎 WebAPI: Searching '{query}'")
        # Strategy 1: topsearch_flat (most common in modern Instagram web)
        data = self._fetch_api(
            'https://www.instagram.com/api/v1/fbsearch/topsearch_flat/',
            {'query': query, 'context': 'blended', 'search_surface': 'web_top_search'}
        )
        if data and (data.get('users') or data.get('list')):
            return self._parse_search_results(query, data, limit)
        # Strategy 2: web search tray
        data = self._fetch_api(
            f'{self.BASE_API}/web/search/tray/',
            {'query': query, 'context': 'blended', 'include_reel': 'false'}
        )
        if data and data.get('users'):
            return self._parse_search_results(query, data, limit)
        # Strategy 3: legacy tray
        data = self._fetch_api(
            f'{self.BASE_API}/web/search_tray/',
            {'query': query, 'context': 'blended', 'include_reel': 'false'}
        )
        if not data: return WebSearchResult(query=query)
        return self._parse_search_results(query, data, limit)

    def get_hashtag_feed(self, tag: str, max_id: Optional[str] = None) -> HashtagSection:
        """Get posts from a hashtag (POST endpoint)."""
        tag = tag.strip().lstrip('#')
        self.logger.info(f"#️⃣ WebAPI: Hashtag #{tag}")
        body = {'tab': 'recent', 'surface': 'grid', 'include_persistent': 'false'}
        if max_id: body['max_id'] = max_id
        data = self._post_api(f'{self.BASE_API}/tags/{tag}/sections/', body)
        if not data:
            # Fallback: try as GET
            params = {'tab': 'recent'}
            if max_id: params['max_id'] = max_id
            data = self._fetch_api(f'{self.BASE_API}/tags/{tag}/sections/', params)
        if not data: return HashtagSection(tag_name=tag)
        return self._parse_hashtag(tag, data)

    def get_location_feed(self, location_id: str, max_id: Optional[str] = None) -> LocationSection:
        """Get posts from a location (POST endpoint)."""
        self.logger.info(f"📍 WebAPI: Location ID={location_id}")
        body = {'tab': 'recent', 'surface': 'grid'}
        if max_id: body['max_id'] = max_id
        data = self._post_api(f'{self.BASE_API}/locations/{location_id}/sections/', body)
        if not data:
            params = {'tab': 'recent'}
            if max_id: params['max_id'] = max_id
            data = self._fetch_api(f'{self.BASE_API}/locations/{location_id}/sections/', params)
        if not data: return LocationSection(location_id=location_id)
        return self._parse_location(location_id, data)

    def get_tagged_posts(self, user_id: str, max_id: Optional[str] = None) -> UserFeedResult:
        """Get posts where user is tagged."""
        self.logger.info(f"🏷️ WebAPI: Tagged posts for ID={user_id}")
        params = {} if not max_id else {'max_id': max_id}
        data = self._fetch_api(f'{self.BASE_API}/usertags/{user_id}/feed/', params)
        if not data: return UserFeedResult()
        return self._parse_user_feed(data)

    # ══════════════════════════════════════════════════════════
    # RAW ACCESS
    # ══════════════════════════════════════════════════════════

    def fetch_raw(self, endpoint: str, params: Optional[Dict] = None, method: str = 'GET', body: Optional[Dict] = None) -> Optional[Dict]:
        """Make a raw API call to any Instagram endpoint (GET or POST)."""
        if not endpoint.startswith('http'):
            endpoint = f'https://www.instagram.com{endpoint}'
        if method.upper() == 'POST' and body:
            return self._post_api(endpoint, body)
        return self._fetch_api(endpoint, params)

    # ══════════════════════════════════════════════════════════
    # INTERNAL: Core Fetch
    # ══════════════════════════════════════════════════════════

    def _fetch_api(self, url: str, params: Optional[Dict] = None, max_retries: int = 2) -> Optional[Dict]:
        """Core fetch — executes API call via page.evaluate(fetch())."""
        if not self.page:
            self.logger.error("❌ WebAPI: No page — browser not started")
            return None
        if params:
            query_string = '&'.join(f'{k}={v}' for k, v in params.items())
            full_url = f'{url}?{query_string}'
        else:
            full_url = url
        self._apply_rate_limit()
        fetch_js = self._build_fetch_js(full_url)
        for attempt in range(max_retries + 1):
            try:
                result = self.page.evaluate(fetch_js)
                self._request_count += 1
                self._last_request_time = time.time()
                if isinstance(result, dict):
                    if 'error' in result:
                        status = result.get('status', 'unknown')
                        if status == 429:
                            wait_time = min(60, 10 * (attempt + 1))
                            self.logger.warning(f"⚠️ Rate limited (429). Waiting {wait_time}s...")
                            time.sleep(wait_time); continue
                        if status in (401, 403):
                            self.logger.error(f"❌ Auth error ({status})")
                            return None
                        if attempt < max_retries:
                            time.sleep(2 * (attempt + 1)); continue
                        return None
                    return result
                return None
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                else:
                    self.logger.error(f"❌ WebAPI failed: {e}")
                    return None
        return None

    def _build_fetch_js(self, url: str) -> str:
        safe_url = url.replace("'", "\\'").replace("\\", "\\\\")
        return f'''async () => {{
            try {{
                const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
                const resp = await fetch('{safe_url}', {{
                    credentials: 'include',
                    headers: {{
                        'X-CSRFToken': csrfToken,
                        'X-IG-App-ID': '{self.IG_APP_ID}',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-ASBD-ID': '129477',
                        'Accept': '*/*'
                    }}
                }});
                if (!resp.ok) {{ return {{ error: resp.statusText, status: resp.status }}; }}
                return await resp.json();
            }} catch(e) {{ return {{ error: e.message, status: 0 }}; }}
        }}'''

    def _post_api(self, url: str, body: Optional[Dict] = None, max_retries: int = 2) -> Optional[Dict]:
        """POST fetch — for endpoints that require POST (reels, hashtags, locations)."""
        if not self.page:
            self.logger.error("❌ WebAPI: No page — browser not started")
            return None
        self._apply_rate_limit()
        fetch_js = self._build_post_js(url, body or {})
        for attempt in range(max_retries + 1):
            try:
                result = self.page.evaluate(fetch_js)
                self._request_count += 1
                self._last_request_time = time.time()
                if isinstance(result, dict):
                    if 'error' in result:
                        status = result.get('status', 'unknown')
                        if status == 429:
                            wait_time = min(60, 10 * (attempt + 1))
                            self.logger.warning(f"⚠️ Rate limited (429). Waiting {wait_time}s...")
                            time.sleep(wait_time); continue
                        if status in (401, 403): return None
                        if attempt < max_retries:
                            time.sleep(2 * (attempt + 1)); continue
                        return None
                    return result
                return None
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                else:
                    self.logger.error(f"❌ WebAPI POST failed: {e}")
                    return None
        return None

    def _build_post_js(self, url: str, body: Dict) -> str:
        """Build JavaScript POST fetch() code with form-urlencoded body."""
        safe_url = url.replace("'", "\\'").replace("\\", "\\\\")
        # Build URL-encoded form body
        form_parts = []
        for k, v in body.items():
            val = str(v).lower() if isinstance(v, bool) else str(v)
            form_parts.append(f'{k}={val}')
        form_body = '&'.join(form_parts)
        safe_body = form_body.replace("'", "\\'")
        return f'''async () => {{
            try {{
                const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
                const resp = await fetch('{safe_url}', {{
                    method: 'POST',
                    credentials: 'include',
                    headers: {{
                        'X-CSRFToken': csrfToken,
                        'X-IG-App-ID': '{self.IG_APP_ID}',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-ASBD-ID': '129477',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': '*/*'
                    }},
                    body: '{safe_body}'
                }});
                if (!resp.ok) {{ return {{ error: resp.statusText, status: resp.status }}; }}
                return await resp.json();
            }} catch(e) {{ return {{ error: e.message, status: 0 }}; }}
        }}'''

    def _apply_rate_limit(self):
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            min_interval = getattr(self.config, 'web_api_min_interval', 1.0)
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

    # ══════════════════════════════════════════════════════════
    # INTERNAL: Parsers
    # ══════════════════════════════════════════════════════════

    def _parse_profile(self, user: Dict[str, Any]) -> WebProfileData:
        business_address = None
        addr_json = user.get('business_address_json')
        if addr_json and isinstance(addr_json, str) and addr_json != 'null':
            try: business_address = json.loads(addr_json)
            except: pass
        bio_links = []
        for link in (user.get('bio_links') or []):
            if isinstance(link, dict):
                bio_links.append({'title': link.get('title', ''), 'url': link.get('url', ''), 'link_type': link.get('link_type', 'external')})
        biography = (user.get('biography', '') or '').replace('\\n', '\n').replace('\\"', '"')
        fc = user.get('edge_followed_by', {}).get('count') or user.get('follower_count') or 0
        foc = user.get('edge_follow', {}).get('count') or user.get('following_count') or 0
        mc = user.get('edge_owner_to_timeline_media', {}).get('count') or user.get('media_count') or 0
        mutual = user.get('edge_mutual_followed_by', {})
        mc2 = mutual.get('count', 0) if isinstance(mutual, dict) else 0
        p = WebProfileData(
            username=user.get('username', ''), full_name=user.get('full_name', ''),
            user_id=str(user.get('id', user.get('pk', ''))), fbid=str(user.get('fbid', '')),
            biography=biography, follower_count=int(fc), following_count=int(foc), media_count=int(mc),
            is_verified=bool(user.get('is_verified')), is_private=bool(user.get('is_private')),
            is_business_account=bool(user.get('is_business_account')), is_professional_account=bool(user.get('is_professional_account')),
            category_name=user.get('category_name') if user.get('category_name') != 'None' else None,
            category_enum=user.get('category_enum'), external_url=user.get('external_url'),
            bio_links=bio_links, profile_pic_url=user.get('profile_pic_url', ''),
            profile_pic_url_hd=user.get('profile_pic_url_hd', ''),
            business_address=business_address, business_email=user.get('business_email') or None,
            business_phone=user.get('business_phone_number') or None,
            business_category_name=user.get('business_category_name') if user.get('business_category_name') != 'None' else None,
            highlight_reel_count=int(user.get('highlight_reel_count', 0)),
            has_clips=bool(user.get('has_clips')), has_guides=bool(user.get('has_guides')),
            has_channel=bool(user.get('has_channel')), is_joined_recently=bool(user.get('is_joined_recently')),
            pronouns=user.get('pronouns', []) or [], mutual_followers_count=mc2,
            followed_by_viewer=bool(user.get('followed_by_viewer')), follows_viewer=bool(user.get('follows_viewer')),
            _raw=user
        )
        self.logger.info(f"✅ @{p.username} — {p.follower_count:,} followers, {p.media_count:,} posts")
        return p

    def _parse_follow_list(self, data: Dict) -> FollowListResult:
        users = []
        for u in data.get('users', []):
            users.append(FollowUserItem(
                username=u.get('username', ''), full_name=u.get('full_name', ''),
                user_id=str(u.get('pk', u.get('id', ''))),
                is_verified=bool(u.get('is_verified')), is_private=bool(u.get('is_private')),
                profile_pic_url=u.get('profile_pic_url', ''),
                has_anonymous_profile_picture=bool(u.get('has_anonymous_profile_picture'))
            ))
        return FollowListResult(
            users=users, next_max_id=data.get('next_max_id'),
            has_more=bool(data.get('next_max_id')), total_count=len(users)
        )

    def _parse_friendship(self, data: Dict, user_id: str) -> FriendshipStatus:
        s = data if 'following' in data else data.get('friendship_status', data)
        return FriendshipStatus(
            following=bool(s.get('following')), followed_by=bool(s.get('followed_by')),
            blocking=bool(s.get('blocking')), muting=bool(s.get('muting')),
            is_private=bool(s.get('is_private')), incoming_request=bool(s.get('incoming_request')),
            outgoing_request=bool(s.get('outgoing_request')), is_restricted=bool(s.get('is_restricted')),
            is_feed_favorite=bool(s.get('is_feed_favorite')), user_id=user_id
        )

    def _parse_user_feed(self, data: Dict) -> UserFeedResult:
        posts = []
        for item in data.get('items', []):
            posts.append(self._parse_feed_post(item))
        return UserFeedResult(
            posts=posts, next_max_id=data.get('next_max_id'),
            has_more=bool(data.get('more_available', data.get('next_max_id'))),
            total_count=len(posts)
        )

    def _parse_feed_post(self, item: Dict) -> FeedPost:
        caption_obj = item.get('caption') or {}
        caption = caption_obj.get('text', '') if isinstance(caption_obj, dict) else str(caption_obj)
        images = item.get('image_versions2', {}).get('candidates', [])
        image_url = images[0].get('url', '') if images else ''
        videos = item.get('video_versions', [])
        video_url = videos[0].get('url') if videos else None
        usertags = [t.get('user', {}).get('username', '') for t in (item.get('usertags', {}).get('in', []))]
        carousel = []
        for cm in item.get('carousel_media', []):
            ci = cm.get('image_versions2', {}).get('candidates', [])
            cv = cm.get('video_versions', [])
            carousel.append({'image_url': ci[0].get('url', '') if ci else '', 'video_url': cv[0].get('url') if cv else None, 'media_type': cm.get('media_type', 1)})
        location = item.get('location')
        if location and isinstance(location, dict):
            location = {'pk': location.get('pk'), 'name': location.get('name', ''), 'address': location.get('address', ''), 'city': location.get('city', ''), 'lat': location.get('lat'), 'lng': location.get('lng')}
        owner = item.get('user', {})
        return FeedPost(
            media_id=str(item.get('pk', item.get('id', ''))), shortcode=item.get('code', ''),
            media_type=item.get('media_type', 1), caption=caption,
            like_count=item.get('like_count', 0), comment_count=item.get('comment_count', 0),
            view_count=item.get('view_count', item.get('play_count', 0)),
            timestamp=item.get('taken_at', 0), image_url=image_url, video_url=video_url,
            is_video=bool(item.get('video_versions')), location=location, usertags=usertags,
            carousel_media=carousel, is_paid_partnership=bool(item.get('is_paid_partnership')),
            is_pinned=bool(item.get('timeline_pinned_user_ids') or item.get('is_pinned', False)),
            owner_username=owner.get('username', ''), owner_id=str(owner.get('pk', ''))
        )

    def _parse_media_info(self, item: Dict) -> MediaInfo:
        caption_obj = item.get('caption') or {}
        caption = caption_obj.get('text', '') if isinstance(caption_obj, dict) else ''
        owner = item.get('user', {})
        usertags = [t.get('user', {}).get('username', '') for t in (item.get('usertags', {}).get('in', []))]
        location = item.get('location')
        if location and isinstance(location, dict):
            location = {'pk': location.get('pk'), 'name': location.get('name', ''), 'address': location.get('address', '')}
        return MediaInfo(
            media_id=str(item.get('pk', '')), shortcode=item.get('code', ''),
            media_type=item.get('media_type', 1), caption=caption,
            like_count=item.get('like_count', 0), comment_count=item.get('comment_count', 0),
            view_count=item.get('view_count', 0), play_count=item.get('play_count', 0),
            timestamp=item.get('taken_at', 0),
            image_versions=item.get('image_versions2', {}).get('candidates', []),
            video_versions=item.get('video_versions', []),
            location=location, usertags=usertags,
            is_paid_partnership=bool(item.get('is_paid_partnership')),
            owner_username=owner.get('username', ''), owner_id=str(owner.get('pk', '')),
            _raw=item
        )

    def _parse_comments(self, data: Dict) -> CommentsResult:
        comments = []
        for c in data.get('comments', []):
            user = c.get('user', {})
            comments.append(CommentItem(
                comment_id=str(c.get('pk', '')), text=c.get('text', ''),
                username=user.get('username', ''), user_id=str(user.get('pk', '')),
                timestamp=c.get('created_at', 0), like_count=c.get('comment_like_count', 0),
                reply_count=len(c.get('preview_child_comments', [])),
                is_verified=bool(user.get('is_verified'))
            ))
        return CommentsResult(
            comments=comments, next_min_id=data.get('next_min_id'),
            has_more=bool(data.get('has_more_comments', data.get('next_min_id'))),
            total_count=data.get('comment_count', len(comments))
        )

    def _parse_likers(self, data: Dict) -> LikersResult:
        likers = []
        for u in data.get('users', []):
            likers.append(LikerItem(
                username=u.get('username', ''), full_name=u.get('full_name', ''),
                user_id=str(u.get('pk', '')), is_verified=bool(u.get('is_verified')),
                profile_pic_url=u.get('profile_pic_url', '')
            ))
        return LikersResult(likers=likers, total_count=data.get('user_count', len(likers)))

    def _parse_story_items(self, items: List, user: Dict) -> List[StoryMediaItem]:
        stories = []
        for item in items:
            images = item.get('image_versions2', {}).get('candidates', [])
            videos = item.get('video_versions', [])

            # Story mention/tag extraction
            reel_mentions = []
            # reel_mentions field — tag qilingan userlar
            for rm in item.get('reel_mentions', []):
                u = rm.get('user', {})
                username = u.get('username', '')
                if username:
                    reel_mentions.append(username)
            # story_bloks_stickers ichida ham mention bo'lishi mumkin
            for sticker in item.get('story_bloks_stickers', []):
                sticker_data = sticker.get('bloks_sticker', {}).get('sticker_data', {})
                # mention sticker — username TO'G'RIDAN-TO'G'RI ig_mention ichida
                ig_mention = sticker_data.get('ig_mention', {})
                mention_user = ig_mention.get('username', '')
                if mention_user and mention_user not in reel_mentions:
                    reel_mentions.append(mention_user)

            # story_hashtags field
            story_hashtags = []
            for sh in item.get('story_hashtags', []):
                ht = sh.get('hashtag', {})
                name = ht.get('name', '')
                if name:
                    story_hashtags.append(name)

            stories.append(StoryMediaItem(
                story_id=str(item.get('pk', '')), media_type=item.get('media_type', 1),
                image_url=images[0].get('url', '') if images else '',
                video_url=videos[0].get('url') if videos else None,
                timestamp=item.get('taken_at', 0), expiring_at=item.get('expiring_at', 0),
                has_audio=bool(item.get('has_audio')),
                owner_username=user.get('username', ''), owner_id=str(user.get('pk', '')),
                reel_mentions=reel_mentions,
                story_hashtags=story_hashtags,
            ))
        return stories

    def _parse_highlights(self, data: Dict) -> HighlightsResult:
        highlights = []
        for h in data.get('tray', []):
            highlights.append(HighlightInfo(
                highlight_id=str(h.get('id', '')), title=h.get('title', ''),
                cover_url=h.get('cover_media', {}).get('cropped_image_version', {}).get('url', ''),
                media_count=h.get('media_count', 0),
                items=[]  # Items require separate API call
            ))
        return HighlightsResult(highlights=highlights, total_count=len(highlights))

    def _parse_reels(self, data: Dict) -> ReelsResult:
        reels = []
        for item in data.get('items', []):
            media = item.get('media', item)
            caption_obj = media.get('caption') or {}
            caption = caption_obj.get('text', '') if isinstance(caption_obj, dict) else ''
            videos = media.get('video_versions', [])
            images = media.get('image_versions2', {}).get('candidates', [])
            owner = media.get('user', {})
            reels.append(ReelItem(
                media_id=str(media.get('pk', '')), shortcode=media.get('code', ''),
                play_count=media.get('play_count', 0), like_count=media.get('like_count', 0),
                comment_count=media.get('comment_count', 0),
                video_url=videos[0].get('url', '') if videos else '',
                thumbnail_url=images[0].get('url', '') if images else '',
                caption=caption, timestamp=media.get('taken_at', 0),
                owner_username=owner.get('username', ''), owner_id=str(owner.get('pk', ''))
            ))
        return ReelsResult(
            reels=reels, paging_token=data.get('paging_info', {}).get('max_id'),
            has_more=bool(data.get('paging_info', {}).get('more_available'))
        )

    def _parse_search_results(self, query: str, data: Dict, limit: int) -> WebSearchResult:
        users_list = []
        # Handle different response formats
        raw_users = data.get('users', []) or data.get('data', {}).get('users', [])
        # topsearch_flat format: has 'list' with items containing 'user' key
        if not raw_users and data.get('list'):
            raw_users = [item for item in data.get('list', []) if item.get('user')]
        for raw_user in raw_users[:limit]:
            ud = raw_user.get('user', raw_user)
            users_list.append(SearchUserResult(
                username=ud.get('username', ''), full_name=ud.get('full_name', ''),
                user_id=str(ud.get('pk', ud.get('id', ''))),
                is_verified=bool(ud.get('is_verified')), is_private=bool(ud.get('is_private')),
                profile_pic_url=ud.get('profile_pic_url', ''),
                follower_count=int(ud.get('follower_count', 0)),
                mutual_followers_count=int(ud.get('mutual_followers_count', 0))
            ))
        return WebSearchResult(query=query, users=users_list, total_found=len(users_list))

    def _parse_hashtag(self, tag: str, data: Dict) -> HashtagSection:
        posts = []
        for section in data.get('sections', []):
            for medias in section.get('layout_content', {}).get('medias', []):
                media = medias.get('media', {})
                if media: posts.append({'media_id': str(media.get('pk', '')), 'shortcode': media.get('code', ''), 'like_count': media.get('like_count', 0), 'comment_count': media.get('comment_count', 0)})
        return HashtagSection(
            tag_name=tag, media_count=data.get('media_count', len(posts)),
            posts=posts, next_max_id=data.get('next_max_id'),
            has_more=bool(data.get('more_available', data.get('next_max_id')))
        )

    def _parse_location(self, location_id: str, data: Dict) -> LocationSection:
        posts = []
        loc_name = ''
        for section in data.get('sections', []):
            for medias in section.get('layout_content', {}).get('medias', []):
                media = medias.get('media', {})
                if media:
                    loc = media.get('location', {})
                    if loc and not loc_name: loc_name = loc.get('name', '')
                    posts.append({'media_id': str(media.get('pk', '')), 'shortcode': media.get('code', ''), 'like_count': media.get('like_count', 0)})
        return LocationSection(
            location_name=loc_name, location_id=location_id, posts=posts,
            next_max_id=data.get('next_max_id'), has_more=bool(data.get('more_available', data.get('next_max_id')))
        )

    # ══════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════

    @property
    def request_count(self) -> int:
        return self._request_count

    def __repr__(self) -> str:
        has_page = '✅' if self.page else '❌'
        return f"<InstagramWebAPI page={has_page} requests={self._request_count}>"
