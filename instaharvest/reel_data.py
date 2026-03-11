"""
Instagram Scraper - Reel data extractor
Extract tags, likes, timestamps, location, owner, caption from reels

SEPARATE FILE - FOR REELS ONLY!
JSON-First Architecture: Extracts 30+ fields from embedded JSON scripts.
"""

import time
import json
import random
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import HTMLStructureChangedError
from .post_data import PostLocation, PostOwner, CarouselSlide


@dataclass
class ReelData:
    """Reel data structure with JSON-First enriched fields"""
    # Core fields (backward compatible)
    url: str
    tagged_accounts: List[str] = field(default_factory=list)
    likes: Optional[int] = 0
    timestamp: str = 'N/A'
    content_type: str = 'Reel'
    
    # JSON-First enriched fields
    caption: str = ''
    comment_count: int = 0
    like_count: int = 0
    location: Optional[PostLocation] = None
    owner: Optional[PostOwner] = None
    taken_at: int = 0
    taken_at_human: str = ''
    shortcode: str = ''
    pk: str = ''
    media_type: int = 0
    product_type: str = ''
    width: int = 0
    height: int = 0
    accessibility_caption: str = ''
    top_likers: List[str] = field(default_factory=list)
    has_audio: bool = False
    video_duration: float = 0.0
    tag_positions: List[Dict] = field(default_factory=list)
    has_liked: bool = False
    json_extracted: bool = False
    media_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @property
    def has_tags(self) -> bool:
        return len(self.tagged_accounts) > 0
    
    @property
    def has_location(self) -> bool:
        return self.location is not None


class ReelDataScraper(BaseScraper):
    """
    Instagram REEL data scraper - REELS ONLY!

    Features:
    - Extract tagged accounts from reels (via popup button)
    - Extract likes count
    - Extract reel timestamp
    - Multiple fallback methods
    - Error handling
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize reel data scraper"""
        super().__init__(config)
        self.logger.info("ReelDataScraper ready (REELS ONLY)")

    def scrape(
        self,
        reel_url: str,
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True
    ) -> ReelData:
        """
        Scrape data from a single REEL
        
        JSON-First Architecture:
        1. Try extracting all data from embedded JSON scripts (instant)
        2. Fallback to DOM extraction if JSON not available

        Args:
            reel_url: URL of the reel (must contain /reel/)
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract reel timestamp

        Returns:
            ReelData object with 30+ enriched fields
        """
        # Validate it's a reel URL
        if '/reel/' not in reel_url:
            raise ValueError(f"Invalid reel URL: {reel_url} (must contain /reel/)")

        # ═══════ AUTO BROWSER SETUP (standalone mode) ═══════
        is_shared_browser = self.page is not None and self.browser is not None
        if not is_shared_browser:
            self.logger.debug("Setting up new browser session (standalone mode)")
            session_data = self.load_session()
            self.setup_browser(session_data)

        self.logger.info(f"🎬 Scraping REEL: {reel_url}")

        # Navigate to reel
        self.goto_url(reel_url)

        # CRITICAL: Wait for content to load
        time.sleep(self.config.reel_open_delay)

        # ═══════ JSON-FIRST FULL EXTRACTION ═══════
        json_data = self._extract_all_from_json()
        
        if json_data:
            tagged_accounts = json_data.get('tagged_accounts', []) if get_tags else []
            likes = json_data.get('likes', 0) if get_likes else 0
            timestamp = json_data.get('timestamp', 'N/A') if get_timestamp else 'N/A'
            
            data = ReelData(
                url=reel_url,
                tagged_accounts=tagged_accounts or [],
                likes=likes,
                timestamp=timestamp,
                content_type='Reel',
                # JSON-First enriched fields
                caption=json_data.get('caption', ''),
                comment_count=json_data.get('comment_count', 0),
                like_count=json_data.get('like_count', 0),
                location=json_data.get('location'),
                owner=json_data.get('owner'),
                taken_at=json_data.get('taken_at', 0),
                taken_at_human=json_data.get('taken_at_human', ''),
                shortcode=json_data.get('shortcode', ''),
                pk=json_data.get('pk', ''),
                media_type=json_data.get('media_type', 0),
                product_type=json_data.get('product_type', ''),
                width=json_data.get('width', 0),
                height=json_data.get('height', 0),
                accessibility_caption=json_data.get('accessibility_caption', ''),
                top_likers=json_data.get('top_likers', []),
                has_audio=json_data.get('has_audio', False),
                video_duration=json_data.get('video_duration', 0.0),
                tag_positions=json_data.get('tag_positions', []),
                has_liked=json_data.get('has_liked', False),
                media_urls=json_data.get('media_urls', []),
                json_extracted=True
            )
            
            self.logger.info(
                f"✅ JSON-FIRST [Reel]: {len(data.tagged_accounts)} tags, "
                f"{data.likes} likes, {data.comment_count} comments, "
                f"📍 {data.location.name if data.location else 'N/A'}"
            )
            return data
        
        # ═══════ DOM FALLBACK ═══════
        self.logger.warning("⚠️ JSON extraction failed, using DOM fallback...")
        
        tagged_accounts = self.get_tagged_accounts() if get_tags else []
        likes = self.get_likes_count() if get_likes else 0
        timestamp = self.get_timestamp() if get_timestamp else 'N/A'

        data = ReelData(
            url=reel_url,
            tagged_accounts=tagged_accounts,
            likes=likes,
            timestamp=timestamp,
            content_type='Reel'
        )

        self.logger.info(
            f"✅ DOM-Extracted [Reel]: {len(data.tagged_accounts)} tags, "
            f"{data.likes} likes, {data.timestamp}"
        )

        return data

    def scrape_multiple(
        self,
        reel_urls: List[str],
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True,
        delay_between_reels: bool = True
    ) -> List[ReelData]:
        """
        Scrape multiple reels sequentially

        Args:
            reel_urls: List of reel URLs
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract reel timestamp
            delay_between_reels: Add delay between reels (rate limiting)

        Returns:
            List of ReelData objects
        """
        self.logger.info(f"🎬 Scraping {len(reel_urls)} reels...")

        # SharedBrowser check — skip setup if browser already injected
        is_shared_browser = self.page is not None and self.browser is not None
        if not is_shared_browser:
            session_data = self.load_session()
            self.setup_browser(session_data)
        else:
            self.logger.debug("Using existing browser session (SharedBrowser mode)")

        results = []
        start_time = time.time()

        try:
            for i, url in enumerate(reel_urls, 1):
                self.logger.info(f"[{i}/{len(reel_urls)}] Processing Reel: {url}")

                try:
                    data = self.scrape(
                        url,
                        get_tags=get_tags,
                        get_likes=get_likes,
                        get_timestamp=get_timestamp
                    )
                    results.append(data)

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    # Add placeholder data
                    results.append(ReelData(
                        url=url,
                        tagged_accounts=[],
                        likes='ERROR',
                        timestamp='N/A',
                        content_type='Reel'
                    ))

                # Delay between reels (rate limiting)
                if delay_between_reels and i < len(reel_urls):
                    delay = random.uniform(
                        self.config.post_scrape_delay_min,
                        self.config.post_scrape_delay_max
                    )
                    self.logger.debug(f"⏱️ Waiting {delay:.1f}s...")
                    time.sleep(delay)

            # Print final statistics
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.likes != 'ERROR')

            self.logger.info(
                f"\n{'='*70}\n"
                f"📊 REEL SCRAPING COMPLETE\n"
                f"{'='*70}\n"
                f"Total Reels: {len(reel_urls)}\n"
                f"Successfully scraped: {success_count}/{len(reel_urls)} "
                f"({(success_count/len(reel_urls)*100):.1f}%)\n"
                f"Failed: {len(reel_urls) - success_count}\n"
                f"Total time: {total_time:.2f}s\n"
                f"Average time per reel: {total_time/len(reel_urls):.2f}s\n"
                f"{'='*70}"
            )
            return results

        except KeyboardInterrupt:
            self.logger.warning("\n✋ Scraping interrupted by user! Saving extracted data...")
            self.interrupted = True
            
            # Print partial statistics
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.likes != 'ERROR')
            
            self.logger.info(
                f"\n{'='*70}\n"
                f"⚠️  PARTIAL SCRAPING RESULTS (INTERRUPTED)\n"
                f"{'='*70}\n"
                f"Total Processed: {len(results)}/{len(reel_urls)}\n"
                f"Successfully scraped: {success_count}\n"
                f"{'='*70}"
            )
            
            return results

        finally:
            if not is_shared_browser:
                self.close()
            else:
                self.logger.debug("Keeping browser open (SharedBrowser mode)")

    # ==================== JSON-FIRST EXTRACTION ====================

    def _extract_all_from_json(self) -> Optional[Dict[str, Any]]:
        """JSON-FIRST: Extract ALL data from embedded JSON scripts."""
        try:
            scripts = self.page.locator('script[type="application/json"]').all()
            self.logger.debug(f"Reel JSON: checking {len(scripts)} scripts")
            
            for script in scripts:
                try:
                    content = script.inner_text(timeout=1000)
                    if len(content) < 500:
                        continue
                    
                    data = json.loads(content)
                    item = self._find_media_item(data, depth=0)
                    
                    if item:
                        result = self._parse_media_item(item)
                        if result:
                            self.logger.info(
                                f"✅ Reel JSON-FIRST: "
                                f"{result.get('like_count', 0)} likes, "
                                f"{len(result.get('tagged_accounts', []))} tags"
                            )
                            return result
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel JSON extraction error: {e}")
        return None

    def _find_media_item(self, obj, depth: int = 0) -> Optional[dict]:
        """Find media item: Post items[] or Reel edges[].node.media"""
        if depth > self.config.json_max_recursion_depth or not obj:
            return None
        if isinstance(obj, dict):
            if 'items' in obj and isinstance(obj['items'], list):
                for item in obj['items']:
                    if isinstance(item, dict) and ('pk' in item or 'media_type' in item):
                        return item
            if 'edges' in obj and isinstance(obj['edges'], list):
                for edge in obj['edges']:
                    if isinstance(edge, dict) and 'node' in edge:
                        node = edge['node']
                        if isinstance(node, dict):
                            media = node.get('media')
                            if isinstance(media, dict) and ('pk' in media or 'media_type' in media):
                                return media
                            if 'pk' in node or 'media_type' in node:
                                return node
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    r = self._find_media_item(value, depth + 1)
                    if r: return r
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    r = self._find_media_item(item, depth + 1)
                    if r: return r
        return None

    def _parse_media_item(self, item: dict) -> Optional[Dict[str, Any]]:
        """Parse media item dict into comprehensive result."""
        if not isinstance(item, dict):
            return None
        
        result = {}
        
        # Basic
        result['pk'] = str(item.get('pk', ''))
        result['shortcode'] = item.get('code', '')
        result['media_type'] = item.get('media_type', 0)
        result['product_type'] = item.get('product_type', '')
        
        # Timestamp
        taken_at = item.get('taken_at', 0)
        result['taken_at'] = taken_at
        if taken_at:
            try:
                dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
                result['taken_at_human'] = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                result['timestamp'] = dt.strftime('%b %d, %Y')
            except Exception:
                result['taken_at_human'] = ''
                result['timestamp'] = 'N/A'
        
        # Engagement
        result['like_count'] = item.get('like_count', 0)
        result['likes'] = result['like_count']
        result['comment_count'] = item.get('comment_count', 0)
        result['has_liked'] = item.get('has_liked', False)
        result['top_likers'] = item.get('top_likers', []) or []
        
        # Caption
        cap = item.get('caption')
        result['caption'] = cap.get('text', '') if isinstance(cap, dict) else ''
        
        # Location
        loc = item.get('location')
        if isinstance(loc, dict) and loc.get('name'):
            result['location'] = PostLocation(
                name=loc.get('name', ''),
                pk=str(loc.get('pk', '')),
                latitude=loc.get('lat', loc.get('latitude', 0.0)),
                longitude=loc.get('lng', loc.get('longitude', 0.0)),
                address=loc.get('address', ''),
                city=loc.get('city', '')
            )
        else:
            result['location'] = None
        
        # Owner
        user = item.get('user') or item.get('owner')
        if isinstance(user, dict):
            result['owner'] = PostOwner(
                username=user.get('username', ''),
                full_name=user.get('full_name', ''),
                pk=str(user.get('pk', '')),
                is_verified=user.get('is_verified', False),
                profile_pic_url=user.get('profile_pic_url', '')
            )
        else:
            result['owner'] = None
        
        # Dimensions
        orig = item.get('original_width', 0)
        result['width'] = orig if orig else 0
        result['height'] = item.get('original_height', 0)
        result['accessibility_caption'] = item.get('accessibility_caption', '')
        
        # Video
        result['has_audio'] = item.get('has_audio', False)
        result['video_duration'] = item.get('video_duration', 0.0)
        result['is_video'] = True
        
        # Tags
        tagged_accounts = []
        tag_positions = []
        usertags = item.get('usertags')
        if isinstance(usertags, dict) and 'in' in usertags:
            for entry in usertags['in']:
                if isinstance(entry, dict) and 'user' in entry:
                    u = entry['user']
                    if isinstance(u, dict) and 'username' in u:
                        uname = u['username']
                        if uname not in tagged_accounts:
                            tagged_accounts.append(uname)
                        pos = entry.get('position', [0, 0])
                        tag_positions.append({
                            'username': uname,
                            'x': pos[0] if isinstance(pos, list) and len(pos) > 0 else 0,
                            'y': pos[1] if isinstance(pos, list) and len(pos) > 1 else 0
                        })
        
        result['tagged_accounts'] = tagged_accounts
        result['tag_positions'] = tag_positions
        
        # Media URLs
        media_urls = []
        video_versions = item.get('video_versions', [])
        if isinstance(video_versions, list) and video_versions:
            best = max(video_versions, key=lambda v: v.get('width', 0) * v.get('height', 0))
            media_urls.append(best.get('url', ''))
        result['media_urls'] = media_urls
        
        return result

    # ==================== REEL-SPECIFIC DOM EXTRACTION METHODS ====================

    def get_likes_count(self) -> int:
        """
        Extract likes count from REEL

        Returns:
            Likes count as int
        """
        # Method 1: Reel-specific selector
        try:
            likes_span = self.page.locator(self.config.selector_reel_likes + '[role="button"]').first
            likes_text = likes_span.inner_text(timeout=self.config.reel_likes_timeout).strip()
            val = self.parse_number(likes_text)
            if val is not None:
                self.logger.debug(f"✓ Found reel likes: {val}")
                return val
        except Exception as e:
            self.logger.debug(f"Reel likes method 1 failed: {e}")

        # Method 2: General span with role=button (first one is usually likes)
        try:
            spans = self.page.locator('span[role="button"]').all()
            for span in spans[:3]:  # Check first 3
                try:
                    text = span.inner_text(timeout=self.config.visibility_timeout).strip()
                    val = self.parse_number(text)
                    if val is not None:
                         self.logger.debug(f"✓ Found reel likes (method 2): {val}")
                         return val
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 2 failed: {e}")

        # Method 3: Try any span with number-like content
        try:
            section = self.page.locator('section').first
            spans = section.locator('span').all()
            for span in spans[:self.config.reel_max_span_check]:
                try:
                    text = span.inner_text(timeout=self.config.attribute_timeout).strip()
                    # Check if it's purely numeric or has K/M notation
                    if text and len(text) < 20:  # Reasonable length for likes
                        val = self.parse_number(text)
                        if val is not None:
                            self.logger.debug(f"✓ Found reel likes (method 3): {val}")
                            return val
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 3 failed: {e}")

        self.logger.warning("Failed to extract reel likes count")
        return 0

    def get_timestamp(self) -> str:
        """
        Extract timestamp from REEL

        Reel timestamp location:
        <time class="x1p4m5qa" datetime="2025-07-23T12:34:14.000Z" title="Jul 23, 2025">July 23</time>

        Returns:
            Timestamp string
        """
        # Method 1: time.x1p4m5qa selector (reel-specific)
        try:
            time_element = self.page.locator(self.config.selector_reel_timestamp).first

            # Try title attribute first (most readable)
            title = time_element.get_attribute('title', timeout=self.config.reel_element_timeout)
            if title:
                self.logger.debug(f"✓ Found reel timestamp (title): {title}")
                return title

            # Try datetime attribute
            datetime_str = time_element.get_attribute('datetime', timeout=self.config.reel_element_timeout)
            if datetime_str:
                self.logger.debug(f"✓ Found reel timestamp (datetime): {datetime_str}")
                return datetime_str

            # Fallback to text
            text = time_element.inner_text(timeout=self.config.reel_element_timeout)
            if text:
                self.logger.debug(f"✓ Found reel timestamp (text): {text}")
                return text
        except Exception as e:
            self.logger.debug(f"Reel timestamp method 1 failed: {e}")

        # Method 2: Any time element (fallback)
        try:
            time_element = self.page.locator('time').first

            # Try title first
            title = time_element.get_attribute('title')
            if title:
                self.logger.debug(f"✓ Found reel timestamp (fallback title): {title}")
                return title

            # Try datetime
            datetime_str = time_element.get_attribute('datetime')
            if datetime_str:
                self.logger.debug(f"✓ Found reel timestamp (fallback datetime): {datetime_str}")
                return datetime_str

            # Try text
            text = time_element.inner_text()
            if text:
                self.logger.debug(f"✓ Found reel timestamp (fallback text): {text}")
                return text
        except Exception as e:
            self.logger.debug(f"Reel timestamp method 2 failed: {e}")

        self.logger.warning("Failed to extract reel timestamp")
        return 'N/A'

    def get_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from REEL via popup button

        Reel tag extraction:
        1. Find tag button: <button> with <svg aria-label="Tags">
        2. Click the button to open popup
        3. Extract href attributes from popup: href="/username/"
        4. Close popup

        Returns:
            List of usernames (without @)
        """
        tagged = []

        try:
            # Step 1: Find and click tag button
            self.logger.debug("Looking for reel tag button...")

            # Look for button with Tags SVG
            tag_button = self.page.locator(self.config.selector_tag_button).first

            # Check if button exists
            if tag_button.count() == 0:
                self.logger.debug("No tag button found - reel has no tags")
                if self.config.return_empty_list_for_no_tags:
                    return []
                return [self.config.default_no_tags_text]

            # Click the tag button
            self.logger.debug("Clicking tag button...")
            tag_button.click(timeout=self.config.tag_button_click_timeout)

            # Step 2: Wait for popup to appear
            time.sleep(self.config.ui_animation_delay)

            # Step 3: Extract tagged accounts from popup (EXCLUDE comment section!)
            self.logger.debug("Extracting tagged accounts from popup...")

            # Method 1: Links ONLY from popup container (NOT from comment section!)
            try:
                # Wait for popup content to load
                time.sleep(self.config.popup_content_load_delay)

                # CRITICAL FIX: Extract links ONLY from within popup container
                # Popup class: x1cy8zhl x9f619 x78zum5 xl56j7k x2lwn1j xeuugli x47corl
                self.logger.debug("Looking for popup container...")

                # Find popup container - look for div with these specific classes
                popup_container = self.page.locator(self.config.selector_popup_containers[0]).first

                if popup_container.count() == 0:
                    self.logger.debug("Popup container not found, trying alternative selectors...")
                    # Alternative: any div with role="dialog" or similar popup indicators
                    popup_container = self.page.locator(self.config.selector_popup_dialog).first

                # Extract links ONLY from within the popup container
                links = popup_container.locator('a[href^="/"]').all()
                self.logger.debug(f"Found {len(links)} links in popup")

                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=self.config.attribute_timeout)
                        if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                            username = href.strip('/').split('/')[-1]

                            # Filter out Instagram system paths
                            if username in self.config.instagram_system_paths:
                                continue

                            if username not in tagged:
                                tagged.append(username)
                                self.logger.debug(f"✓ Added tag: {username}")
                    except Exception:
                        continue

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags in reel: {tagged}")

                    # Close popup by clicking close button
                    try:
                        close_button = self.page.locator(self.config.selector_close_button).first
                        close_button.click(timeout=self.config.popup_close_timeout)
                        time.sleep(self.config.popup_close_delay)
                    except Exception:
                        # Try pressing Escape
                        try:
                            self.page.keyboard.press('Escape')
                            time.sleep(self.config.popup_close_delay)
                        except Exception:
                            pass

                    return tagged
            except Exception as e:
                self.logger.debug(f"Reel tag extraction from popup failed: {e}")

            # If no tags found but popup opened, close it
            try:
                self.page.keyboard.press('Escape')
            except Exception:
                pass

        except Exception as e:
            self.logger.debug(f"Reel tag button click failed: {e}")

        # Fallback: Try looking for div._aa1y (post-style tags)
        try:
            self.logger.debug("Fallback: Looking for post-style tags in reel...")
            tag_containers = self.page.locator(self.config.selector_post_tag_container).all()
            for container in tag_containers:
                try:
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href', timeout=self.config.visibility_timeout)
                    if href:
                        username = href.strip('/').split('/')[-1]
                        if username and username not in tagged:
                            tagged.append(username)
                except Exception:
                    continue

            if tagged:
                self.logger.info(f"✓ Found {len(tagged)} tags (fallback method): {tagged}")
                return tagged
        except Exception as e:
            self.logger.debug(f"Fallback tag extraction failed: {e}")

        self.logger.warning("No tags found in reel")
        if self.config.return_empty_list_for_no_tags:
            return []
        return [self.config.default_no_tags_text]
