"""
Instagram Story Scraper
View and extract story items (images/videos) and tagged accounts.

Architecture:
    PRIMARY: Extract tags/mentions from embedded <script> JSON data (ig_mention, reel_mentions)
    FALLBACK: DOM parsing (img alt text, anchor links, text spans)

    Instagram pre-loads ALL story slide data in a single JSON blob on page load.
    This means we can extract tags from ALL slides without navigating through them,
    making the process faster, more reliable, and safer for the account.

Usage:
    from instaharvest import StoryScraper, ScraperConfig

    scraper = StoryScraper(ScraperConfig())
    result = scraper.scrape("username")
    print(result.all_tagged_accounts)   # ['user1', 'user2']
    for item in result.items:
        print(f"{item.media_type}: {item.media_url}")
        print(f"Caption: {item.caption}")
        print(f"Tags: {item.tagged_accounts}")
"""

import json
import re
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set, Tuple

from .base import BaseScraper
from .config import ScraperConfig


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class StorySlideInfo:
    """Per-slide tag and metadata mapping."""
    slide_index: int = 0
    timestamp: str = ''           # ISO format datetime
    timestamp_unix: int = 0       # Unix timestamp
    media_type: str = 'unknown'   # 'image' | 'video' | 'unknown'
    tagged_accounts: List[str] = field(default_factory=list)
    has_tags: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryItem:
    """Single story item (image or video)"""
    media_url: str = ''
    media_type: str = 'image'  # 'image' | 'video'
    timestamp: str = ''
    expiry: str = ''
    width: int = 0
    height: int = 0
    caption: str = ''
    tagged_accounts: List[str] = field(default_factory=list)
    slide_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryResult:
    """Result from story scraping"""
    username: str = ''
    story_count: int = 0
    has_stories: bool = False
    items: List[StoryItem] = field(default_factory=list)
    slides: List[StorySlideInfo] = field(default_factory=list)
    all_tagged_accounts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'story_count': self.story_count,
            'has_stories': self.has_stories,
            'items': [item.to_dict() for item in self.items],
            'slides': [s.to_dict() for s in self.slides],
            'all_tagged_accounts': self.all_tagged_accounts,
        }


# ═══════════════════════════════════════════════════════════════
# StoryScraper
# ═══════════════════════════════════════════════════════════════

class StoryScraper(BaseScraper):
    """
    Scrape stories from Instagram profiles.

    Extraction Pipeline:
        1. Navigate to /stories/{username}/
        2. Handle "View story" dialog
        3. Pause story (single pause, no slide navigation)
        4. PRIMARY: Extract ALL tags from embedded <script> JSON
        5. FALLBACK: DOM-based extraction (img alt, anchors, spans)
        6. Extract media from intercepted API or DOM

    Features:
        - JSON-first architecture: all tags from all slides in one read
        - No slide navigation needed: faster, safer, more reliable
        - Challenge delay for manual captcha solving
        - ig_mention, reel_mentions, story_bloks_stickers support
        - Caption extraction from img alt text
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self._story_responses: List[Dict] = []

    # ───────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────

    def scrape(self, username: str, extract_tags: bool = True, challenge_delay: int = 10) -> StoryResult:
        """
        Scrape stories from a user profile.

        Args:
            username: Instagram username (without @)
            extract_tags: Extract tagged accounts (default: True)
            challenge_delay: Seconds to wait for manual challenge solving (default: 10)

        Returns:
            StoryResult with story items and tagged accounts
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"Scraping stories for @{username}")

        result = StoryResult(username=username)
        self._story_responses = []

        # Check if browser is already setup (SharedBrowser mode)
        is_shared_browser = self.page is not None and self.browser is not None

        try:
            if is_shared_browser:
                self.logger.debug("Using existing browser session (SharedBrowser mode)")
            else:
                # ── Phase 1: Browser Setup & Session ──
                session_data = self._load_session()
                self.setup_browser(session_data)

            base_url = self.config.instagram_base_url.rstrip('/')

            # SharedBrowser + challenge_delay=0: bosh sahifaga borish SHART EMAS
            # Session allaqachon faol — to'g'ridan-to'g'ri story'ga o'tamiz
            if is_shared_browser and challenge_delay == 0:
                self.logger.debug("⚡ SharedBrowser: homepage skip — to'g'ridan-to'g'ri story'ga")
            else:
                # Activate session on Instagram homepage (birinchi marta kerak)
                self.logger.info("Activating session on Instagram...")
                self.goto_url(base_url + '/')

                if challenge_delay > 0:
                    self.logger.info(f"⏳ {challenge_delay}s kutilmoqda (challenge uchun)...")
                    time.sleep(challenge_delay)

            # ── Phase 2: Navigate to Stories ──
            self._setup_story_interceptor()

            stories_url = f'{base_url}/stories/{username}/'
            self.logger.info(f"Navigating to stories: {stories_url}")
            self.goto_url(stories_url)
            time.sleep(1.5)  # Sahifa barqarorligi (3s→1.5s optimizatsiya)

            # Check redirect (no stories = redirect away)
            if '/stories/' not in self.page.url:
                self.logger.info(f"@{username} has no active stories (redirected)")
                return result

            result.has_stories = True

            # ── Phase 3: View Story & Pause ──
            self._handle_view_story_dialog()
            time.sleep(0.5)  # View dialog (2s→0.5s optimizatsiya)

            self._pause_story()
            time.sleep(0.5)  # Pause (1.5s→0.5s optimizatsiya)

            # ── Phase 4: Extract Tags (JSON-First Architecture) ──
            all_tags: Set[str] = set()
            caption = ''

            if extract_tags:
                # PRIMARY: Script JSON extraction (gets ALL slides at once)
                json_tags, slides = self._extract_tags_from_script_json()
                if json_tags:
                    all_tags.update(json_tags)
                    self.logger.info(f"📦 JSON'dan {len(json_tags)} ta tag topildi: {sorted(json_tags)}")

                # Store per-slide info
                if slides:
                    result.slides = slides
                    tagged_slides = [s for s in slides if s.has_tags]
                    self.logger.info(
                        f"📊 {len(slides)} ta slide, {len(tagged_slides)} tasida tag bor"
                    )

                # FALLBACK: DOM extraction (current visible slide only)
                dom_tags, caption = self._extract_tags_from_dom()
                if dom_tags:
                    # Validatsiya: faqat haqiqiy username'larni qo'shish
                    validated_dom_tags = {t for t in dom_tags if self._is_valid_instagram_username(t)}
                    new_tags = validated_dom_tags - all_tags
                    if new_tags:
                        self.logger.info(f"🔍 DOM'dan {len(new_tags)} ta qo'shimcha tag: {sorted(new_tags)}")
                    if dom_tags - validated_dom_tags:
                        self.logger.debug(
                            f"🚫 DOM filtrlangan (noto'g'ri username): "
                            f"{sorted(dom_tags - validated_dom_tags)}"
                        )
                    all_tags.update(validated_dom_tags)

            # ── Phase 5: Extract Media ──
            items = self._extract_from_intercepted()
            if not items:
                items = self._extract_from_dom_media()

            # Attach per-slide tags to matching items (by slide_index or timestamp)
            slide_tag_map = {s.slide_index: s for s in result.slides} if result.slides else {}

            for item in items:
                # Try to match item to a slide by index or timestamp
                matched_slide = slide_tag_map.get(item.slide_index)
                if matched_slide:
                    item.tagged_accounts = matched_slide.tagged_accounts
                else:
                    item.tagged_accounts = sorted(list(all_tags))
                item.caption = caption

            # If no media but we have tags, create placeholder
            if not items and all_tags:
                items = [StoryItem(
                    media_type='unknown',
                    caption=caption,
                    tagged_accounts=sorted(list(all_tags)),
                )]

            result.items = items
            result.all_tagged_accounts = sorted(list(all_tags))
            result.story_count = len(items)

            self.logger.info(
                f"✅ {result.story_count} story, "
                f"{len(result.all_tagged_accounts)} tag @{username} uchun"
            )

        except Exception as e:
            self.logger.error(f"Story scraping failed: {e}")
            raise
        finally:
            if not is_shared_browser:
                self.close()
            else:
                self.logger.debug("Keeping browser open (SharedBrowser mode)")

        return result

    # ───────────────────────────────────────────────────────────
    # Phase 3: Story Dialog & Pause
    # ───────────────────────────────────────────────────────────

    def _handle_view_story_dialog(self) -> None:
        """
        Handle 'View as X?' confirmation dialog.
        Instagram shows this before loading story content.
        """
        try:
            # Method 1: Direct button selectors
            for selector in [
                'button:has-text("View story")',
                'div[role="button"]:has-text("View story")',
            ]:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        self.logger.info("✅ 'View story' dialog accepted")
                        return
                except Exception as e:
                    self.logger.debug(f"View story selector '{selector}' failed: {e}")
                    continue

            # Method 2: Role-based
            try:
                btn = self.page.get_by_role("button", name="View story")
                if btn.count() > 0 and btn.is_visible():
                    btn.click()
                    self.logger.info("✅ 'View story' dialog accepted (role)")
                    return
            except Exception as e:
                self.logger.debug(f"View story role-based lookup failed: {e}")
                pass

            # Method 3: Text match fallback
            try:
                for el in self.page.locator('div, button, span').all():
                    try:
                        if el.inner_text().strip() == 'View story':
                            el.click()
                            self.logger.info("✅ 'View story' dialog accepted (text)")
                            return
                    except Exception as e:
                        self.logger.debug(f"View story text match element failed: {e}")
                        continue
            except Exception as e:
                self.logger.debug(f"View story text match iteration failed: {e}")
                pass

            self.logger.debug("No 'View story' dialog detected")

        except Exception as e:
            self.logger.debug(f"View story dialog: {e}")

    def _pause_story(self) -> None:
        """Pause story to prevent auto-advancing."""
        try:
            # Method 1: Pause button
            for selector in [
                'button[aria-label="Pause"]',
                'svg[aria-label="Pause"]',
            ]:
                try:
                    el = self.page.locator(selector).first
                    if el.count() > 0:
                        el.click()
                        self.logger.debug("Story paused via button")
                        return
                except Exception as e:
                    self.logger.debug(f"Pause button '{selector}' failed: {e}")
                    continue

            # Method 2: Keyboard shortcut
            try:
                self.page.keyboard.press('Space')
                self.logger.debug("Story paused via keyboard")
            except Exception as e:
                self.logger.debug(f"Keyboard pause failed: {e}")

        except Exception as e:
            self.logger.debug(f"Could not pause: {e}")

    # ───────────────────────────────────────────────────────────
    # Phase 4A: PRIMARY — Script JSON Extraction
    # ───────────────────────────────────────────────────────────

    def _extract_tags_from_script_json(self) -> Tuple[Set[str], List[StorySlideInfo]]:
        """
        PRIMARY extraction: Parse embedded <script type="application/json"> tags.

        Returns:
            Tuple of (flat set of all tags, list of StorySlideInfo per slide)
        """
        tags: Set[str] = set()
        slides: List[StorySlideInfo] = []

        try:
            scripts = self.page.locator('script[type="application/json"]').all()
            self.logger.debug(f"Found {len(scripts)} JSON script tags")

            for script in scripts:
                try:
                    content = script.inner_text().strip()
                    if not content or len(content) < 20:
                        continue
                    data = json.loads(content)

                    # Extract flat tags
                    self._find_mentions_recursive(data, tags)

                    # Extract per-slide mapping
                    self._find_story_items_with_tags(data, slides)

                except (json.JSONDecodeError, Exception) as e:
                    self.logger.debug(f"JSON script parse error: {e}")
                    continue

        except Exception as e:
            self.logger.debug(f"Script JSON extraction error: {e}")

        # Deduplicate slides by index
        if slides:
            seen_indices = set()
            unique_slides = []
            for s in slides:
                if s.slide_index not in seen_indices:
                    seen_indices.add(s.slide_index)
                    unique_slides.append(s)
            slides = sorted(unique_slides, key=lambda s: s.slide_index)

        return tags, slides

    def _find_mentions_recursive(self, data: Any, tags: Set[str], depth: int = 0) -> None:
        """
        Recursively search JSON for mention/tag data.

        Handles these Instagram JSON structures:
        - ig_mention: {username: "...", full_name: "..."}
        - reel_mentions: [{user: {username: "..."}}]
        - story_bloks_stickers: [{bloks_sticker: {sticker_data: {ig_mention: {...}}}}]
        """
        if depth > self.config.json_story_recursion_depth:
            return

        if isinstance(data, dict):
            # ── ig_mention ──
            if 'ig_mention' in data:
                mention = data['ig_mention']
                if isinstance(mention, dict):
                    username = mention.get('username', '')
                    if username and isinstance(username, str) and len(username) <= 30:
                        tags.add(username)

            # ── reel_mentions ──
            if 'reel_mentions' in data:
                reel_mentions = data['reel_mentions']
                if isinstance(reel_mentions, list):
                    for m in reel_mentions:
                        if isinstance(m, dict):
                            user = m.get('user', {})
                            if isinstance(user, dict):
                                username = user.get('username', '')
                                if username and isinstance(username, str):
                                    tags.add(username)

            # ── story_bloks_stickers ──
            if 'story_bloks_stickers' in data:
                stickers = data['story_bloks_stickers']
                if isinstance(stickers, list):
                    for sticker in stickers:
                        self._find_mentions_recursive(sticker, tags, depth + 1)

            # Recurse into all values
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._find_mentions_recursive(value, tags, depth + 1)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._find_mentions_recursive(item, tags, depth + 1)
    # ═══════════════════════════════════════════════════════════════
    # USERNAME VALIDATION
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _is_valid_instagram_username(username: str) -> bool:
        """
        Instagram username validatsiyasi — noto'g'ri tag'larni filtrlash.

        Instagram qoidalari:
            - 1-30 belgi
            - Faqat harf, raqam, nuqta (.), pastki chiziq (_)
            - Nuqta bilan boshlanib/tugamasligi kerak
            - Ketma-ket nuqtalar yo'q

        Qo'shimcha evristik filtrlash:
            - 20+ belgili username'da separator (_, .) bo'lmasa → soxta
              (masalan: dolcegabbanashowroomtoday)
            - Kichik harfda common so'zlar birikmasi → soxta
        """
        if not username or not isinstance(username, str):
            return False

        u = username.strip().lower()

        # Uzunlik tekshirish
        if len(u) < 1 or len(u) > 30:
            return False

        # Faqat ruxsat etilgan belgilar
        if not re.match(r'^[a-zA-Z0-9_.]+$', u):
            return False

        # Nuqta bilan boshlanish/tugash
        if u.startswith('.') or u.endswith('.'):
            return False

        # Ketma-ket nuqtalar
        if '..' in u:
            return False

        # ── Evristik: uzun username separator'siz = soxta ──
        # Haqiqiy uzun username'lar: dolce_gabbana_official, my.fashion.page
        # Soxta: dolcegabbanashowroomtoday (img alt mashup)
        if len(u) > 18 and '_' not in u and '.' not in u:
            return False

        # ── Evristik: umumiy so'zlar birikmasi ──
        # "showroom", "today", "official" kabi so'zlar username'da
        # bo'lishi mumkin, lekin ularsiz ham uzun bo'lsa soxta
        false_suffixes = [
            'showroom', 'today', 'tomorrow', 'yesterday',
            'thankyou', 'giveaway', 'collab', 'lookbook',
        ]
        for suffix in false_suffixes:
            # username oddiy so'z + suffix bo'lsa va separator yo'q
            if u.endswith(suffix) and len(u) > len(suffix) + 5:
                base = u[:-len(suffix)]
                if '_' not in base and '.' not in base and len(base) > 10:
                    return False

        return True

    def _find_story_items_with_tags(
        self, data: Any, slides: List[StorySlideInfo], depth: int = 0
    ) -> None:
        """
        Find story 'items' arrays in JSON and extract per-slide tag mapping.

        Looks for arrays of objects that have 'taken_at' (= story items)
        and maps each item's stickers/mentions to a StorySlideInfo.
        """
        if depth > self.config.json_story_items_depth:
            return

        if isinstance(data, dict):
            # Check if this dict has an 'items' key with story items
            if 'items' in data and isinstance(data['items'], list):
                items_list = data['items']
                # Verify these are story items (must have 'taken_at')
                if items_list and isinstance(items_list[0], dict) and 'taken_at' in items_list[0]:
                    for idx, item in enumerate(items_list):
                        if not isinstance(item, dict):
                            continue

                        # Get timestamp
                        taken_at = item.get('taken_at', 0)
                        timestamp_str = ''
                        if taken_at:
                            try:
                                from datetime import datetime, timezone
                                dt = datetime.fromtimestamp(int(taken_at), tz=timezone.utc)
                                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                            except Exception as e:
                                self.logger.debug(f"Timestamp parse error for {taken_at}: {e}")
                                timestamp_str = str(taken_at)

                        # Determine media type
                        media_type = 'video' if item.get('video_versions') else 'image'

                        # Extract tags from this specific item
                        item_tags: Set[str] = set()
                        self._find_mentions_recursive(item, item_tags)

                        slides.append(StorySlideInfo(
                            slide_index=idx,
                            timestamp=timestamp_str,
                            timestamp_unix=int(taken_at) if taken_at else 0,
                            media_type=media_type,
                            tagged_accounts=sorted(list(item_tags)),
                            has_tags=len(item_tags) > 0,
                        ))
                    return  # Found story items, no need to recurse further

            # Recurse into values
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._find_story_items_with_tags(value, slides, depth + 1)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._find_story_items_with_tags(item, slides, depth + 1)

    # ───────────────────────────────────────────────────────────
    # Phase 4B: FALLBACK — DOM-based Extraction
    # ───────────────────────────────────────────────────────────

    def _extract_tags_from_dom(self) -> Tuple[Set[str], str]:
        """
        FALLBACK extraction: Parse visible DOM elements for tags.

        Strategies:
        1. img alt text (Instagram OCR): img[alt] → @mentions
        2. Anchor tags: a[href] → profile links
        3. Text elements: span/div → @mention text

        Returns:
            Tuple of (set of usernames, caption text)
        """
        tags: Set[str] = set()
        caption = ''
        mention_re = re.compile(r'@([A-Za-z0-9_.]{1,30})')

        try:
            # Strategy 1: img alt text
            for img in self.page.locator('img[alt]').all():
                try:
                    alt = img.get_attribute('alt') or ''
                    # Extract caption
                    if 'text that says' in alt.lower():
                        match = re.search(
                            r"text that says ['\"](.+?)['\"]",
                            alt, re.IGNORECASE
                        )
                        if match:
                            caption = match.group(1)
                        else:
                            idx = alt.lower().index('text that says')
                            caption = alt[idx + 15:].strip().strip("'.\"")

                    if '@' in alt:
                        for m in mention_re.findall(alt):
                            if m.lower() not in ('', 'instagram'):
                                tags.add(m)
                except Exception as e:
                    self.logger.debug(f"DOM img alt extraction failed: {e}")
                    continue

            # Strategy 2: Anchor tags with profile links
            for link in self.page.locator('a[role="link"]').all():
                try:
                    text = link.inner_text().strip()
                    if text.startswith('@') or ('@' in text and len(text) < 50):
                        for m in mention_re.findall(text):
                            if m.lower() not in ('', 'instagram'):
                                tags.add(m)
                except Exception as e:
                    self.logger.debug(f"DOM anchor tag extraction failed: {e}")
                    continue

            # Strategy 3: Text spans
            for el in self.page.locator('span[dir="auto"], div[dir="auto"]').all():
                try:
                    text = el.inner_text().strip()
                    if '@' in text and len(text) < 100:
                        for m in mention_re.findall(text):
                            if m.lower() not in ('', 'instagram'):
                                tags.add(m)
                except Exception as e:
                    self.logger.debug(f"DOM text span extraction failed: {e}")
                    continue

        except Exception as e:
            self.logger.debug(f"DOM tag extraction error: {e}")

        return tags, caption

    # ───────────────────────────────────────────────────────────
    # Phase 5: Media Extraction
    # ───────────────────────────────────────────────────────────

    def _setup_story_interceptor(self) -> None:
        """Setup network interception for story API endpoints."""
        def handle_response(response):
            try:
                url = response.url
                patterns = [
                    '/api/v1/feed/reels_media/',
                    '/api/v1/feed/user/',
                    'graphql/query',
                    '/api/v1/stories/',
                ]
                if any(p in url for p in patterns):
                    try:
                        body = response.json()
                        self._story_responses.append({
                            'url': url,
                            'data': body,
                        })
                        self.logger.debug(f"Intercepted: {url[:80]}")
                    except Exception as e:
                        self.logger.debug(f"Story response parse error: {e}")
                        pass
            except Exception as e:
                self.logger.debug(f"Story interceptor handler error: {e}")
                pass

        self.page.on('response', handle_response)

    def _extract_from_intercepted(self) -> List[StoryItem]:
        """Extract story items from intercepted API responses."""
        items = []
        seen_urls = set()

        for response in self._story_responses:
            try:
                data = response['data']

                # reels_media format
                reels = data.get('reels_media', data.get('reels', {}))
                if isinstance(reels, list):
                    for reel in reels:
                        self._parse_reel_items(reel, items, seen_urls)
                elif isinstance(reels, dict):
                    for reel in reels.values():
                        if isinstance(reel, dict):
                            self._parse_reel_items(reel, items, seen_urls)

                # graphql format
                if 'data' in data:
                    gql_data = data['data']
                    reel_data = (
                        gql_data.get('reels_media', []) or
                        [gql_data.get('reel', {})]
                    )
                    for reel in reel_data:
                        if isinstance(reel, dict):
                            self._parse_reel_items(reel, items, seen_urls)

            except Exception as e:
                self.logger.debug(f"Intercepted response parse error: {e}")
                continue

        return items

    def _parse_reel_items(self, reel: Dict, items: List[StoryItem], seen_urls: set) -> None:
        """Parse individual reel items from API response."""
        try:
            reel_items = reel.get('items', [])
            for idx, item in enumerate(reel_items):
                # Video
                video_versions = item.get('video_versions', [])
                if video_versions:
                    url = video_versions[0].get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        items.append(StoryItem(
                            media_url=url,
                            media_type='video',
                            timestamp=str(item.get('taken_at', '')),
                            expiry=str(item.get('expiring_at', '')),
                            width=video_versions[0].get('width', 0),
                            height=video_versions[0].get('height', 0),
                            slide_index=idx,
                        ))
                    continue

                # Image
                image_versions = item.get('image_versions2', {}).get('candidates', [])
                if image_versions:
                    url = image_versions[0].get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        items.append(StoryItem(
                            media_url=url,
                            media_type='image',
                            timestamp=str(item.get('taken_at', '')),
                            expiry=str(item.get('expiring_at', '')),
                            width=image_versions[0].get('width', 0),
                            height=image_versions[0].get('height', 0),
                            slide_index=idx,
                        ))
        except Exception as e:
            self.logger.debug(f"Reel items parse error: {e}")
            pass

    def _extract_from_dom_media(self) -> List[StoryItem]:
        """Fallback: Extract story media URLs from DOM elements."""
        items = []
        skip_patterns = ['s150x150', 's100x100', 's320x320', 'profile_pic', '_s64x64']

        try:
            # Videos
            for v in self.page.locator('video source, video[src]').all():
                src = v.get_attribute('src') or ''
                if src and 'instagram' in src:
                    items.append(StoryItem(media_url=src, media_type='video'))

            # Images
            for img in self.page.locator('img[srcset], img[src*="instagram"]').all():
                src = img.get_attribute('srcset') or img.get_attribute('src') or ''
                if src and 'instagram' in src:
                    if any(p in src for p in skip_patterns):
                        continue
                    if ',' in src:
                        src = src.split(',')[-1].strip().split()[0]
                    items.append(StoryItem(media_url=src, media_type='image'))

        except Exception as e:
            self.logger.debug(f"DOM media extraction error: {e}")
            pass
        return items

    # ───────────────────────────────────────────────────────────
    # Utilities
    # ───────────────────────────────────────────────────────────

    def _load_session(self) -> Dict:
        """Load session from file."""
        session_file = Path(self.config.session_file)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}
