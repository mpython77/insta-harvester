"""
Instagram Scraper - Post data extractor
Extract tags, likes, and timestamps from individual posts

PROFESSIONAL VERSION with:
- Advanced diagnostics
- Intelligent error recovery
- Performance monitoring
"""

import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import HTMLStructureChangedError
from .diagnostics import HTMLDiagnostics, run_diagnostic_mode
from .error_handler import ErrorHandler
from .performance import PerformanceMonitor


@dataclass
class PostLocation:
    """Post location data extracted from JSON"""
    name: str = ''
    pk: str = ''
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = ''
    city: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PostOwner:
    """Post owner/author data extracted from JSON"""
    username: str = ''
    full_name: str = ''
    pk: str = ''
    is_verified: bool = False
    profile_pic_url: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CarouselSlide:
    """Per-slide data for carousel posts"""
    slide_index: int = 0
    media_type: str = 'image'  # 'image' or 'video'
    width: int = 0
    height: int = 0
    tagged_accounts: List[str] = None
    tag_positions: List[Dict[str, float]] = None  # [{username, x, y}]
    image_url: str = ''
    video_url: str = ''
    video_duration: float = 0.0
    has_audio: bool = False
    accessibility_caption: str = ''

    def __post_init__(self):
        if self.tagged_accounts is None:
            self.tagged_accounts = []
        if self.tag_positions is None:
            self.tag_positions = []

    @property
    def has_tags(self) -> bool:
        return len(self.tagged_accounts) > 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PostData:
    """Post/Reel data structure — JSON-First Architecture"""
    url: str
    tagged_accounts: List[str]
    likes: str
    timestamp: str
    media_urls: List[str] = None  # Direct CDN links
    is_video: bool = False  # Is it a video/reel?
    content_type: str = 'Post'  # 'Post' or 'Reel'
    tagged_users_per_media: List[List[str]] = None  # Tags per slide

    # ── JSON-First Enriched Fields ──────────────────────────────
    caption: str = ''  # Full post caption text
    comment_count: int = 0  # Total comments
    like_count: int = 0  # Exact like count (integer)
    location: PostLocation = None  # GPS + name
    owner: PostOwner = None  # Post author info
    taken_at: int = 0  # Unix timestamp (raw)
    taken_at_human: str = ''  # Human-readable timestamp
    shortcode: str = ''  # Post shortcode (e.g. DVs7LK-iO0C)
    pk: str = ''  # Post unique ID
    media_type: int = 0  # 1=image, 2=video, 8=carousel
    product_type: str = ''  # feed, carousel_container, clips
    width: int = 0  # Original width
    height: int = 0  # Original height
    accessibility_caption: str = ''  # AI-generated image description
    top_likers: List[str] = None  # Notable accounts that liked
    has_audio: bool = False  # Has audio track
    video_duration: float = 0.0  # Video length in seconds
    carousel_media_count: int = 0  # Number of carousel slides
    carousel_slides: List[CarouselSlide] = None  # Per-slide details
    tag_positions: List[Dict[str, Any]] = None  # Tag positions on image
    has_liked: bool = False  # Current user liked this
    json_extracted: bool = False  # Whether data came from JSON

    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []
        if self.tagged_users_per_media is None:
            self.tagged_users_per_media = []
        if self.top_likers is None:
            self.top_likers = []
        if self.carousel_slides is None:
            self.carousel_slides = []
        if self.tag_positions is None:
            self.tag_positions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)



class PostDataScraper(BaseScraper):
    """
    Instagram post data scraper - PROFESSIONAL VERSION

    Features:
    - Extract tagged accounts
    - Extract likes count
    - Extract post timestamp
    - Multiple fallback methods
    - HTML structure change detection
    - Modular extraction (get only what you need)
    - Advanced diagnostics
    - Intelligent error recovery
    - Performance monitoring
    """

    def __init__(self, config: Optional[ScraperConfig] = None, enable_diagnostics: bool = True):
        """
        Initialize post data scraper

        Args:
            config: Scraper configuration
            enable_diagnostics: Enable diagnostic mode (default: True)
        """
        super().__init__(config)

        # Initialize advanced systems
        self.error_handler = ErrorHandler(self.logger)
        self.performance_monitor = PerformanceMonitor(self.logger)
        self.diagnostics = None  # Will be initialized when page is ready
        self.enable_diagnostics = enable_diagnostics
        
        # [NEW] Network interception for capturing real media URLs
        self.captured_media_urls = []  # Will store intercepted CDN URLs

        self.logger.info("✨ PostDataScraper ready (Professional Mode)")

    def _setup_network_interception(self):
        """Setup handler to capture media URLs from network requests"""
        self.captured_media_urls = []  # Reset
        
        def on_response(response):
            url = response.url
            # Capture ONLY VIDEO CDN URLs via network (images handled better by DOM)
            if any(pattern in url for pattern in ['scontent', 'cdninstagram.com', 'fbcdn.net']):
                # Only capture MP4s from network to exclude random thumbnails/avatars
                if '.mp4' in url.lower():
                    # CRITICAL: Instagram uses HLS-like segmented delivery
                    # We need to get the full video by setting bytestart=0 and removing byteend
                    import re
                    clean_url = url
                    
                    # Replace bytestart with 0, remove byteend to get full video
                    if 'bytestart=' in url:
                        clean_url = re.sub(r'bytestart=\d+', 'bytestart=0', url)
                    if 'byteend=' in url:
                        clean_url = re.sub(r'&byteend=\d+', '', clean_url)
                    
                    # Deduplicate by base URL (ignore query params for dedup)
                    base_url = clean_url.split('?')[0] if '?' in clean_url else clean_url
                    existing_bases = [u.split('?')[0] if '?' in u else u for u in self.captured_media_urls]
                    
                    if base_url not in existing_bases:
                        self.captured_media_urls.append(clean_url)
                        self.logger.debug(f"Captured video URL: {clean_url[:80]}...")
        
        try:
            self.page.on('response', on_response)
            self.logger.debug("Network interception enabled")
        except Exception as e:
            self.logger.warning(f"Failed to setup network interception: {e}")


    def _is_reel(self, url: str) -> bool:
        """Check if URL is a reel (handles both /reel/ and /reels/ patterns)"""
        return '/reel/' in url or '/reels/' in url

    def scrape(
        self,
        post_url: str,
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True,
        get_media: bool = False  # [NEW]
    ) -> PostData:
        """
        Scrape data from a single post or reel - PROFESSIONAL VERSION

        Args:
            post_url: URL of the post/reel
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract post timestamp

        Returns:
            PostData object
        """
        # [NEW] Initialize run-specific attributes
        self.tags_per_media = []
        self.detected_video_count = 0

        # ═══════ AUTO BROWSER SETUP (like ProfileScraper) ═══════
        is_shared_browser = self.page is not None and self.browser is not None
        if not is_shared_browser:
            self.logger.debug("Setting up new browser session (standalone mode)")
            session_data = self.load_session()
            self.setup_browser(session_data)

        # Start performance monitoring
        with self.performance_monitor.measure(f"scrape_{self._get_content_type(post_url)}"):
            # Detect content type
            is_reel = self._is_reel(post_url)
            content_type = 'Reel' if is_reel else 'Post'

            self.logger.info(f"🎯 Scraping {content_type}: {post_url}")

            # [NEW] Setup network interception for media capture
            if get_media:
                self._setup_network_interception()

            # Navigate to post/reel
            self.goto_url(post_url)

            # CRITICAL: Wait for content to load
            time.sleep(self.config.post_open_delay)

            # [FIXED] Strict scoping to avoid "Related Posts"
            # MUST be AFTER goto_url() — page needs content before locator queries
            self.main_scope = None
            try:
                # 1. Try Article (Standard Post View) - Best for isolating main post
                if self.page.locator('article').count() > 0:
                    self.main_scope = self.page.locator('article').first
                
                # 2. Try Dialog (Modal View)
                elif self.page.locator('div[role="dialog"]').count() > 0:
                    self.main_scope = self.page.locator('div[role="dialog"]').first

                # 3. Try Main (Fallback, but be careful)
                elif self.page.locator('main[role="main"]').count() > 0:
                    self.main_scope = self.page.locator('main[role="main"]').first

                # 4. Try Media Container (Specific for partial HTML dumps)
                elif self.page.locator('div._aa1z').count() > 0:
                    self.main_scope = self.page.locator('div._aa1z').first

                # 5. FAIL SAFE - Do NOT use self.page
                if not self.main_scope:
                    self.logger.warning("⚠️ Could not find strict post scope (article/dialog/main). Skipping full page scan to avoid noise.")
                    self.main_scope = self.page.locator('nonexistent_scope_strict_mode')
            except Exception as e:
                self.logger.debug(f"Scope determination error: {e}")
                self.main_scope = self.page.locator('nonexistent_scope_strict_mode')

            # Initialize diagnostics if page is ready
            if self.enable_diagnostics and self.diagnostics is None:
                self.diagnostics = HTMLDiagnostics(self.page, self.logger)

            # Run diagnostics to detect HTML structure changes
            if self.enable_diagnostics and self.diagnostics:
                try:
                    if is_reel:
                        report = self.diagnostics.diagnose_reel(post_url)
                    else:
                        report = self.diagnostics.diagnose_post(post_url)

                    if report.overall_status == 'FAILED':
                        self.logger.critical(
                            f"❌ CRITICAL HTML STRUCTURE CHANGE DETECTED!\n"
                            f"   {', '.join(report.recommendations)}"
                        )
                    elif report.overall_status == 'PARTIAL':
                        self.logger.warning(
                            f"⚠️ Some HTML selectors may have changed: "
                            f"{report.get_success_rate():.1f}% success rate"
                        )
                except Exception as e:
                    self.logger.debug(f"Diagnostics failed: {e}")

            # ═══════ JSON-FIRST FULL EXTRACTION ═══════
            json_data = self._extract_all_from_json()
            
            if json_data:
                # JSON extraction successful — build PostData from JSON
                tagged_accounts = json_data.get('tagged_accounts', []) if get_tags else []
                likes = json_data.get('likes', 'N/A') if get_likes else 'N/A'
                timestamp = json_data.get('timestamp', 'N/A') if get_timestamp else 'N/A'
                media_urls = json_data.get('media_urls', []) if get_media else []
                is_video = json_data.get('is_video', is_reel)
                
                data = PostData(
                    url=post_url,
                    tagged_accounts=tagged_accounts or [],
                    likes=likes,
                    timestamp=timestamp,
                    media_urls=media_urls,
                    is_video=is_video,
                    content_type=content_type,
                    tagged_users_per_media=json_data.get('tagged_users_per_media', []),
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
                    carousel_media_count=json_data.get('carousel_media_count', 0),
                    carousel_slides=json_data.get('carousel_slides', []),
                    tag_positions=json_data.get('tag_positions', []),
                    has_liked=json_data.get('has_liked', False),
                    json_extracted=True
                )
                
                self.logger.info(
                    f"✅ JSON-FIRST [{content_type}]: {len(data.tagged_accounts)} tags, "
                    f"{data.likes} likes, {data.comment_count} comments, "
                    f"📍 {data.location.name if data.location else 'N/A'}"
                )
                
                return data
            
            # ═══════ DOM FALLBACK (if JSON failed) ═══════
            self.logger.warning("⚠️ JSON extraction failed, using DOM fallback...")
            
            # Extract data based on type with error recovery
            if is_reel:
                tagged_accounts = self._extract_with_recovery(
                    self.get_reel_tagged_accounts, 'reel_tags'
                ) if get_tags else []

                likes = self._extract_with_recovery(
                    self.get_reel_likes_count, 'reel_likes', default='N/A'
                ) if get_likes else 'N/A'

                timestamp = self._extract_with_recovery(
                    self.get_reel_timestamp, 'reel_timestamp', default='N/A'
                ) if get_timestamp else 'N/A'
            else:
                tagged_accounts = self._extract_with_recovery(
                    self.get_tagged_accounts, 'post_tags'
                ) if get_tags else []

                likes = self._extract_with_recovery(
                    self.get_likes_count, 'post_likes', default='N/A'
                ) if get_likes else 'N/A'

                timestamp = self._extract_with_recovery(
                    self.get_timestamp, 'post_timestamp', default='N/A'
                ) if get_timestamp else 'N/A'

            # Extract Media URLs (Images/Videos/Carousels)
            media_urls = []
            is_video = is_reel
            if get_media:
                media_urls = self._extract_with_recovery(
                    lambda: self.get_media_urls(is_reel), 'media_urls', default=[]
                )
                if not is_reel:
                    is_video = self._is_video_post()

            data = PostData(
                url=post_url,
                tagged_accounts=tagged_accounts,
                likes=likes,
                timestamp=timestamp,
                media_urls=media_urls,
                is_video=is_video,
                content_type=content_type,
                tagged_users_per_media=self.tags_per_media
            )

            self.logger.info(
                f"✅ DOM-Extracted [{content_type}]: {len(data.tagged_accounts)} tags, "
                f"{data.likes} likes, {data.timestamp}"
            )

            return data

    def _get_content_type(self, url: str) -> str:
        """Helper to get content type from URL"""
        return 'reel' if self._is_reel(url) else 'post'

    def _is_video_post(self) -> bool:
        """Check if current post is a video (non-reels)"""
        try:
            return self.page.locator('video').count() > 0
        except Exception:
            return False

    def get_media_urls(self, is_reel: bool) -> List[str]:
        """
        Extract direct CDN URLs for images and videos.
        Uses multiple methods for maximum reliability:
        1. DOM selector fallbacks (and detects videos)
        2. Network request interception (uses detected video count)
        """
        media_urls = set()
        
        # METHOD 2: Direct selector extraction with multiple fallbacks
        # We run this FIRST to populate detected_video_count
        self.logger.info("Method 2: DOM selector extraction...")
        try:
            dom_urls = self._extract_from_dom(is_reel)
            if dom_urls:
                media_urls.update(dom_urls)
                self.logger.info(f"Found {len(dom_urls)} URLs from DOM")
            else:
                # Fallback: Try full page extraction if scoped extraction failed
                self.logger.info("Method 2b: Fallback - full page img scan...")
                fallback_urls = self._extract_from_full_page()
                if fallback_urls:
                    media_urls.update(fallback_urls)
                    self.logger.info(f"Found {len(fallback_urls)} URLs from full page fallback")
        except Exception as e:
            self.logger.debug(f"DOM extraction failed: {e}")

        # METHOD 0: Use captured network URLs (best method for videos!)
        if self.captured_media_urls:
            # Smart filtering based on content type
            if is_reel:
                # FIRST: Try to get video src directly from DOM (most reliable!)
                try:
                    video_elem = self.page.locator('video').first
                    if video_elem.count() > 0:
                        video_src = video_elem.get_attribute('src', timeout=2000)
                        if video_src and not video_src.startswith('blob:') and '.mp4' in video_src:
                            self.logger.info(f"Method 0a: Got video src directly from DOM!")
                            media_urls.add(video_src)
                            # Skip network URLs - DOM src is better
                            self.captured_media_urls = []
                except Exception as e:
                    self.logger.debug(f"Direct video src extraction failed: {e}")
                
                # Fallback to captured network URLs
                if self.captured_media_urls:
                    self.logger.info(f"Method 0: Using 1st captured video for Reel (of {len(self.captured_media_urls)})")
                    media_urls.add(self.captured_media_urls[0])
            else:
                # For posts (carousels), use the count of videos we actually encountered
                # This ensures we don't pick up background videos, but DO pick up carousel videos
                # Fallback to visible count if detected count is 0 (non-carousel matches)
                target_count = self.detected_video_count
                if target_count == 0:
                    target_count = self._count_visible_videos()
                
                if target_count > 0:
                    self.logger.info(f"Method 0: Found {target_count} detected videos, using captured URLs")
                    # Take videos chronologically
                    current_count = 0
                    for url in self.captured_media_urls:
                        if current_count < target_count:
                            media_urls.add(url)
                            current_count += 1
                else:
                    self.logger.info("Method 0: No videos detected in post, ignoring captured videos")
        
        # Filter out blob: URLs and invalid URLs
        # Instagram CDN patterns: scontent, cdninstagram.com, fbcdn.net
        valid_urls = []
        for url in media_urls:
            if not url or url.startswith('blob:') or url.startswith('data:'):
                self.logger.debug(f"Rejected URL (blob/data): {url[:60] if url else 'None'}...")
                continue
            url_lower = url.lower()
            if 'scontent' in url_lower or 'cdninstagram' in url_lower or 'fbcdn' in url_lower:
                valid_urls.append(url)
                self.logger.debug(f"Accepted URL: {url[:80]}...")
            else:
                self.logger.debug(f"Rejected URL (not CDN): {url[:80]}...")
        
        self.logger.info(f"Total valid media URLs found: {len(valid_urls)} (from {len(media_urls)} candidates)")
        return valid_urls

    def _count_visible_videos(self) -> int:
        """Count how many video elements are actually visible in the viewport"""
        count = 0
        try:
            videos = self.page.locator('video').all()
            for v in videos:
                try:
                    box = v.bounding_box()
                    if box:
                        # Check if sizable and near top (main content)
                        if box['width'] > 150 and box['y'] < 1200:
                            count += 1
                except Exception:
                    pass
        except Exception:
            pass
        return count

    def _extract_from_page_json(self) -> List[str]:
        """Extract media URLs from Instagram's embedded JSON in page"""
        urls = []
        
        try:
            # Get all script tags content
            scripts = self.page.locator('script[type="application/json"]').all()
            for script in scripts:
                try:
                    content = script.inner_text(timeout=1000)
                    urls.extend(self._parse_json_for_urls(content))
                except Exception:
                    continue
            
            # Also try inline scripts with require/define patterns
            inline_scripts = self.page.locator('script:not([src])').all()
            for script in inline_scripts[:10]:  # Limit to first 10
                try:
                    content = script.inner_text(timeout=500)
                    if 'display_url' in content or 'video_url' in content:
                        urls.extend(self._parse_json_for_urls(content))
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Script parsing error: {e}")
        
        return urls

    def _parse_json_for_urls(self, content: str) -> List[str]:
        """Parse JSON-like content for media URLs"""
        import re
        urls = []
        
        # Pattern for Instagram CDN URLs
        cdn_pattern = r'https://[^"\']+?(?:cdninstagram|fbcdn)[^"\']+?(?:\.jpg|\.mp4|\.webp)[^"\']*'
        
        matches = re.findall(cdn_pattern, content)
        for match in matches:
            # Clean up escaped unicode
            clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
            if clean_url not in urls:
                urls.append(clean_url)
        
        # Also look for display_url and video_url patterns
        display_pattern = r'"display_url"\s*:\s*"([^"]+)"'
        video_pattern = r'"video_url"\s*:\s*"([^"]+)"'
        
        for pattern in [display_pattern, video_pattern]:
            matches = re.findall(pattern, content)
            for match in matches:
                clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                if clean_url not in urls:
                    urls.append(clean_url)
        
        return urls

    def _extract_from_dom(self, is_reel: bool) -> List[str]:
        """Extract media URLs from DOM elements with multiple selector fallbacks"""
        media_urls = set()
        
        # Image selectors to try (in order of preference)
        # Updated for 2024+ Instagram HTML structure
        image_selectors = self.config.post_image_selectors
        
        # Video selectors (only for fallback, mostly handled by interceptor)
        video_selectors = self.config.post_video_selectors
        
        # Try each image selector
        for selector in image_selectors:
            try:
                # DEBUG: Log scope type
                if self.main_scope:
                    self.logger.debug(f"Searching selector '{selector}' in scope: {self.main_scope}")
                
                elements = self.main_scope.locator(selector).all() # Use main_scope
                self.logger.debug(f"Selector '{selector}' found {len(elements)} elements")
                
                for i, elem in enumerate(elements):
                    try:
                        # [NEW] Size and Viewport Filter
                        box = elem.bounding_box()
                        if not box:
                            self.logger.debug(f"  Element {i}: No bounding box")
                            continue
                            
                        # Ignore small images (avatars, icons)
                        if box['width'] < 150 or box['height'] < 150:
                            self.logger.debug(f"  Element {i}: Too small ({box['width']}x{box['height']})")
                            continue
                            
                        # Ignore images far below (recommendations)
                        # Relaxed to 2000px to be safe
                        if box['y'] > 2000:
                            self.logger.debug(f"  Element {i}: Too far down (y={box['y']})")
                            continue

                        # Skip profile pictures explicitly
                        alt = elem.get_attribute('alt') or ''
                        if 'profile picture' in alt.lower():
                            self.logger.debug(f"  Element {i}: Profile picture ignored")
                            continue
                        
                        # Get srcset (best quality)
                        srcset = elem.get_attribute('srcset')
                        if srcset:
                            # Parse srcset to get largest image
                            parts = srcset.split(',')
                            if parts:
                                # Last one is usually largest
                                last = parts[-1].strip().split(' ')[0]
                                if last and not last.startswith('blob:'):
                                    media_urls.add(last)
                                    self.logger.debug(f"  Element {i}: Added via srcset")
                                    continue
                        
                        # Fallback to src
                        src = elem.get_attribute('src')
                        if src and not src.startswith('blob:') and not src.startswith('data:'):
                            media_urls.add(src)
                            self.logger.debug(f"  Element {i}: Added via src")
                        else:
                            self.logger.debug(f"  Element {i}: No valid src or srcset")
                            
                    except Exception as e:
                        self.logger.debug(f"  Element {i} error: {e}")
                        continue
            except Exception as e:
                self.logger.debug(f"Selector '{selector}' error: {e}")
                continue
        
        # Try video selectors (only poster)
        for selector in video_selectors:
            try:
                # Use Scoped Search
                elements = self.main_scope.locator(selector).all()
                for elem in elements:
                    try:
                        # [NEW] Size filter for posters too
                        box = elem.bounding_box()
                        if not box or box['width'] < 150:
                            continue
                        
                        # Note: We do NOT increment detected_video_count here for Posts
                        # because _extract_carousel_media handles counting videos in slides.
                        # For Reels, we hardcode to take 1 video anyway.

                        poster = elem.get_attribute('poster')
                        if poster and not poster.startswith('blob:'):
                            media_urls.add(poster)
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Handle carousel navigation
        if not is_reel:
            carousel_urls = self._extract_carousel_media()
            media_urls.update(carousel_urls)
        else:
            # For single image/video posts (non-carousel, non-reel)
            # If it's not a reel and no carousel was detected, it's a single post.
            # We need to extract tags for this single media item.
            if not self.main_scope.locator('button[aria-label="Next"]').count() > 0:
                single_tags = self._extract_tagged_users(self.main_scope)
                if single_tags:
                    self.tags_per_media.append(single_tags)
                else:
                    self.tags_per_media.append([]) # Placeholder for single media item

        # Log what we found
        self.logger.debug(f"DOM extraction complete: {len(media_urls)} raw URLs found")
        for url in list(media_urls)[:3]:  # Log first 3 for debugging
            self.logger.debug(f"  Raw URL sample: {url[:80]}...")
            
        return list(media_urls)

    def _extract_from_full_page(self) -> List[str]:
        """
        Fallback: Extract media URLs from the full page.
        IMPORTANT: Only extracts from MAIN post content, NOT from "More posts from" section.
        Uses Y-position filtering to exclude recommendation thumbnails.
        For carousels: Clicks through all slides to load lazy-loaded images.
        """
        media_urls = set()
        
        try:
            # Method 1: Try to find carousel container first (multi-image posts)
            # Instagram uses ul._acay for carousel slides
            carousel = self.page.locator(self.config.carousel_selectors['container'])
            if carousel.count() > 0:
                self.logger.debug("Fallback: Found carousel container (ul._acay)")
                
                # First, collect images from current view
                def collect_carousel_images():
                    imgs = carousel.locator('img').all()
                    for img in imgs:
                        try:
                            src = img.get_attribute('src') or ''
                            srcset = img.get_attribute('srcset') or ''
                            alt = img.get_attribute('alt') or ''
                            
                            if 'profile picture' in alt.lower():
                                continue
                            
                            url_to_check = src
                            if srcset:
                                parts = srcset.split(',')
                                if parts:
                                    url_to_check = parts[-1].strip().split(' ')[0]
                            
                            if url_to_check and not url_to_check.startswith(('blob:', 'data:')):
                                url_lower = url_to_check.lower()
                                if 'scontent' in url_lower or 'cdninstagram' in url_lower or 'fbcdn' in url_lower:
                                    media_urls.add(url_to_check)
                        except Exception:
                            continue
                
                # Collect initial images
                collect_carousel_images()
                initial_count = len(media_urls)
                self.logger.debug(f"Initial carousel images: {initial_count}")
                
                # Click through carousel to load all slides (Instagram lazy-loads them)
                next_btn = self.page.locator(self.config.carousel_selectors['next_button'])
                max_clicks = 50  # Increased from 10 to 50 for large carousels
                clicks = 0
                
                while next_btn.count() > 0 and clicks < max_clicks:
                    try:
                        if next_btn.first.is_visible(timeout=1000):
                            next_btn.first.click()
                            self.page.wait_for_timeout(300)  # Wait for slide animation
                            collect_carousel_images()
                            clicks += 1
                            self.logger.debug(f"Carousel click {clicks}: {len(media_urls)} total images")
                        else:
                            break
                    except Exception:
                        break
                
                if media_urls:
                    self.logger.info(f"Full page fallback found: {len(media_urls)} CDN images from carousel")
                    return list(media_urls)
            
            # Method 2: Single/no carousel - find FIRST large main post image ONLY
            # For non-carousel posts, there should be exactly ONE main image
            # Strategy: Get first _aagv image that's large and in upper viewport
            self.logger.debug("Fallback: Searching for FIRST main post image (_aagv)")
            
            all_imgs = self.page.locator('div._aagv img').all()
            self.logger.debug(f"Found {len(all_imgs)} total _aagv images on page")
            
            for i, img in enumerate(all_imgs):
                try:
                    # Get bounding box for Y-position check
                    box = img.bounding_box()
                    if not box:
                        continue
                    
                    # CRITICAL: Main post image should be at the TOP (y < 600)
                    # Recommendation thumbnails are always below
                    if box['y'] > 600:
                        self.logger.debug(f"Skipping img {i}: y={box['y']:.0f} (below main content)")
                        continue
                    
                    # Size check - main post images are large (at least 300x300)
                    if box['width'] < 300 or box['height'] < 300:
                        self.logger.debug(f"Skipping img {i}: too small ({box['width']:.0f}x{box['height']:.0f})")
                        continue
                    
                    src = img.get_attribute('src') or ''
                    srcset = img.get_attribute('srcset') or ''
                    alt = img.get_attribute('alt') or ''
                    
                    if 'profile picture' in alt.lower():
                        continue
                    
                    url_to_check = src
                    if srcset:
                        parts = srcset.split(',')
                        if parts:
                            url_to_check = parts[-1].strip().split(' ')[0]
                    
                    if url_to_check and not url_to_check.startswith(('blob:', 'data:')):
                        url_lower = url_to_check.lower()
                        if 'scontent' in url_lower or 'cdninstagram' in url_lower or 'fbcdn' in url_lower:
                            media_urls.add(url_to_check)
                            self.logger.debug(f"Main post img (y={box['y']:.0f}): {url_to_check[:50]}...")
                            # For single-image posts, we only want ONE image
                            # Break after finding the first valid main post image
                            self.logger.info(f"Full page fallback found: 1 CDN image (single post)")
                            return list(media_urls)
                except Exception as e:
                    self.logger.debug(f"Error processing img {i}: {e}")
                    continue
                        
        except Exception as e:
            self.logger.debug(f"Full page extraction error: {e}")
        
        self.logger.info(f"Full page fallback found: {len(media_urls)} CDN images")
        return list(media_urls)

    def _extract_tagged_users(self, container) -> List[str]:
        """[NEW] Helper to extract tagged users from a slide/post container"""
        tags = []
        try:
            # 1. Look for Tag Button (user icon) and Click it
            # Using ari-labels from user's provided HTML
            tag_btn = container.locator(self.config.tagged_user_selectors['tag_button']).first
            
            if tag_btn.is_visible(timeout=500):
                try:
                    tag_btn.click(timeout=300)
                    self.page.wait_for_timeout(200) # Wait for bubbles to appear
                except Exception:
                    pass

            # 2. Extract Tag Bubbles (links to users)
            # They are typically direct child links styled as bubbles
            # We filter for valid usernames
            links = container.locator(self.config.tagged_user_selectors['tag_link']).all()
            for link in links:
                try:
                    # Ignore non-visible links (e.g. caption links if container is broad)
                    if not link.is_visible(): continue
                    
                    href = link.get_attribute('href')
                    if not href: continue
                    
                    user = href.strip('/')
                    # Filter out system paths
                    ignore_list = set(self.config.tagged_user_selectors['ignored_users'])
                    if user in ignore_list or '/' in user:
                        continue
                        
                    # Basic check: tag bubbles usually don't have much text besides the name? 
                    # Or we just accept all specific user links in the slide area.
                    if user not in tags:
                        tags.append(user)
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Error extracting tagged users: {e}")
        return tags

    def _extract_carousel_media(self) -> List[str]:
        """
        Handle carousel posts (multiple slides) using Next button.
        Iteratively collects media and TAGS from each slide.
        """
        media_urls = []
        
        # Use our scoped main container to find the carousel
        # Instagram carousel usually has a ul._acay or similar
        carousel_container = self.main_scope.locator(self.config.carousel_selectors['container']).first
        
        try:
            # We will try to click "Next" button until it disappears
            # Instagram carousel next button usually has aria-label="Next"
            next_btn = self.main_scope.locator(self.config.carousel_selectors['next_button']).first
            
            # Max slides safety limit (increased for larger carousels)
            for i in range(50): 
                self.page.wait_for_timeout(500) # Wait for slide animation/load
                
                # 1. Find the ACTIVE slide
                # In standard IG HTML, slides are 'li'. The active one is visible.
                # We search inside our determined scope
                
                # Extract media from CURRENT view (works for both image and video)
                # Video check
                video = self.main_scope.locator('video').first # Only visible video
                if video.count() > 0 and video.is_visible():
                     # It's a video slide
                     # We assume video URL is captured by network, but we track the tag
                     # Videos usually don't have tagged users, but we check anyway
                     # Increment global detected video count
                     self.detected_video_count += 1
                     self.tags_per_media.append([]) # Videos rarely have tags in this way
                else:
                    # It's an image slide
                    # Find the main image in current view
                    images = self.main_scope.locator('img').all()
                    
                    # Simple heuristic: largest visible image in main scope is the slide
                    best_img = None
                    max_width = 0
                    for img in images:
                        try:
                            box = img.bounding_box()
                            if box and box['width'] > 200 and box['y'] > 0 and box['y'] < 1000:
                                if box['width'] > max_width:
                                    max_width = box['width']
                                    best_img = img
                        except Exception:
                            continue
                    
                    if best_img:
                        src = best_img.get_attribute('src')
                        if src: media_urls.append(src)
                        
                        # [NEW] Extract Tags for this slide
                        # We pass the parent (likely the slide li) or just scope search
                        # Since we are "on" the slide, the tag button should be visible in Main Scope
                        current_tags = self._extract_tagged_users(self.main_scope)
                        self.tags_per_media.append(current_tags)
                    else:
                        self.tags_per_media.append([]) # Placeholder if no image found
                
                # 2. Click NEXT
                if next_btn.is_visible():
                    next_btn.click()
                else:
                    break # End of carousel
                    
        except Exception as e:
            self.logger.debug(f"Carousel extraction error: {e}")
            
        return media_urls



    def _extract_with_recovery(self, extractor_func, element_name: str, default: Any = None):
        """
        Extract with intelligent error recovery

        Args:
            extractor_func: Extraction function
            element_name: Name for logging
            default: Default value if extraction fails

        Returns:
            Extracted value or default
        """
        return self.error_handler.safe_extract(
            extractor=extractor_func,
            element_name=element_name,
            default=default if default is not None else []
        )

    def scrape_multiple(
        self,
        post_urls: List[str],
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True,
        delay_between_posts: bool = True
    ) -> List[PostData]:
        """
        Scrape multiple posts sequentially - PROFESSIONAL VERSION

        Args:
            post_urls: List of post URLs
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract post timestamp
            delay_between_posts: Add delay between posts (rate limiting)

        Returns:
            List of PostData objects
        """
        self.logger.info(f"📦 Scraping {len(post_urls)} posts/reels...")
        self.performance_monitor.log_system_info()

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
            for i, url in enumerate(post_urls, 1):
                content_type = 'Reel' if self._is_reel(url) else 'Post'
                self.logger.info(f"[{i}/{len(post_urls)}] Processing [{content_type}]: {url}")

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
                    results.append(PostData(
                        url=url,
                        tagged_accounts=[],
                        likes='ERROR',
                        timestamp='N/A',
                        content_type=content_type
                    ))

                # Check memory usage and optimize if needed
                if i % self.config.memory_check_interval == 0:
                    if not self.performance_monitor.check_memory_threshold(self.config.memory_threshold_mb):
                        self.performance_monitor.optimize_memory()

                # Delay between posts (rate limiting)
                if delay_between_posts and i < len(post_urls):
                    delay = random.uniform(
                        self.config.post_scrape_delay_min,
                        self.config.post_scrape_delay_max
                    )
                    self.logger.debug(f"⏱️ Waiting {delay:.1f}s...")
                    time.sleep(delay)

            # Print final statistics
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.likes != 'ERROR')
            posts_count = sum(1 for r in results if r.content_type == 'Post' and r.likes != 'ERROR')
            reels_count = sum(1 for r in results if r.content_type == 'Reel' and r.likes != 'ERROR')

            self.logger.info(
                f"\n{'='*70}\n"
                f"📊 SCRAPING COMPLETE - STATISTICS\n"
                f"{'='*70}\n"
                f"Total URLs: {len(post_urls)}\n"
                f"Successfully scraped: {success_count}/{len(post_urls)} "
                f"({(success_count/len(post_urls)*100):.1f}%)\n"
                f"  - Posts: {posts_count}\n"
                f"  - Reels: {reels_count}\n"
                f"Failed: {len(post_urls) - success_count}\n"
                f"Total time: {total_time:.2f}s\n"
                f"Average time per item: {total_time/len(post_urls):.2f}s\n"
                f"{'='*70}"
            )

            # Print performance report
            self.performance_monitor.print_report()

            # Print error statistics
            self.error_handler.print_stats()

            return results

        finally:
            self.close()

    # ==================== JSON-FIRST TAG EXTRACTION ====================

    def _extract_tags_from_json(self) -> tuple:
        """Backward compatible: Extract just tags from JSON."""
        result = self._extract_all_from_json()
        if result and result.get('tagged_accounts'):
            return result['tagged_accounts'], result.get('tagged_users_per_media', [])
        return [], []

    # ==================== JSON-FIRST FULL EXTRACTION ====================

    def _extract_all_from_json(self) -> Optional[Dict[str, Any]]:
        """
        JSON-FIRST: Extract ALL available data from embedded JSON scripts.
        
        Instagram pre-loads full post data in <script type="application/json">.
        Path: xdt_api__v1__media__shortcode__web_info.items[0]
        
        Returns dict with ALL extracted fields, or None if not found.
        """
        import json
        from datetime import datetime, timezone
        
        try:
            scripts = self.page.locator('script[type="application/json"]').all()
            self.logger.debug(f"JSON full extraction: checking {len(scripts)} scripts")
            
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
                                f"✅ JSON-FIRST: Extracted full data "
                                f"({result.get('like_count', 0)} likes, "
                                f"{result.get('comment_count', 0)} comments, "
                                f"{len(result.get('tagged_accounts', []))} tags)"
                            )
                            return result
                        
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"JSON full extraction error: {e}")
        
        return None

    def _find_media_item(self, obj, depth: int = 0) -> Optional[dict]:
        """
        Recursively find the media item object in JSON.
        
        Handles two Instagram JSON structures:
        - Posts: xdt_api__v1__media__shortcode__web_info.items[0]  
        - Reels: xdt_api__v1__clips__home__connection_v2.edges[0].node.media
        """
        if depth > self.config.json_max_recursion_depth or not obj:
            return None
        
        if isinstance(obj, dict):
            # Pattern 1: Post — items[] array with media objects
            if 'items' in obj and isinstance(obj['items'], list):
                for item in obj['items']:
                    if isinstance(item, dict) and ('pk' in item or 'media_type' in item):
                        return item
            
            # Pattern 2: Reel — edges[].node.media structure
            if 'edges' in obj and isinstance(obj['edges'], list):
                for edge in obj['edges']:
                    if isinstance(edge, dict) and 'node' in edge:
                        node = edge['node']
                        if isinstance(node, dict):
                            # Try node.media first
                            media = node.get('media')
                            if isinstance(media, dict) and ('pk' in media or 'media_type' in media):
                                return media
                            # Or node itself might be the media
                            if 'pk' in node or 'media_type' in node:
                                return node
            
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    result = self._find_media_item(value, depth + 1)
                    if result:
                        return result
        
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    result = self._find_media_item(item, depth + 1)
                    if result:
                        return result
        
        return None

    def _parse_media_item(self, item: dict) -> Optional[Dict[str, Any]]:
        """Parse a media item dict into comprehensive result"""
        from datetime import datetime, timezone
        
        if not isinstance(item, dict):
            return None
        
        result = {}
        
        # ── Basic Info ──
        result['pk'] = str(item.get('pk', ''))
        result['shortcode'] = item.get('code', '')
        result['media_type'] = item.get('media_type', 0)
        result['product_type'] = item.get('product_type', '')
        
        # ── Timestamp ──
        taken_at = item.get('taken_at', 0)
        result['taken_at'] = taken_at
        if taken_at:
            try:
                dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
                result['taken_at_human'] = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                result['timestamp'] = dt.strftime('%b %d, %Y')
            except Exception:
                result['taken_at_human'] = ''
                result['timestamp'] = ''
        
        # ── Engagement ──
        result['like_count'] = item.get('like_count', 0)
        result['likes'] = str(result['like_count'])
        result['comment_count'] = item.get('comment_count', 0)
        result['has_liked'] = item.get('has_liked', False)
        result['top_likers'] = item.get('top_likers', []) or []
        
        # ── Caption ──
        caption_obj = item.get('caption')
        if isinstance(caption_obj, dict):
            result['caption'] = caption_obj.get('text', '')
        elif isinstance(caption_obj, str):
            result['caption'] = caption_obj
        else:
            result['caption'] = ''
        
        # ── Location ──
        loc = item.get('location')
        if isinstance(loc, dict):
            result['location'] = PostLocation(
                name=loc.get('name', ''),
                pk=str(loc.get('pk', '')),
                latitude=loc.get('lat', 0.0) or 0.0,
                longitude=loc.get('lng', 0.0) or 0.0,
                address=loc.get('address', ''),
                city=loc.get('city', '')
            )
        else:
            result['location'] = None
        
        # ── Owner / User ──
        user = item.get('user')
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
        
        # ── Dimensions ──
        result['width'] = item.get('original_width', 0)
        result['height'] = item.get('original_height', 0)
        result['accessibility_caption'] = item.get('accessibility_caption', '')
        
        # ── Video fields ──
        result['video_duration'] = item.get('video_duration', 0.0) or 0.0
        result['has_audio'] = item.get('has_audio', False)
        result['is_video'] = item.get('media_type', 0) == 2
        
        # ── Tags (single post) ──
        tagged_accounts = []
        tag_positions = []
        per_slide_tags = []
        
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
        
        # ── Carousel ──
        carousel_media = item.get('carousel_media', [])
        carousel_slides = []
        result['carousel_media_count'] = item.get('carousel_media_count', 0)
        
        if isinstance(carousel_media, list) and carousel_media:
            for i, slide in enumerate(carousel_media):
                if not isinstance(slide, dict):
                    continue
                
                # Slide tags
                slide_tags = []
                slide_tag_positions = []
                slide_usertags = slide.get('usertags')
                if isinstance(slide_usertags, dict) and 'in' in slide_usertags:
                    for entry in slide_usertags['in']:
                        if isinstance(entry, dict) and 'user' in entry:
                            u = entry['user']
                            if isinstance(u, dict) and 'username' in u:
                                uname = u['username']
                                slide_tags.append(uname)
                                if uname not in tagged_accounts:
                                    tagged_accounts.append(uname)
                                pos = entry.get('position', [0, 0])
                                slide_tag_positions.append({
                                    'username': uname,
                                    'x': pos[0] if isinstance(pos, list) and len(pos) > 0 else 0,
                                    'y': pos[1] if isinstance(pos, list) and len(pos) > 1 else 0
                                })
                
                per_slide_tags.append(slide_tags)
                
                # Slide media type
                s_media_type = slide.get('media_type', 1)
                s_type_str = 'video' if s_media_type == 2 else 'image'
                
                # Slide image URL
                s_image_url = ''
                img_versions = slide.get('image_versions2', {})
                if isinstance(img_versions, dict):
                    candidates = img_versions.get('candidates', [])
                    if isinstance(candidates, list) and candidates:
                        s_image_url = candidates[0].get('url', '')
                
                # Slide video URL
                s_video_url = ''
                vid_versions = slide.get('video_versions', [])
                if isinstance(vid_versions, list) and vid_versions:
                    s_video_url = vid_versions[0].get('url', '')
                
                carousel_slides.append(CarouselSlide(
                    slide_index=i,
                    media_type=s_type_str,
                    width=slide.get('original_width', 0),
                    height=slide.get('original_height', 0),
                    tagged_accounts=slide_tags,
                    tag_positions=slide_tag_positions,
                    image_url=s_image_url,
                    video_url=s_video_url,
                    video_duration=slide.get('video_duration', 0.0) or 0.0,
                    has_audio=slide.get('has_audio', False),
                    accessibility_caption=slide.get('accessibility_caption', '')
                ))
        
        # ── Image / Video URLs (single post) ──
        media_urls = []
        img_versions = item.get('image_versions2', {})
        if isinstance(img_versions, dict):
            candidates = img_versions.get('candidates', [])
            if isinstance(candidates, list) and candidates:
                media_urls.append(candidates[0].get('url', ''))
        
        vid_versions = item.get('video_versions', [])
        if isinstance(vid_versions, list) and vid_versions:
            media_urls.append(vid_versions[0].get('url', ''))
        
        result['tagged_accounts'] = tagged_accounts
        result['tag_positions'] = tag_positions
        result['tagged_users_per_media'] = per_slide_tags
        result['carousel_slides'] = carousel_slides
        result['media_urls'] = media_urls
        result['json_extracted'] = True
        
        return result



    def get_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from posts (handles both IMAGE and VIDEO posts)

        Instagram tag structure:
        - IMAGE posts: Tags in <div class="_aa1y"> containers
        - VIDEO posts: Tags in popup (click button, then extract from popup)

        Returns:
            List of usernames (without @)
        """
        tagged = []

        # STEP 0: JSON-FIRST extraction (fastest, no clicks needed)
        try:
            json_tags, json_per_slide = self._extract_tags_from_json()
            if json_tags:
                # Also populate tags_per_media for carousel support
                if json_per_slide:
                    self.tags_per_media = json_per_slide
                self.logger.info(f"✅ JSON-FIRST tags: {json_tags}")
                return json_tags
        except Exception as e:
            self.logger.debug(f"JSON-first failed, falling back to DOM: {e}")

        # STEP 0.5: Check if this post has tags (look for Tags SVG)
        try:
            has_tags = self.page.locator(self.config.selector_tag_button.replace('button:has(', '').replace(')', '')).count() > 0
            if not has_tags:
                self.logger.debug("No tag icon found - post has no tags")
                return [self.config.default_no_tags_text]
        except Exception:
            pass

        # STEP 1: Detect if this is a VIDEO post or IMAGE post
        is_video_post = False
        try:
            # Check for video element
            video_count = self.page.locator('video').count()
            if video_count > 0:
                is_video_post = True
                self.logger.debug("Detected VIDEO post")
            else:
                self.logger.debug("Detected IMAGE post")
        except Exception:
            pass

        # STEP 2: If VIDEO post, use POPUP extraction (like reels)
        if is_video_post:
            self.logger.debug("Using VIDEO post tag extraction (popup method)...")
            try:
                # Find and click tag button
                tag_button = self.page.locator(self.config.selector_tag_button).first

                if tag_button.count() == 0:
                    self.logger.debug("No tag button found")
                    return [self.config.default_no_tags_text]

                # Click the tag button
                self.logger.debug("Clicking tag button...")
                tag_button.click(timeout=self.config.tag_button_click_timeout)
                time.sleep(self.config.popup_animation_delay)
                time.sleep(self.config.popup_content_load_delay)

                # CRITICAL: Extract from popup container ONLY
                self.logger.debug("Extracting tags from popup...")
                popup_container = self.page.locator(self.config.selector_popup_containers[0]).first

                if popup_container.count() == 0:
                    # Fallback: Try role="dialog"
                    popup_container = self.page.locator(self.config.selector_popup_dialog).first

                if popup_container.count() > 0:
                    # Extract links ONLY from popup
                    popup_links = popup_container.locator('a[href^="/"]').all()

                    for link in popup_links:
                        try:
                            href = link.get_attribute('href', timeout=1000)
                            if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                                username = href.strip('/').split('/')[-1]

                                # Filter out system paths
                                if username in self.config.instagram_system_paths:
                                    continue

                                if username and username not in tagged:
                                    tagged.append(username)
                                    self.logger.debug(f"✓ Found tag: {username}")
                        except Exception:
                            continue

                    # Close popup
                    try:
                        close_button = self.page.locator(self.config.selector_close_button).first
                        close_button.click(timeout=self.config.popup_close_timeout)
                    except Exception:
                        self.page.keyboard.press('Escape')

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags (VIDEO popup): {tagged}")
                    return tagged

            except Exception as e:
                self.logger.warning(f"VIDEO post popup extraction failed: {e}")
                # Try closing popup
                try:
                    self.page.keyboard.press('Escape')
                except Exception:
                    pass

        # STEP 3: If IMAGE post (or video extraction failed), use div._aa1y extraction
        self.logger.debug("Using IMAGE post tag extraction (div._aa1y method)...")
        try:
            # Find all tag containers
            tag_containers = self.page.locator(self.config.selector_post_tag_container).all()
            self.logger.debug(f"Found {len(tag_containers)} {self.config.selector_post_tag_container} tag containers")

            for container in tag_containers:
                try:
                    # Get the link inside this container
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href', timeout=self.config.attribute_timeout)

                    if href:
                        # Extract username from href="/username/"
                        username = href.strip('/').split('/')[-1]

                        # Filter out system paths
                        if username in self.config.instagram_system_paths:
                            continue

                        if username and username not in tagged:
                            tagged.append(username)
                            self.logger.debug(f"✓ Found tag: {username}")
                except Exception:
                    continue

            if tagged:
                self.logger.info(f"✓ Found {len(tagged)} tags (IMAGE): {tagged}")
                return tagged

        except Exception as e:
            self.logger.warning(f"Tag extraction from div._aa1y failed: {e}")

        # FALLBACK: BeautifulSoup method
        try:
            from bs4 import BeautifulSoup
            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            tag_containers = soup.find_all('div', class_='_aa1y')
            self.logger.debug(f"BS4: Found {len(tag_containers)} div._aa1y containers")

            for container in tag_containers:
                link = container.find('a', href=True)
                if link and link.get('href'):
                    href = link['href']
                    username = href.strip('/').split('/')[-1]

                    # Filter out system paths
                    if username in self.config.instagram_system_paths:
                        continue

                    if username and username not in tagged:
                        tagged.append(username)

            if tagged:
                self.logger.info(f"✓ Found {len(tagged)} tags (BS4 method): {tagged}")
                return tagged

        except Exception as e:
            self.logger.warning(f"BS4 tag extraction failed: {e}")

        # No tags found
        self.logger.warning("⚠️ No tags found in this post")
        return [self.config.default_no_tags_text]

    def get_likes_count(self) -> str:
        """
        Extract likes count with multiple fallback methods

        Returns:
            Likes count as string
        """
        # Method 1: span[role="button"] after Like SVG (new structure)
        try:
            section = self.page.locator('section').first
            spans = section.locator('span[role="button"]').all()

            for span in spans[:2]:  # First 2 spans (likes and comments)
                try:
                    text = span.inner_text(timeout=self.config.visibility_timeout).strip()
                    # Check if it's a number
                    if text and text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit():
                        self.logger.debug(f"✓ Found likes (method 1): {text}")
                        return text.replace(',', '')
                    # Handle K/M notation
                    if text and ('K' in text or 'M' in text):
                        self.logger.debug(f"✓ Found likes (method 1): {text}")
                        return text
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Method 1 failed: {e}")

        # Method 2: Try all configured selectors in priority order
        for selector_idx, selector in enumerate(self.config.selector_likes_options):
            try:
                section = self.page.locator('section').first
                likes_span = section.locator(selector).first
                likes_text = likes_span.inner_text(timeout=self.config.visibility_timeout).strip()
                # Handle numeric format
                if likes_text and likes_text.replace(',', '').replace('.', '').isdigit():
                    self.logger.debug(f"✓ Found likes (method 2, selector {selector_idx}): {likes_text}")
                    return likes_text.replace(',', '')
                # Handle K/M notation (e.g., "149.2K", "1.5M")
                if likes_text and ('K' in likes_text or 'M' in likes_text):
                    self.logger.debug(f"✓ Found likes (method 2, selector {selector_idx}): {likes_text}")
                    return likes_text
            except Exception as e:
                self.logger.debug(f"Method 2 selector {selector_idx} failed: {e}")
                continue

        # Method 3: Link-based (old structure)
        try:
            likes_link = self.page.locator('a[href*="/liked_by/"]').first
            likes_text = likes_link.locator(self.config.selector_html_span).first.inner_text(timeout=self.config.visibility_timeout)
            if likes_text.replace(',', '').isdigit():
                self.logger.debug(f"✓ Found likes (method 3): {likes_text}")
                return likes_text.strip().replace(',', '')
        except Exception as e:
            self.logger.debug(f"Method 3 failed: {e}")

        # Method 4: Text-based search
        try:
            likes_count = self.page.locator('span:has-text("likes")').count()
            for i in range(likes_count):
                try:
                    span = self.page.locator('span:has-text("likes")').nth(i)
                    number = span.locator(self.config.selector_html_span).first
                    text = number.inner_text(timeout=self.config.visibility_timeout)
                    if text.replace(',', '').isdigit():
                        self.logger.debug(f"✓ Found likes (method 4): {text}")
                        return text.strip().replace(',', '')
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Method 4 failed: {e}")

        self.logger.warning("All methods failed to extract likes count")
        return 'N/A'

    def get_timestamp(self) -> str:
        """
        Extract post timestamp

        Returns:
            Timestamp string (e.g., "Nov 17, 2025")
        """
        selector = 'time'

        def extract():
            time_element = self.page.locator(selector).first

            # Try title attribute first (human-readable)
            title = time_element.get_attribute('title')
            if title:
                return title

            # Try datetime attribute
            datetime_str = time_element.get_attribute('datetime')
            if datetime_str:
                return datetime_str

            # Fallback to inner text
            return time_element.inner_text()

        result = self.safe_extract(
            extract,
            element_name='timestamp',
            selector=selector,
            default='N/A'
        )

        return result

    # ==================== REEL-SPECIFIC EXTRACTION METHODS ====================

    def get_reel_likes_count(self) -> str:
        """
        Extract likes count from REEL (different HTML structure than posts)

        Reel likes location (from reels.html analysis):
        - Near svg[aria-label="Like"] in the button container
        - Inside span.html-span element

        Returns:
            Likes count as string
        """
        # Method 1: Use diagnostics selector from config (most reliable)
        try:
            likes_selector = self.config.diagnostics_reel_selectors.get('likes', '')
            if likes_selector:
                likes_elem = self.page.locator(likes_selector).first
                if likes_elem.count() > 0:
                    likes_text = likes_elem.inner_text(timeout=self.config.reel_likes_timeout).strip()
                    if likes_text and likes_text.replace(',', '').replace('K', '').replace('M', '').replace('.', '').isdigit():
                        self.logger.debug(f"✓ Found reel likes (config selector): {likes_text}")
                        return likes_text.replace(',', '')
        except Exception as e:
            self.logger.debug(f"Reel likes config selector failed: {e}")

        # Method 2: Find Like SVG's parent button and look for number in siblings
        try:
            like_container = self.page.locator('div:has(> span > svg[aria-label="Like"])').first
            if like_container.count() > 0:
                # Look for span with number in nearby elements
                spans = like_container.locator('span.html-span, span.x1hl2dhg, span.x1vvkbs').all()
                for span in spans[:5]:
                    try:
                        text = span.inner_text(timeout=500).strip()
                        if text and (text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit() or 'K' in text or 'M' in text):
                            self.logger.debug(f"✓ Found reel likes (method 2): {text}")
                            return text.replace(',', '')
                    except Exception:
                        continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 2 failed: {e}")

        # Method 3: Fallback - look for role="button" with number near Like button
        try:
            buttons = self.page.locator('div[role="button"]').all()
            for btn in buttons[:10]:
                try:
                    # Skip if it doesn't have Like/Comment SVG nearby
                    html = btn.inner_html(timeout=500)
                    if 'aria-label="Like"' not in html and 'x1lliihq' in html:
                        text = btn.inner_text(timeout=500).strip()
                        if text and len(text) < 10 and (text.replace(',', '').replace('K', '').replace('M', '').replace('.', '').isdigit() or 'K' in text or 'M' in text):
                            self.logger.debug(f"✓ Found reel likes (method 3): {text}")
                            return text.replace(',', '')
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 3 failed: {e}")

        self.logger.warning("Failed to extract reel likes count")
        return 'N/A'

    def get_reel_timestamp(self) -> str:
        """
        Extract timestamp from REEL
        
        NOTE: Instagram Reels typically DON'T show timestamps on the page.
        This method uses quick timeouts to avoid wasting time.

        Returns:
            Timestamp string or 'N/A'
        """
        # Quick check - Reels rarely have time elements, use short timeout
        quick_timeout = 1000  # 1 second max
        
        # Method 1: Check for time element quickly
        try:
            time_element = self.page.locator('time').first
            if time_element.count() > 0:
                # Element exists, try to get attributes
                title = time_element.get_attribute('title', timeout=quick_timeout)
                if title:
                    self.logger.debug(f"✓ Found reel timestamp: {title}")
                    return title
                    
                datetime_str = time_element.get_attribute('datetime', timeout=quick_timeout)
                if datetime_str:
                    self.logger.debug(f"✓ Found reel timestamp (datetime): {datetime_str}")
                    return datetime_str
        except Exception as e:
            self.logger.debug(f"No timestamp element found (expected for Reels)")

        # Reels don't have timestamps - return N/A immediately
        self.logger.warning("Failed to extract reel timestamp")
        return 'N/A'

    def get_reel_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from REEL (different logic than posts)

        Reel tag extraction:
        1. Find tag button: <button> with <svg aria-label="Tags">
        2. Click the button to open popup
        3. Extract href attributes from popup: href="/username/"

        Returns:
            List of usernames (without @)
        """
        tagged = []

        # STEP 0: JSON-FIRST extraction (works for reels too!)
        try:
            json_tags, _ = self._extract_tags_from_json()
            if json_tags:
                self.logger.info(f"✅ JSON-FIRST reel tags: {json_tags}")
                return json_tags
        except Exception as e:
            self.logger.debug(f"JSON-first failed for reel, falling back to DOM: {e}")

        try:
            # Step 1: Find and click tag button
            self.logger.debug("Looking for reel tag button...")

            # Look for button with Tags SVG
            tag_button = self.page.locator(self.config.selector_tag_button).first

            # Check if button exists
            if tag_button.count() == 0:
                self.logger.debug("No tag button found - reel has no tags")
                return [self.config.default_no_tags_text]

            # Click the tag button
            self.logger.debug("Clicking tag button...")
            tag_button.click(timeout=self.config.tag_button_click_timeout)

            # Step 2: Wait for popup to appear
            time.sleep(self.config.ui_animation_delay)

            # Step 3: Extract tagged accounts from popup
            self.logger.debug("Extracting tagged accounts from popup...")

            # Method 1: All links in the popup
            try:
                # Look for links with username pattern
                links = self.page.locator('a[href^="/"]').all()
                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=1000)
                        if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                            username = href.strip('/').split('/')[-1]
                            # Filter out Instagram system paths
                            if username and username not in self.config.instagram_system_paths and username not in tagged:
                                tagged.append(username)
                    except Exception:
                        continue

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags in reel: {tagged}")

                    # Close popup by clicking outside or close button
                    try:
                        close_button = self.page.locator(self.config.selector_close_button).first
                        close_button.click(timeout=self.config.popup_close_timeout)
                    except Exception:
                        # Try pressing Escape
                        self.page.keyboard.press('Escape')

                    return tagged
            except Exception as e:
                self.logger.debug(f"Reel tag extraction from popup failed: {e}")

            # If popup method failed, try closing and return
            try:
                self.page.keyboard.press('Escape')
            except Exception:
                pass

        except Exception as e:
            self.logger.debug(f"Reel tag button click failed: {e}")

        # Fallback: Try post tag extraction method
        self.logger.debug("Fallback to post tag extraction for reel...")
        try:
            tagged = self.get_tagged_accounts()
            if tagged and tagged != ['No tags']:
                return tagged
        except Exception as e:
            self.logger.debug(f"Fallback tag extraction failed: {e}")

        self.logger.warning("No tags found in reel")
        return [self.config.default_no_tags_text]
