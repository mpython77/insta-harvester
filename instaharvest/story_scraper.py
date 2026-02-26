"""
Instagram Story Scraper
View and extract story items (images/videos) via API interception.

Usage:
    from instaharvest import StoryScraper, ScraperConfig

    scraper = StoryScraper(ScraperConfig())
    result = scraper.scrape("username")
    for item in result.items:
        print(f"{item.media_type}: {item.media_url}")
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from .base import BaseScraper
from .config import ScraperConfig


@dataclass
class StoryItem:
    """Single story item (image or video)"""
    media_url: str = ''
    media_type: str = 'image'  # 'image' | 'video'
    timestamp: str = ''
    expiry: str = ''
    width: int = 0
    height: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryResult:
    """Result from story scraping"""
    username: str = ''
    story_count: int = 0
    has_stories: bool = False
    items: List[StoryItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'story_count': self.story_count,
            'has_stories': self.has_stories,
            'items': [item.to_dict() for item in self.items],
        }


class StoryScraper(BaseScraper):
    """
    Scrape stories from Instagram profiles.

    Uses two methods:
    1. Network interception: Capture story API responses
    2. DOM extraction: Fallback to parsing visible story elements

    Features:
    - Intercepts /api/v1/feed/reels_media/ and graphql story endpoints
    - Extracts both image and video URLs
    - Gets timestamps and expiry information
    - Handles profiles with no stories gracefully
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self._story_responses: List[Dict] = []

    def scrape(self, username: str) -> StoryResult:
        """
        Scrape stories from a user profile.

        Args:
            username: Instagram username (without @)

        Returns:
            StoryResult with story items
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"Scraping stories for @{username}")

        result = StoryResult(username=username)
        self._story_responses = []

        try:
            session_data = self._load_session()
            self.setup_browser(session_data)

            # Setup network interception for story API
            self._setup_story_interceptor()

            # Navigate to profile
            profile_url = self.config.profile_url_pattern.format(username=username)
            self.goto_url(profile_url)
            time.sleep(self.config.page_stability_delay)

            # Check if profile has stories (highlighted ring around avatar)
            result.has_stories = self._has_story_ring()

            if not result.has_stories:
                self.logger.info(f"@{username} has no active stories")
                return result

            # Click on story avatar to open stories
            story_opened = self._click_story_avatar()
            if not story_opened:
                self.logger.warning("Could not open stories")
                return result

            time.sleep(2.0)  # Wait for story to load

            # Extract stories from intercepted API data
            items = self._extract_from_intercepted()

            # Fallback: DOM extraction
            if not items:
                items = self._extract_from_dom()

            # Navigate through stories to get more
            if items:
                additional = self._navigate_stories(max_extra=20)
                for item in additional:
                    if item.media_url not in [i.media_url for i in items]:
                        items.append(item)

            result.items = items
            result.story_count = len(items)
            self.logger.info(f"Found {len(items)} story items for @{username}")

        except Exception as e:
            self.logger.error(f"Story scraping failed: {e}")
            raise
        finally:
            self.close()

        return result

    def _setup_story_interceptor(self) -> None:
        """Setup network request interception for story API endpoints"""
        def handle_response(response):
            try:
                url = response.url
                story_patterns = [
                    '/api/v1/feed/reels_media/',
                    '/api/v1/feed/user/',
                    'graphql/query',
                    '/api/v1/stories/',
                ]
                if any(p in url for p in story_patterns):
                    try:
                        body = response.json()
                        self._story_responses.append({
                            'url': url,
                            'data': body,
                        })
                        self.logger.debug(f"Intercepted story API: {url[:80]}")
                    except Exception:
                        pass
            except Exception:
                pass

        self.page.on('response', handle_response)

    def _has_story_ring(self) -> bool:
        """Check if profile avatar has story ring (gradient border)"""
        try:
            # Story ring is usually indicated by a canvas or gradient element around avatar
            selectors = [
                'header canvas',
                'header svg circle[stroke-dasharray]',
                'header div[role="button"] canvas',
                'header a[href*="stories"] img',
            ]
            for selector in selectors:
                try:
                    el = self.page.locator(selector).first
                    if el.count() > 0:
                        return True
                except Exception:
                    continue

            # Alternative: check for clickable story element
            story_link = self.page.locator(f'a[href*="/stories/"]').first
            if story_link.count() > 0:
                return True

            return False
        except Exception:
            return False

    def _click_story_avatar(self) -> bool:
        """Click on profile avatar to open stories"""
        try:
            selectors = [
                'header canvas',
                'header img[alt*="profile"]',
                'header a[href*="stories"]',
                f'header div[role="button"]',
            ]
            for selector in selectors:
                try:
                    el = self.page.locator(selector).first
                    if el.count() > 0:
                        el.click()
                        time.sleep(1.0)
                        # Verify story viewer opened
                        if self._is_story_viewer_open():
                            return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _is_story_viewer_open(self) -> bool:
        """Check if story viewer overlay is open"""
        try:
            indicators = [
                'div[role="dialog"]',
                'div[class*="story"]',
                'section[class*="story"]',
                'div[style*="position: fixed"]',
            ]
            for selector in indicators:
                try:
                    if self.page.locator(selector).first.count() > 0:
                        return True
                except Exception:
                    continue
            return '/stories/' in self.page.url
        except Exception:
            return False

    def _extract_from_intercepted(self) -> List[StoryItem]:
        """Extract story items from intercepted API responses"""
        items = []
        seen_urls = set()

        for response in self._story_responses:
            try:
                data = response['data']
                # Parse reels_media format
                reels = data.get('reels_media', data.get('reels', {}))
                if isinstance(reels, list):
                    for reel in reels:
                        self._parse_reel_items(reel, items, seen_urls)
                elif isinstance(reels, dict):
                    for reel in reels.values():
                        if isinstance(reel, dict):
                            self._parse_reel_items(reel, items, seen_urls)

                # Parse graphql format
                if 'data' in data:
                    gql_data = data['data']
                    reel_data = (
                        gql_data.get('reels_media', []) or
                        [gql_data.get('reel', {})] if gql_data.get('reel') else []
                    )
                    for reel in reel_data:
                        if reel:
                            self._parse_reel_items(reel, items, seen_urls)

            except Exception as e:
                self.logger.debug(f"Parse error: {e}")

        return items

    def _parse_reel_items(self, reel: Dict, items: List[StoryItem], seen: set) -> None:
        """Parse story items from a reel object"""
        reel_items = reel.get('items', [])
        for item in reel_items:
            try:
                # Video
                video_versions = item.get('video_versions', [])
                if video_versions:
                    url = video_versions[0].get('url', '')
                    if url and url not in seen:
                        seen.add(url)
                        items.append(StoryItem(
                            media_url=url,
                            media_type='video',
                            timestamp=str(item.get('taken_at', '')),
                            expiry=str(item.get('expiring_at', '')),
                            width=video_versions[0].get('width', 0),
                            height=video_versions[0].get('height', 0),
                        ))
                    continue

                # Image
                image_versions = item.get('image_versions2', {}).get('candidates', [])
                if image_versions:
                    url = image_versions[0].get('url', '')
                    if url and url not in seen:
                        seen.add(url)
                        items.append(StoryItem(
                            media_url=url,
                            media_type='image',
                            timestamp=str(item.get('taken_at', '')),
                            expiry=str(item.get('expiring_at', '')),
                            width=image_versions[0].get('width', 0),
                            height=image_versions[0].get('height', 0),
                        ))
            except Exception:
                continue

    def _extract_from_dom(self) -> List[StoryItem]:
        """Fallback: Extract story media from DOM elements"""
        items = []
        try:
            # Look for video/image sources in story viewer
            videos = self.page.locator('video source, video[src]').all()
            for v in videos:
                src = v.get_attribute('src') or ''
                if src and 'instagram' in src:
                    items.append(StoryItem(media_url=src, media_type='video'))

            images = self.page.locator('img[srcset], img[src*="instagram"]').all()
            for img in images:
                src = img.get_attribute('srcset') or img.get_attribute('src') or ''
                if src and 'instagram' in src and 'profile' not in src:
                    # Take highest quality from srcset
                    if ',' in src:
                        src = src.split(',')[-1].strip().split()[0]
                    items.append(StoryItem(media_url=src, media_type='image'))
        except Exception:
            pass
        return items

    def _navigate_stories(self, max_extra: int = 20) -> List[StoryItem]:
        """Click through stories to load more items"""
        items = []
        for _ in range(max_extra):
            try:
                # Click right side to go to next story
                width = self.page.viewport_size['width']
                height = self.page.viewport_size['height']
                self.page.mouse.click(width * 0.8, height * 0.5)
                time.sleep(0.8)

                # Check if story viewer is still open
                if not self._is_story_viewer_open():
                    break

                # Extract new items from intercepted data
                new_items = self._extract_from_intercepted()
                for item in new_items:
                    if item.media_url not in [i.media_url for i in items]:
                        items.append(item)

            except Exception:
                break
        return items

    def _load_session(self) -> Dict:
        """Load session from file"""
        session_file = Path(self.config.session_file)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}
