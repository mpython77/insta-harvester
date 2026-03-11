"""
Instagram Scraper - Tagged Posts Extractor
Scrape posts where a user has been tagged by others.

URL: /{username}/tagged/
JSON Key: xdt_api__v1__usertags__user_id__feed_connection

JSON-First Architecture: Extracts post links, engagement data, 
and tagger info from embedded JSON scripts with scroll pagination.
"""

import time
import json
import random
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

from .base import BaseScraper
from .config import ScraperConfig
from .post_data import PostLocation, PostOwner


@dataclass
class TaggedPostData:
    """A single post where the target user was tagged"""
    url: str = ''
    shortcode: str = ''
    pk: str = ''
    media_type: int = 0          # 1=image, 2=video, 8=carousel
    product_type: str = ''       # feed, clips, carousel_container

    # Who tagged them (post owner)
    owner: Optional[PostOwner] = None

    # Engagement
    like_count: int = 0
    comment_count: int = 0

    # Content
    caption: str = ''
    timestamp: str = ''
    taken_at: int = 0
    taken_at_human: str = ''

    # Location
    location: Optional[PostLocation] = None

    # Tags in this post
    tagged_accounts: List[str] = field(default_factory=list)

    # Media
    thumbnail_url: str = ''
    width: int = 0
    height: int = 0
    accessibility_caption: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_reel(self) -> bool:
        return self.product_type == 'clips' or self.media_type == 2

    @property
    def is_carousel(self) -> bool:
        return self.media_type == 8

    @property
    def has_location(self) -> bool:
        return self.location is not None


@dataclass
class TaggedPostsResult:
    """Complete result from tagged posts scraping"""
    username: str = ''
    tagged_posts: List[TaggedPostData] = field(default_factory=list)
    total_found: int = 0
    scrape_time: float = 0.0
    json_extracted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def post_count(self) -> int:
        return len(self.tagged_posts)

    @property
    def reel_count(self) -> int:
        return sum(1 for p in self.tagged_posts if p.is_reel)

    @property
    def unique_taggers(self) -> List[str]:
        """Unique users who tagged this account"""
        taggers = []
        for p in self.tagged_posts:
            if p.owner and p.owner.username not in taggers:
                taggers.append(p.owner.username)
        return taggers


class TaggedPostsScraper(BaseScraper):
    """
    Instagram Tagged Posts Scraper

    Extracts posts from /{username}/tagged/ page.
    These are posts where OTHER users have tagged the target account.

    JSON-First Architecture:
    - Primary: Extract from <script type="application/json"> tags
    - Scroll: Load more posts via infinite scroll
    - Fallback: DOM-based link extraction

    Perfect for lead generation — find who promotes your brand!

    Usage:
        scraper = TaggedPostsScraper(config=config)
        session = scraper.load_session()
        scraper.setup_browser(session)

        result = scraper.scrape("mondayswimwear", max_posts=50)
        for post in result.tagged_posts:
            print(f"{post.owner.username} tagged you — {post.like_count} likes")
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.logger.info("TaggedPostsScraper ready")

    def scrape(
        self,
        username: str,
        *,
        target_count: Optional[int] = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        scroll_pause: float = 2.0,
        max_scrolls: int = 20
    ) -> TaggedPostsResult:
        """
        Scrape tagged posts for a user.

        Args:
            username: Instagram username (without @)
            target_count: Maximum posts to collect (None = all)
            date_from: Filter start date 'YYYY-MM-DD' (inclusive)
            date_to: Filter end date 'YYYY-MM-DD' (inclusive)
            scroll_pause: Seconds between scrolls (default 2.0)
            max_scrolls: Maximum scroll attempts (default 20)

        Returns:
            TaggedPostsResult with all tagged posts
        """
        username = username.strip().lstrip('@').strip('/')
        url = f"https://www.instagram.com/{username}/tagged/"

        # ═══════ AUTO BROWSER SETUP (standalone mode) ═══════
        is_shared_browser = self.page is not None and self.browser is not None
        if not is_shared_browser:
            self.logger.debug("Setting up new browser session (standalone mode)")
            session_data = self.load_session()
            self.setup_browser(session_data)

        self.logger.info(f"🏷️ Scraping tagged posts: {url}")
        start_time = time.time()

        # Navigate to tagged page
        self.goto_url(url)
        time.sleep(3)  # Wait for initial load

        # ═══════ JSON-FIRST EXTRACTION ═══════
        posts = self._extract_from_json()

        if posts:
            self.logger.info(
                f"✅ JSON-FIRST: Found {len(posts)} tagged posts"
            )
        else:
            self.logger.warning("⚠️ JSON extraction found 0 posts, trying DOM...")
            posts = self._extract_from_dom()

        # ═══════ SCROLL FOR MORE ═══════
        if target_count is None or len(posts) < target_count:
            limit_str = str(target_count) if target_count else "all"
            self.logger.info(
                f"📜 Scrolling for more posts... "
                f"(have {len(posts)}, want {limit_str})"
            )
            posts = self._scroll_and_collect(
                existing_posts=posts,
                target_count=target_count,
                scroll_pause=scroll_pause,
                max_scrolls=max_scrolls
            )

        # ═══════ DATE RANGE FILTER ═══════
        if date_from or date_to:
            posts = self._filter_by_date_range(posts, date_from, date_to, url_key='url')

        # Trim to max
        if target_count is not None:
            posts = posts[:target_count]

        elapsed = time.time() - start_time
        result = TaggedPostsResult(
            username=username,
            tagged_posts=posts,
            total_found=len(posts),
            scrape_time=elapsed,
            json_extracted=len(posts) > 0
        )

        self.logger.info(
            f"\n{'='*60}\n"
            f"🏷️ TAGGED POSTS COMPLETE\n"
            f"{'='*60}\n"
            f"User: @{username}\n"
            f"Posts found: {result.post_count}\n"
            f"Reels: {result.reel_count}\n"
            f"Unique taggers: {len(result.unique_taggers)}\n"
            f"Time: {elapsed:.1f}s\n"
            f"{'='*60}"
        )

        return result

    # ==================== JSON-FIRST ====================

    def _extract_from_json(self) -> List[TaggedPostData]:
        """Extract tagged posts from embedded JSON scripts."""
        posts = []
        seen_codes = set()

        try:
            scripts = self.page.locator('script[type="application/json"]').all()
            self.logger.debug(f"Tagged JSON: checking {len(scripts)} scripts")

            for script in scripts:
                try:
                    content = script.inner_text(timeout=1000)
                    if len(content) < 500:
                        continue

                    data = json.loads(content)
                    nodes = self._find_tagged_nodes(data, depth=0)

                    for node in nodes:
                        code = node.get('code', '')
                        if code and code not in seen_codes:
                            seen_codes.add(code)
                            post = self._parse_node(node)
                            if post:
                                posts.append(post)

                except Exception:
                    continue

        except Exception as e:
            self.logger.debug(f"Tagged JSON error: {e}")

        return posts

    def _find_tagged_nodes(self, obj, depth: int = 0) -> List[dict]:
        """
        Find all media nodes from tagged posts JSON.

        Looks for:
        - xdt_api__v1__usertags__user_id__feed_connection.edges[].node
        - edges[].node with pk/media_type
        """
        nodes = []
        if depth > 20 or not obj:
            return nodes

        if isinstance(obj, dict):
            # Direct match: edges[] with nodes containing media
            if 'edges' in obj and isinstance(obj['edges'], list):
                for edge in obj['edges']:
                    if isinstance(edge, dict) and 'node' in edge:
                        node = edge['node']
                        if isinstance(node, dict):
                            # node itself is media
                            if 'pk' in node or 'code' in node or 'media_type' in node:
                                nodes.append(node)
                            # node.media
                            media = node.get('media')
                            if isinstance(media, dict) and ('pk' in media or 'code' in media):
                                nodes.append(media)

                if nodes:
                    return nodes  # Found, don't recurse further

            # Recurse into values
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    found = self._find_tagged_nodes(value, depth + 1)
                    if found:
                        nodes.extend(found)

        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    found = self._find_tagged_nodes(item, depth + 1)
                    if found:
                        nodes.extend(found)

        return nodes

    def _parse_node(self, node: dict) -> Optional[TaggedPostData]:
        """Parse a media node dict into TaggedPostData."""
        if not isinstance(node, dict):
            return None

        code = node.get('code', '')
        if not code:
            return None

        # Determine URL — Instagram tagged page links include owner: /{owner}/p/{code}/
        media_type = node.get('media_type', 1)
        product_type = node.get('product_type', '')
        
        # Owner (who posted / tagged the target user)
        owner = None
        user = node.get('user') or node.get('owner')
        if isinstance(user, dict):
            owner = PostOwner(
                username=user.get('username', ''),
                full_name=user.get('full_name', ''),
                pk=str(user.get('pk', '')),
                is_verified=user.get('is_verified', False),
                profile_pic_url=user.get('profile_pic_url', '')
            )
        
        # Build URL with owner username if available
        owner_prefix = f"{owner.username}/" if owner and owner.username else ''
        if product_type == 'clips' or media_type == 2:
            url = f"https://www.instagram.com/reel/{code}/"
        else:
            url = f"https://www.instagram.com/{owner_prefix}p/{code}/"

        # Timestamp
        taken_at = node.get('taken_at', 0)
        timestamp = ''
        taken_at_human = ''
        if taken_at:
            try:
                dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
                timestamp = dt.strftime('%b %d, %Y')
                taken_at_human = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception:
                pass


        # Caption
        caption = ''
        cap = node.get('caption')
        if isinstance(cap, dict):
            caption = cap.get('text', '')

        # Location
        location = None
        loc = node.get('location')
        if isinstance(loc, dict) and loc.get('name'):
            location = PostLocation(
                name=loc.get('name', ''),
                pk=str(loc.get('pk', '')),
                latitude=loc.get('lat', loc.get('latitude', 0.0)),
                longitude=loc.get('lng', loc.get('longitude', 0.0)),
                address=loc.get('address', ''),
                city=loc.get('city', '')
            )

        # Tags
        tagged_accounts = []
        usertags = node.get('usertags')
        if isinstance(usertags, dict) and 'in' in usertags:
            for entry in usertags['in']:
                if isinstance(entry, dict) and 'user' in entry:
                    u = entry['user']
                    if isinstance(u, dict) and 'username' in u:
                        uname = u['username']
                        if uname not in tagged_accounts:
                            tagged_accounts.append(uname)

        # Carousel tags
        carousel = node.get('carousel_media', [])
        if isinstance(carousel, list):
            for slide in carousel:
                if isinstance(slide, dict):
                    s_ut = slide.get('usertags')
                    if isinstance(s_ut, dict) and 'in' in s_ut:
                        for entry in s_ut['in']:
                            if isinstance(entry, dict) and 'user' in entry:
                                u = entry['user']
                                if isinstance(u, dict) and 'username' in u:
                                    uname = u['username']
                                    if uname not in tagged_accounts:
                                        tagged_accounts.append(uname)

        # Thumbnail
        thumbnail_url = ''
        img_versions = node.get('image_versions2', {})
        if isinstance(img_versions, dict):
            candidates = img_versions.get('candidates', [])
            if isinstance(candidates, list) and candidates:
                thumbnail_url = candidates[0].get('url', '')

        return TaggedPostData(
            url=url,
            shortcode=code,
            pk=str(node.get('pk', '')),
            media_type=media_type,
            product_type=product_type,
            owner=owner,
            like_count=node.get('like_count', 0),
            comment_count=node.get('comment_count', 0),
            caption=caption,
            timestamp=timestamp,
            taken_at=taken_at,
            taken_at_human=taken_at_human,
            location=location,
            tagged_accounts=tagged_accounts,
            thumbnail_url=thumbnail_url,
            width=node.get('original_width', 0),
            height=node.get('original_height', 0),
            accessibility_caption=node.get('accessibility_caption', '')
        )

    # ==================== DOM FALLBACK ====================

    def _extract_from_dom(self) -> List[TaggedPostData]:
        """Extract post links from DOM — also parses owner from href path."""
        posts = []
        seen = set()

        try:
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"]').all()
            for link in links:
                try:
                    href = link.get_attribute('href', timeout=1000)
                    if href and href not in seen:
                        seen.add(href)
                        full_url = f"https://www.instagram.com{href}" if href.startswith('/') else href

                        # Parse href: /{owner}/p/{code}/ or /reel/{code}/
                        parts = href.strip('/').split('/')
                        code = ''
                        owner_username = ''
                        
                        if '/p/' in href and len(parts) >= 3:
                            # /{owner}/p/{code}
                            owner_username = parts[0]
                            code = parts[2]
                        elif '/reel/' in href and len(parts) >= 2:
                            code = parts[1]
                        elif len(parts) >= 2:
                            code = parts[-1]

                        owner = None
                        if owner_username:
                            owner = PostOwner(
                                username=owner_username,
                                full_name='',
                                pk='',
                                is_verified=False,
                                profile_pic_url=''
                            )

                        posts.append(TaggedPostData(
                            url=full_url,
                            shortcode=code,
                            owner=owner,
                            product_type='clips' if '/reel/' in href else 'feed'
                        ))
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"DOM extraction error: {e}")

        return posts

    # ==================== SCROLL PAGINATION ====================

    def _scroll_and_collect(
        self,
        existing_posts: List[TaggedPostData],
        target_count: Optional[int],
        scroll_pause: float,
        max_scrolls: int
    ) -> List[TaggedPostData]:
        """Scroll down to load and collect more tagged posts."""
        all_posts = list(existing_posts)
        seen_codes = {p.shortcode for p in all_posts if p.shortcode}

        prev_count = len(all_posts)
        no_new_count = 0

        for scroll_num in range(1, max_scrolls + 1):
            if target_count is not None and len(all_posts) >= target_count:
                self.logger.info(f"✅ Reached target ({target_count} posts)")
                break

            # Scroll down
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(scroll_pause + random.uniform(0.5, 1.5))

            # Try JSON extraction after scroll
            new_posts = self._extract_from_json()

            # Also try DOM
            dom_posts = self._extract_from_dom()
            new_posts.extend(dom_posts)

            # Add only unseen posts
            added = 0
            for post in new_posts:
                if post.shortcode and post.shortcode not in seen_codes:
                    seen_codes.add(post.shortcode)
                    all_posts.append(post)
                    added += 1

            self.logger.debug(
                f"Scroll {scroll_num}/{max_scrolls}: "
                f"+{added} new, total={len(all_posts)}"
            )

            if added == 0:
                no_new_count += 1
                if no_new_count >= 3:
                    self.logger.info("📛 No new posts after 3 scrolls, stopping")
                    break
            else:
                no_new_count = 0

        return all_posts
