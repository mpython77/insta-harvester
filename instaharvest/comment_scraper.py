"""
Instagram Scraper - Comment Data Extractor (Direct URL Version)
Full comment scraping with likes, replies, timestamps, user info and collaborators

PROFESSIONAL VERSION with:
- Full comment extraction (text, likes, timestamp, reply count)
- User info extraction (username, profile picture)
- Collaborators extraction (post co-authors)
- Reply extraction (nested comments)
- Real-time progress tracking
- Intelligent page scrolling for all comments
- Error recovery and retry logic

NOTE: This version is designed for DIRECT URL viewing (https://www.instagram.com/p/POST_ID/)
      NOT for popup/modal views when clicking post from profile grid
"""

import time
import random
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .base import BaseScraper
from .config import ScraperConfig
from .error_handler import ErrorHandler
from .performance import PerformanceMonitor
from .logger import setup_logger


@dataclass
class CommentAuthor:
    """Comment author data structure"""
    username: str
    profile_url: str = ''
    profile_picture_url: str = ''
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Collaborator:
    """Post collaborator data structure"""
    username: str
    profile_url: str = ''
    profile_picture_url: str = ''
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CommentData:
    """Single comment data structure"""
    comment_id: str
    author: CommentAuthor
    text: str
    timestamp: str
    timestamp_iso: str
    likes_count: int
    reply_count: int
    comment_url: str
    is_reply: bool = False
    parent_comment_id: Optional[str] = None
    replies: List['CommentData'] = field(default_factory=list)
    has_translation: bool = False
    scraped_at: str = ''

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (recursive for replies)"""
        data = {
            'comment_id': self.comment_id,
            'author': self.author.to_dict() if isinstance(self.author, CommentAuthor) else self.author,
            'text': self.text,
            'timestamp': self.timestamp,
            'timestamp_iso': self.timestamp_iso,
            'likes_count': self.likes_count,
            'reply_count': self.reply_count,
            'comment_url': self.comment_url,
            'is_reply': self.is_reply,
            'parent_comment_id': self.parent_comment_id,
            'has_translation': self.has_translation,
            'scraped_at': self.scraped_at,
            'replies': [r.to_dict() if isinstance(r, CommentData) else r for r in self.replies]
        }
        return data


@dataclass
class PostCommentsData:
    """All comments for a single post"""
    post_url: str
    post_id: str
    total_comments_scraped: int
    total_replies_scraped: int
    comments: List[CommentData]
    collaborators: List[Collaborator] = field(default_factory=list)
    scraped_at: str = ''
    scraping_duration_seconds: float = 0.0

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'post_url': self.post_url,
            'post_id': self.post_id,
            'total_comments_scraped': self.total_comments_scraped,
            'total_replies_scraped': self.total_replies_scraped,
            'collaborators': [c.to_dict() for c in self.collaborators],
            'scraped_at': self.scraped_at,
            'scraping_duration_seconds': self.scraping_duration_seconds,
            'comments': [c.to_dict() for c in self.comments]
        }

    def get_all_comments_flat(self) -> List[CommentData]:
        """Get all comments including replies as flat list"""
        result = []
        for comment in self.comments:
            result.append(comment)
            result.extend(comment.replies)
        return result


class CommentScraper(BaseScraper):
    """
    Instagram Comment Scraper - DIRECT URL VERSION

    Designed for scraping comments when visiting posts directly via URL
    (https://www.instagram.com/p/POST_ID/)

    Extracts:
    - Collaborators (post co-authors)
    - Comment text
    - Author info (username, profile pic, verified status)
    - Likes count
    - Timestamp (human readable + ISO format)
    - Reply count
    - Nested replies
    - Comment URL/ID

    Features:
    - Page-based scrolling (not modal scrolling)
    - Reply expansion
    - Real-time progress callback
    - Error recovery
    - Performance monitoring
    """

    def __init__(self, config: Optional[ScraperConfig] = None, enable_diagnostics: bool = True):
        """
        Initialize comment scraper

        Args:
            config: Scraper configuration
            enable_diagnostics: Enable diagnostic mode
        """
        super().__init__(config)

        self.error_handler = ErrorHandler(self.logger)
        self.performance_monitor = PerformanceMonitor(self.logger)
        self.enable_diagnostics = enable_diagnostics

        self.logger.info("CommentScraper ready (Direct URL Mode)")

    def scrape(
        self,
        post_url: str,
        *,
        max_comments: Optional[int] = None,
        include_replies: bool = True,
        max_replies_per_comment: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> PostCommentsData:
        """
        Scrape all comments from a single post

        Args:
            post_url: URL of the Instagram post
            max_comments: Maximum number of main comments to scrape (None = all)
            include_replies: Whether to scrape replies
            max_replies_per_comment: Max replies per comment (None = all)
            progress_callback: Callback function for progress updates
                              signature: callback(scraped_count: int, comment: CommentData)

        Returns:
            PostCommentsData object with all comments and collaborators
        """
        start_time = time.time()

        # Extract post ID from URL
        post_id = self._extract_post_id(post_url)

        self.logger.info(f"Scraping comments from: {post_url}")
        self.logger.info(f"Post ID: {post_id}")
        self.logger.info(f"Max comments: {max_comments or 'All'}")
        self.logger.info(f"Include replies: {include_replies}")

        # Navigate to post
        self.goto_url(post_url)
        time.sleep(self.config.post_open_delay)

        # Wait for page to fully load
        self._wait_for_page_load()

        # Extract collaborators first (at top of post)
        collaborators = self._extract_collaborators()
        if collaborators:
            self.logger.info(f"Found {len(collaborators)} collaborators")

        # Wait for comments section to load
        self._wait_for_comments_to_load()

        # Scrape comments
        comments = self._scrape_all_comments(
            max_comments=max_comments,
            include_replies=include_replies,
            max_replies_per_comment=max_replies_per_comment,
            progress_callback=progress_callback
        )

        # Calculate totals
        total_replies = sum(len(c.replies) for c in comments)
        duration = time.time() - start_time

        result = PostCommentsData(
            post_url=post_url,
            post_id=post_id,
            total_comments_scraped=len(comments),
            total_replies_scraped=total_replies,
            comments=comments,
            collaborators=collaborators,
            scraping_duration_seconds=round(duration, 2)
        )

        self.logger.info(f"Scraped {len(comments)} comments, {total_replies} replies in {duration:.2f}s")

        return result

    def _extract_post_id(self, url: str) -> str:
        """Extract post ID from Instagram URL"""
        # Pattern: /p/ABC123/ or /reel/ABC123/
        match = re.search(r'/(?:p|reel)/([A-Za-z0-9_-]+)/?', url)
        if match:
            return match.group(1)
        return ''

    def _wait_for_page_load(self, timeout: float = 10.0) -> bool:
        """
        Wait for the main post page to fully load

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if page loaded successfully
        """
        self.logger.debug("Waiting for page to fully load...")

        # Key elements that should be present on a post page
        page_indicators = [
            'article',                    # Main article container
            'header',                     # Post header with user info
            'time[datetime]',             # Timestamp element
        ]

        start_time = time.time()
        while time.time() - start_time < timeout:
            for selector in page_indicators:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible(timeout=500):
                        self.logger.debug(f"Page loaded (found '{selector}')")
                        time.sleep(1.0)  # Extra time for JS to render
                        return True
                except:
                    continue
            time.sleep(0.5)

        self.logger.warning("Page load timeout - continuing anyway")
        return False

    def _wait_for_comments_to_load(self, timeout: float = 10.0) -> bool:
        """
        Wait for the comment section to appear on the page

        Direct URL view uses different selectors than popup view

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if comments section found, False otherwise
        """
        self.logger.debug("Waiting for comments section to load...")

        # Selectors for direct URL view comment section
        comment_indicators = [
            'div.x5yr21d',                # Comment section container
            'ul > div > li',              # Comment list items
            'span._ap3a._aaco._aacw',     # Username spans
            'a[href*="/c/"]',             # Comment permalink
            'time[datetime]',             # Comment timestamps
        ]

        start_time = time.time()
        while time.time() - start_time < timeout:
            for selector in comment_indicators:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible(timeout=500):
                        self.logger.debug(f"Comments section found via '{selector}'")
                        time.sleep(1.0)
                        return True
                except:
                    continue
            time.sleep(0.5)

        self.logger.warning("Comments section not found within timeout")
        return False

    def _extract_collaborators(self) -> List[Collaborator]:
        """
        Extract collaborators (post co-authors) from the post

        In direct URL view, collaborators appear with profile pictures
        and "and X others" text near the top of the post

        Returns:
            List of Collaborator objects
        """
        collaborators = []

        try:
            from bs4 import BeautifulSoup

            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Find the header section with collaborators
            # Look for profile pictures near "and X others" text
            header = soup.find('header')
            if not header:
                return collaborators

            # Find all profile picture links in header
            # Collaborators have links like /username/ with profile pictures
            profile_links = header.find_all('a', href=re.compile(r'^/[^/]+/$'))

            seen_usernames = set()

            for link in profile_links:
                try:
                    href = link.get('href', '')
                    username = href.strip('/').split('/')[-1]

                    # Skip system paths and duplicates
                    if not username or username in self.config.instagram_system_paths:
                        continue
                    if username in seen_usernames:
                        continue

                    # Find profile picture
                    profile_pic = ''
                    img = link.find('img', alt=re.compile(rf"{re.escape(username)}'s profile picture", re.I))
                    if not img:
                        img = link.find('img', alt=re.compile(r"profile picture", re.I))
                    if img:
                        profile_pic = img.get('src', '')

                    # Check verified status
                    is_verified = link.find_next('svg', {'aria-label': 'Verified'}) is not None

                    collaborator = Collaborator(
                        username=username,
                        profile_url=f'https://www.instagram.com/{username}/',
                        profile_picture_url=profile_pic,
                        is_verified=is_verified
                    )

                    collaborators.append(collaborator)
                    seen_usernames.add(username)
                    self.logger.debug(f"Found collaborator: @{username}")

                except Exception as e:
                    self.logger.debug(f"Error parsing collaborator: {e}")
                    continue

            # Check for "and X others" to detect if there are more collaborators
            others_text = soup.find(string=re.compile(r'and\s+\d+\s+others?', re.I))
            if others_text:
                match = re.search(r'and\s+(\d+)\s+others?', str(others_text), re.I)
                if match:
                    others_count = int(match.group(1))
                    self.logger.debug(f"Post has {others_count} additional collaborators (not all visible)")

        except ImportError:
            self.logger.warning("BeautifulSoup not available for collaborator extraction")
        except Exception as e:
            self.logger.error(f"Collaborator extraction failed: {e}")

        return collaborators

    def _scrape_all_comments(
        self,
        max_comments: Optional[int],
        include_replies: bool,
        max_replies_per_comment: Optional[int],
        progress_callback: Optional[callable]
    ) -> List[CommentData]:
        """
        Scrape all comments with intelligent scrolling

        Algorithm for Direct URL view:
        1. Extract visible comments
        2. Try to click "View more comments" or similar buttons
        3. Scroll page down to load more comments
        4. Repeat until no new comments found

        Returns:
            List of CommentData objects
        """
        comments = []
        seen_comment_ids = set()
        no_progress_count = 0
        scroll_attempt = 0
        max_no_progress = 3

        self.logger.info("Starting comment extraction (Direct URL mode)...")

        while True:
            # Check if we've reached max comments
            if max_comments and len(comments) >= max_comments:
                self.logger.info(f"Reached max comments limit: {max_comments}")
                break

            # Extract visible comments
            comments_before = len(comments)
            new_comments = self._extract_visible_comments(
                seen_ids=seen_comment_ids,
                include_replies=include_replies,
                max_replies_per_comment=max_replies_per_comment
            )

            # Process new comments
            if new_comments:
                for comment in new_comments:
                    if max_comments and len(comments) >= max_comments:
                        break

                    comments.append(comment)
                    seen_comment_ids.add(comment.comment_id)

                    # Progress callback
                    if progress_callback:
                        try:
                            progress_callback(len(comments), comment)
                        except Exception as e:
                            self.logger.debug(f"Progress callback error: {e}")

                    # Log comment
                    text_preview = comment.text[:50] + '...' if len(comment.text) > 50 else comment.text
                    self.logger.debug(
                        f"[{len(comments)}] @{comment.author.username}: "
                        f"{text_preview} ({comment.likes_count} likes)"
                    )

            comments_added = len(comments) - comments_before
            found_new_comments = comments_added > 0

            # Check max scroll attempts
            scroll_attempt += 1
            if scroll_attempt >= self.config.comment_max_scroll_attempts:
                self.logger.info(f"Reached max scroll attempts: {scroll_attempt}")
                break

            # Try to click "View more comments" button
            clicked_button = self._click_view_more_comments()

            if clicked_button:
                self.logger.debug("Clicked 'View more comments' button")
                time.sleep(random.uniform(
                    self.config.comment_scroll_delay_min,
                    self.config.comment_scroll_delay_max
                ))
                no_progress_count = 0
                continue

            # Scroll page to load more comments
            self._scroll_page()
            time.sleep(random.uniform(
                self.config.comment_scroll_delay_min,
                self.config.comment_scroll_delay_max
            ))

            # Check progress
            if not found_new_comments and not clicked_button:
                no_progress_count += 1
                self.logger.debug(f"No progress attempt {no_progress_count}/{max_no_progress}")

                if no_progress_count >= max_no_progress:
                    self.logger.info(f"No new comments after {no_progress_count} attempts, done")
                    break
            else:
                if found_new_comments:
                    no_progress_count = 0

        self.logger.info(f"Comment extraction complete: {len(comments)} comments found")
        return comments

    def _extract_visible_comments(
        self,
        seen_ids: set,
        include_replies: bool,
        max_replies_per_comment: Optional[int]
    ) -> List[CommentData]:
        """
        Extract all currently visible comments from direct URL view

        Uses selectors specific to direct URL HTML structure
        """
        comments = []

        try:
            from bs4 import BeautifulSoup

            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Find comment containers in direct URL view
            # The structure is different from popup view
            comment_containers = []

            # Strategy 1: Find all div containers with comment-like structure
            # Look for containers that have username links and timestamps
            all_divs = soup.find_all('div', class_=re.compile(r'x5yr21d|xw2csxc|x1odjw0f'))
            for div in all_divs:
                # Check if this div contains comment elements
                if div.find('a', href=re.compile(r'/c/\d+')):
                    comment_containers.append(div)

            # Strategy 2: Find li elements that contain comments
            if not comment_containers:
                all_lis = soup.find_all('li')
                for li in all_lis:
                    # Check for username and comment text
                    has_username = li.find('a', class_=re.compile(r'notranslate|_a6hd'))
                    has_text = li.find('span', class_=re.compile(r'_ap3a'))
                    if has_username or has_text:
                        comment_containers.append(li)

            # Strategy 3: Find by comment permalink pattern
            if not comment_containers:
                comment_links = soup.find_all('a', href=re.compile(r'/p/[^/]+/c/\d+/'))
                for link in comment_links:
                    # Get parent container
                    parent = link.find_parent(['div', 'li', 'article'])
                    if parent and parent not in comment_containers:
                        comment_containers.append(parent)

            # Strategy 4: Find by username pattern in spans
            if not comment_containers:
                username_spans = soup.find_all('span', class_=re.compile(r'_ap3a.*_aaco.*_aacw'))
                for span in username_spans:
                    parent = span.find_parent(['div', 'li'])
                    if parent and parent not in comment_containers:
                        comment_containers.append(parent)

            self.logger.debug(f"Found {len(comment_containers)} potential comment containers")

            for container in comment_containers:
                try:
                    comment = self._parse_comment_container_direct(container, soup)

                    if comment and comment.comment_id not in seen_ids:
                        # Extract replies if enabled
                        if include_replies:
                            comment.replies = self._extract_replies_for_comment(
                                container,
                                soup,
                                max_replies=max_replies_per_comment,
                                parent_comment_id=comment.comment_id
                            )
                            comment.reply_count = len(comment.replies)

                        comments.append(comment)

                except Exception as e:
                    self.logger.debug(f"Failed to parse comment container: {e}")
                    continue

            # Fallback to Playwright extraction if BeautifulSoup finds nothing
            if not comments:
                self.logger.debug("BeautifulSoup found nothing, trying Playwright")
                comments = self._extract_comments_playwright(seen_ids)

        except ImportError:
            self.logger.warning("BeautifulSoup not available, using Playwright")
            comments = self._extract_comments_playwright(seen_ids)
        except Exception as e:
            self.logger.error(f"Comment extraction failed: {e}")

        return comments

    def _parse_comment_container_direct(self, container, soup) -> Optional[CommentData]:
        """
        Parse a single comment container from direct URL view

        Direct URL HTML structure:
        - Profile picture: img[alt*="'s profile picture"]
        - Username link: a.notranslate._a6hd[href^="/"] or a[href^="/username/"]
        - Username text: span._ap3a._aaco._aacw._aacx._aad7._aade
        - Comment text: span with dir="auto" after username
        - Timestamp: time[datetime] with relative text (e.g., "8w")
        - Comment URL: a[href="/p/POST_ID/c/COMMENT_ID/"]
        - Likes: span containing "X likes" or "1 like"
        - View replies: span containing "View all X replies"
        """
        try:
            # === EXTRACT USERNAME ===
            username = ''
            profile_url = ''

            # Method 1: Find username link (a.notranslate or a._a6hd)
            username_link = container.find('a', class_=re.compile(r'notranslate|_a6hd'))
            if username_link:
                href = username_link.get('href', '')
                if href and href.startswith('/'):
                    username = href.strip('/').split('/')[0]
                    profile_url = f'https://www.instagram.com{href}'

            # Method 2: Find username from span._ap3a inside a link
            if not username:
                username_span = container.find('span', class_=re.compile(r'_ap3a.*_aaco.*_aacw.*_aad7.*_aade'))
                if username_span:
                    # Check if inside a link
                    parent_link = username_span.find_parent('a')
                    if parent_link and parent_link.get('href', '').startswith('/'):
                        username = parent_link.get('href', '').strip('/').split('/')[0]
                    else:
                        # Username might be text content
                        text = username_span.get_text(strip=True)
                        # Validate - should be short and no spaces
                        if text and len(text) < 50 and ' ' not in text:
                            username = text

            # Method 3: Find from any link with profile pattern
            if not username:
                all_links = container.find_all('a', href=re.compile(r'^/[^/]+/$'))
                for link in all_links:
                    href = link.get('href', '')
                    potential = href.strip('/').split('/')[0]
                    if potential and potential not in self.config.instagram_system_paths:
                        if not re.match(r'^(p|reel|c|\d+)$', potential):
                            username = potential
                            profile_url = f'https://www.instagram.com{href}'
                            break

            # Skip if no username or system path
            if not username:
                return None
            if username in self.config.instagram_system_paths:
                return None

            # === EXTRACT PROFILE PICTURE ===
            profile_pic_url = ''
            img_tag = container.find('img', alt=re.compile(rf"{re.escape(username)}'s profile picture", re.I))
            if not img_tag:
                img_tag = container.find('img', alt=re.compile(r"'s profile picture", re.I))
            if img_tag:
                profile_pic_url = img_tag.get('src', '')

            # === CHECK VERIFIED STATUS ===
            is_verified = container.find('svg', {'aria-label': 'Verified'}) is not None

            # === EXTRACT COMMENT TEXT ===
            comment_text = ''

            # Method 1: Find span with dir="auto" that contains text (not username)
            auto_spans = container.find_all('span', {'dir': 'auto'})
            for span in auto_spans:
                text = span.get_text(strip=True)
                # Skip if empty, username, or very short
                if not text or text == username or len(text) <= 1:
                    continue
                # Skip if contains just a username link
                if span.find('a') and len(text) < 30:
                    # Check if it's mostly a link
                    link_text = ''.join(a.get_text() for a in span.find_all('a'))
                    if link_text and link_text.strip() == text.strip():
                        continue
                comment_text = text
                break

            # Method 2: Find span._ap3a with comment text
            if not comment_text:
                text_span = container.find('span', class_=re.compile(r'_ap3a'))
                if text_span and text_span.get('dir') == 'auto':
                    text = text_span.get_text(strip=True)
                    if text and text != username:
                        comment_text = text

            # Method 3: Look for h1 > span structure (caption style)
            if not comment_text:
                h1 = container.find('h1')
                if h1:
                    span = h1.find('span')
                    if span:
                        text = span.get_text(strip=True)
                        if text and text != username:
                            comment_text = text

            # === EXTRACT TIMESTAMP ===
            timestamp = ''
            timestamp_iso = ''
            time_element = container.find('time')
            if time_element:
                timestamp = time_element.get_text(strip=True)
                timestamp_iso = time_element.get('datetime', '')

            # === EXTRACT COMMENT URL AND ID ===
            comment_url = ''
            comment_id = ''

            comment_link = container.find('a', href=re.compile(r'/p/[^/]+/c/\d+/'))
            if comment_link:
                href = comment_link.get('href', '')
                comment_url = 'https://www.instagram.com' + href
                match = re.search(r'/c/(\d+)/', href)
                if match:
                    comment_id = match.group(1)

            # Generate ID if not found from URL
            if not comment_id:
                comment_id = f"{username}_{abs(hash(comment_text))}"

            # === EXTRACT LIKES COUNT ===
            likes_count = 0

            # Find text containing "X likes" or "1 like"
            all_text = container.get_text(' ', strip=True)
            likes_match = re.search(r'(\d+)\s*likes?', all_text, re.I)
            if likes_match:
                likes_count = int(likes_match.group(1))

            # Also check spans specifically
            if likes_count == 0:
                spans = container.find_all('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if 'like' in text.lower():
                        match = re.search(r'(\d+)', text)
                        if match:
                            likes_count = int(match.group(1))
                            break

            # === CHECK TRANSLATION AVAILABLE ===
            has_translation = bool(container.find(string=re.compile(r'See\s*translation', re.I)))

            # === EXTRACT REPLY COUNT ===
            reply_count = 0
            view_replies = container.find(string=re.compile(r'View.*(\d+).*repl', re.I))
            if view_replies:
                match = re.search(r'(\d+)', str(view_replies))
                if match:
                    reply_count = int(match.group(1))

            # Also check "View all X replies" pattern
            if reply_count == 0:
                view_all = container.find(string=re.compile(r'View\s+all\s+(\d+)\s+replies', re.I))
                if view_all:
                    match = re.search(r'(\d+)', str(view_all))
                    if match:
                        reply_count = int(match.group(1))

            # Create author object
            author = CommentAuthor(
                username=username,
                profile_url=profile_url or f'https://www.instagram.com/{username}/',
                profile_picture_url=profile_pic_url,
                is_verified=is_verified
            )

            return CommentData(
                comment_id=comment_id,
                author=author,
                text=comment_text,
                timestamp=timestamp,
                timestamp_iso=timestamp_iso,
                likes_count=likes_count,
                reply_count=reply_count,
                comment_url=comment_url,
                is_reply=False,
                has_translation=has_translation
            )

        except Exception as e:
            self.logger.debug(f"Comment parsing error: {e}")
            return None

    def _extract_replies_for_comment(
        self,
        comment_container,
        soup,
        max_replies: Optional[int],
        parent_comment_id: str
    ) -> List[CommentData]:
        """Extract replies for a specific comment"""
        replies = []

        try:
            from bs4 import BeautifulSoup

            # Click "View replies" button if exists
            self._expand_replies(parent_comment_id)

            # Wait for replies to load
            time.sleep(self.config.comment_reply_load_delay)

            # Re-parse HTML to get replies
            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Find reply containers - they're usually nested or indented
            # Look for containers after "View X replies" with reply-like structure
            reply_containers = []

            # Find all elements with reply pattern
            all_reply_links = soup.find_all('a', href=re.compile(r'/c/\d+/'))
            for link in all_reply_links:
                container = link.find_parent(['div', 'li'])
                if container and container not in reply_containers:
                    reply_containers.append(container)

            for container in reply_containers:
                if max_replies and len(replies) >= max_replies:
                    break

                reply = self._parse_comment_container_direct(container, soup)
                if reply and reply.comment_id != parent_comment_id:
                    # Check if this is actually a reply (not main comment)
                    if reply.comment_id not in [r.comment_id for r in replies]:
                        reply.is_reply = True
                        reply.parent_comment_id = parent_comment_id
                        replies.append(reply)

        except Exception as e:
            self.logger.debug(f"Reply extraction error: {e}")

        return replies

    def _expand_replies(self, comment_id: str) -> bool:
        """Click 'View replies' button for a comment"""
        try:
            # Look for "View replies" or "View X replies" buttons
            patterns = [
                'span:has-text("View all")',
                'span:has-text("View replies")',
                'div:has-text("View all"):has-text("replies")',
            ]

            for pattern in patterns:
                try:
                    buttons = self.page.locator(pattern).all()
                    for btn in buttons[:3]:  # Try first 3 matches
                        try:
                            if btn.is_visible():
                                btn.click(timeout=2000)
                                time.sleep(self.config.popup_animation_delay)
                                return True
                        except:
                            continue
                except:
                    continue

        except Exception as e:
            self.logger.debug(f"Expand replies failed: {e}")

        return False

    def _click_view_more_comments(self) -> bool:
        """
        Click button to load more comments

        In direct URL view, this might be:
        - "View all X comments" link
        - "Load more comments" button
        - Plus (+) button

        Returns:
            True if a button was clicked
        """
        try:
            # Method 1: "View all X comments" link
            try:
                view_all = self.page.locator('span:has-text("View all")').first
                if view_all.is_visible(timeout=1000):
                    view_all.click(timeout=2000)
                    self.logger.debug("Clicked 'View all comments'")
                    time.sleep(self.config.popup_animation_delay)
                    return True
            except:
                pass

            # Method 2: "Load more comments" button with SVG
            try:
                load_more = self.page.locator('button:has(svg[aria-label="Load more comments"])').first
                if load_more.is_visible(timeout=1000):
                    load_more.click(timeout=2000)
                    self.logger.debug("Clicked 'Load more comments' button")
                    time.sleep(self.config.popup_animation_delay)
                    return True
            except:
                pass

            # Method 3: Plus button with class _abl-
            try:
                plus_btn = self.page.locator('button._abl-').first
                if plus_btn.is_visible(timeout=1000):
                    plus_btn.click(timeout=2000)
                    self.logger.debug("Clicked plus button")
                    time.sleep(self.config.popup_animation_delay)
                    return True
            except:
                pass

            # Method 4: Any "View" or "Load" text in button area
            patterns = [
                'span:has-text("View more")',
                'button:has-text("Load")',
                'div[role="button"]:has-text("View")',
            ]

            for pattern in patterns:
                try:
                    btn = self.page.locator(pattern).first
                    if btn.is_visible(timeout=500):
                        btn.click(timeout=2000)
                        time.sleep(self.config.ui_animation_delay)
                        return True
                except:
                    continue

        except Exception as e:
            self.logger.debug(f"Click view more failed: {e}")

        return False

    def _scroll_page(self) -> None:
        """
        Scroll the page to load more comments

        In direct URL view, comments load as you scroll the main page
        (not a modal/popup container)
        """
        try:
            # Strategy 1: Scroll to bottom of comment section
            try:
                # Find the last visible comment or time element
                last_time = self.page.locator('time[datetime]').last
                if last_time.is_visible():
                    last_time.scroll_into_view_if_needed()
                    self.logger.debug("Scrolled to last timestamp")
                    return
            except:
                pass

            # Strategy 2: Use keyboard Page Down
            try:
                self.page.keyboard.press('PageDown')
                self.logger.debug("Used PageDown key")
                return
            except:
                pass

            # Strategy 3: JavaScript window scroll
            try:
                self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.7)')
                self.logger.debug("Used window.scrollBy")
                return
            except:
                pass

            # Strategy 4: Find scrollable container
            try:
                scrolled = self.page.evaluate('''() => {
                    // Find main content area
                    const main = document.querySelector('main') ||
                                 document.querySelector('article')?.parentElement;
                    if (main) {
                        const style = window.getComputedStyle(main);
                        if (main.scrollHeight > main.clientHeight) {
                            main.scrollTop += main.clientHeight * 0.7;
                            return true;
                        }
                    }
                    // Fallback to body scroll
                    window.scrollBy(0, window.innerHeight * 0.7);
                    return true;
                }''')
                if scrolled:
                    self.logger.debug("Scrolled via JavaScript")
            except Exception as e:
                self.logger.debug(f"JS scroll failed: {e}")

        except Exception as e:
            self.logger.debug(f"Page scroll failed: {e}")

    def _extract_comments_playwright(self, seen_ids: set) -> List[CommentData]:
        """
        Extract comments using Playwright (fallback method)

        Uses locators specific to direct URL view
        """
        comments = []

        try:
            # Find elements that look like comments
            # Strategy 1: Elements with timestamp links
            time_elements = self.page.locator('time[datetime]').all()

            for time_el in time_elements:
                try:
                    # Get parent container
                    container = time_el.locator('xpath=ancestor::div[position()<=4]').last

                    # Try to extract username
                    username = ''
                    try:
                        user_link = container.locator('a[href^="/"]').first
                        href = user_link.get_attribute('href', timeout=1000)
                        if href:
                            username = href.strip('/').split('/')[0]
                    except:
                        pass

                    if not username or username in self.config.instagram_system_paths:
                        continue

                    # Extract text
                    comment_text = ''
                    try:
                        text_span = container.locator('span[dir="auto"]').first
                        comment_text = text_span.inner_text(timeout=1000)
                    except:
                        pass

                    if not comment_text or comment_text == username:
                        continue

                    # Extract timestamp
                    timestamp = ''
                    timestamp_iso = ''
                    try:
                        timestamp = time_el.inner_text(timeout=1000)
                        timestamp_iso = time_el.get_attribute('datetime', timeout=1000)
                    except:
                        pass

                    # Generate ID
                    comment_id = f"{username}_{abs(hash(comment_text))}"

                    if comment_id in seen_ids:
                        continue

                    # Extract likes
                    likes_count = 0
                    try:
                        text = container.inner_text(timeout=1000)
                        match = re.search(r'(\d+)\s*likes?', text, re.I)
                        if match:
                            likes_count = int(match.group(1))
                    except:
                        pass

                    author = CommentAuthor(
                        username=username,
                        profile_url=f'https://www.instagram.com/{username}/'
                    )

                    comment = CommentData(
                        comment_id=comment_id,
                        author=author,
                        text=comment_text,
                        timestamp=timestamp,
                        timestamp_iso=timestamp_iso,
                        likes_count=likes_count,
                        reply_count=0,
                        comment_url='',
                        is_reply=False
                    )

                    comments.append(comment)
                    self.logger.debug(f"Playwright extracted: @{username}")

                except Exception as e:
                    self.logger.debug(f"Playwright element extraction error: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Playwright extraction failed: {e}")

        self.logger.debug(f"Playwright extraction found {len(comments)} comments")
        return comments

    def scrape_multiple(
        self,
        post_urls: List[str],
        *,
        max_comments_per_post: Optional[int] = None,
        include_replies: bool = True,
        progress_callback: Optional[callable] = None,
        delay_between_posts: bool = True
    ) -> List[PostCommentsData]:
        """
        Scrape comments from multiple posts

        Args:
            post_urls: List of post URLs
            max_comments_per_post: Max comments per post
            include_replies: Include replies
            progress_callback: Progress callback
            delay_between_posts: Add delay between posts

        Returns:
            List of PostCommentsData objects
        """
        self.logger.info(f"Scraping comments from {len(post_urls)} posts...")

        # Load session and setup browser
        session_data = self.load_session()
        self.setup_browser(session_data)

        results = []

        try:
            for i, url in enumerate(post_urls, 1):
                self.logger.info(f"[{i}/{len(post_urls)}] Scraping comments: {url}")

                try:
                    comments_data = self.scrape(
                        url,
                        max_comments=max_comments_per_post,
                        include_replies=include_replies,
                        progress_callback=progress_callback
                    )
                    results.append(comments_data)

                except Exception as e:
                    self.logger.error(f"Failed to scrape comments from {url}: {e}")
                    results.append(PostCommentsData(
                        post_url=url,
                        post_id=self._extract_post_id(url),
                        total_comments_scraped=0,
                        total_replies_scraped=0,
                        comments=[],
                        collaborators=[]
                    ))

                # Delay between posts
                if delay_between_posts and i < len(post_urls):
                    delay = random.uniform(
                        self.config.comment_post_delay_min,
                        self.config.comment_post_delay_max
                    )
                    self.logger.debug(f"Waiting {delay:.1f}s before next post...")
                    time.sleep(delay)

        finally:
            self.close()

        # Print summary
        total_comments = sum(r.total_comments_scraped for r in results)
        total_replies = sum(r.total_replies_scraped for r in results)
        total_collaborators = sum(len(r.collaborators) for r in results)

        self.logger.info(f"\n{'='*60}")
        self.logger.info("COMMENT SCRAPING COMPLETE!")
        self.logger.info(f"Posts processed: {len(results)}")
        self.logger.info(f"Total comments: {total_comments}")
        self.logger.info(f"Total replies: {total_replies}")
        self.logger.info(f"Total collaborators found: {total_collaborators}")
        self.logger.info(f"{'='*60}")

        return results
