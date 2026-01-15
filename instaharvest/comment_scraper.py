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

        Uses selectors specific to direct URL HTML structure.
        Based on Instagram's current HTML structure where each comment has:
        - Profile picture link: a._a6hd with img[alt*="profile picture"]
        - Username span: span._ap3a._aaco._aacw._aacx._aad7._aade
        - Comment permalink: a[href*="/c/"] with time[datetime]
        - Comment text: span[dir="auto"] with specific classes (x5n08af)
        - Likes: span with "X likes" inside role="button" div
        - View replies: "View all X replies" in div.xpdvgm7
        """
        comments = []

        try:
            from bs4 import BeautifulSoup

            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            comment_containers = []
            seen_container_ids = set()

            # PRIMARY STRATEGY: Find by comment permalink (most reliable)
            # Each comment has a unique permalink like /p/POST_ID/c/COMMENT_ID/
            comment_links = soup.find_all('a', href=re.compile(r'/p/[^/]+/c/\d+/'))
            self.logger.debug(f"Found {len(comment_links)} comment permalinks")

            for link in comment_links:
                try:
                    # Navigate up to find the comment container
                    # The container is typically 4-8 levels up from the permalink
                    container = self._find_comment_container(link)
                    if container:
                        container_id = id(container)
                        if container_id not in seen_container_ids:
                            seen_container_ids.add(container_id)
                            comment_containers.append(container)
                except Exception as e:
                    self.logger.debug(f"Error finding container for permalink: {e}")
                    continue

            # FALLBACK STRATEGY 1: Find by username span class
            if not comment_containers:
                self.logger.debug("Trying username span strategy")
                username_spans = soup.find_all('span', class_=re.compile(r'_ap3a.*_aaco.*_aacw.*_aacx.*_aad7.*_aade'))
                for span in username_spans:
                    try:
                        container = self._find_comment_container(span)
                        if container:
                            container_id = id(container)
                            if container_id not in seen_container_ids:
                                seen_container_ids.add(container_id)
                                comment_containers.append(container)
                    except:
                        continue

            # FALLBACK STRATEGY 2: Find by profile picture pattern
            if not comment_containers:
                self.logger.debug("Trying profile picture strategy")
                profile_pics = soup.find_all('img', alt=re.compile(r"'s profile picture", re.I))
                for img in profile_pics:
                    try:
                        container = self._find_comment_container(img)
                        if container:
                            container_id = id(container)
                            if container_id not in seen_container_ids:
                                seen_container_ids.add(container_id)
                                comment_containers.append(container)
                    except:
                        continue

            self.logger.debug(f"Found {len(comment_containers)} unique comment containers")

            for container in comment_containers:
                try:
                    comment = self._parse_comment_container_direct(container, soup)

                    if comment and comment.comment_id not in seen_ids:
                        # Skip if this looks like post caption (no comment ID from URL)
                        if comment.comment_id.startswith('caption_'):
                            continue

                        # Extract replies if enabled
                        if include_replies:
                            comment.replies = self._extract_replies_for_comment(
                                container,
                                soup,
                                max_replies=max_replies_per_comment,
                                parent_comment_id=comment.comment_id
                            )
                            if comment.replies:
                                comment.reply_count = max(comment.reply_count, len(comment.replies))

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

    def _find_comment_container(self, element) -> Optional[Any]:
        """
        Find the full comment container starting from any element inside a comment.

        Instagram HTML structure (January 2026):
        =========================================
        The comment container is typically a div with classes like:
        - x78zum5 xsag5q8 x1iyjqo2 (main flex container)

        It should include:
        - Profile picture area (div.xbmvrgn or containing img with profile picture)
        - Content area with username, timestamp, text
        - Action buttons (likes, reply, etc.)

        The key is to find the first ancestor that has BOTH:
        1. A comment permalink (a[href*="/c/"])
        2. A profile picture

        Returns the container element or None if not found.
        """
        if element is None:
            return None

        # Navigate up the DOM tree looking for the comment container
        current = element
        max_levels = 12  # Maximum levels to traverse up
        best_container = None
        best_container_level = 999

        for level in range(max_levels):
            parent = current.parent
            if parent is None or parent.name in ['body', 'html', '[document]']:
                break

            # Skip certain container types that are too high
            if parent.name in ['article', 'main', 'section', 'ul']:
                break

            # Check if this parent has the essential comment elements
            has_comment_link = parent.find('a', href=re.compile(r'/p/[^/]+/c/\d+/?'))

            # If we find a comment link, check for other essential elements
            if has_comment_link:
                # Check for profile picture
                has_profile_pic = parent.find('img', alt=re.compile(r"'s profile picture", re.I))

                # Check for username span with lambda to handle class variations
                has_username = parent.find('span', class_=lambda x: x and (
                    ('_ap3a' in ' '.join(x) and '_aade' in ' '.join(x)) if isinstance(x, list)
                    else ('_ap3a' in x and '_aade' in x)
                ))

                # Check for timestamp
                has_timestamp = parent.find('time', attrs={'datetime': True})

                # Count comment links to ensure we're not too high
                all_comment_links = parent.find_all('a', href=re.compile(r'/p/[^/]+/c/\d+/?'))

                # Good container criteria:
                # - Has comment link, username, timestamp/profile pic
                # - Has only 1 comment link (not the entire comments list)
                if has_username and (has_timestamp or has_profile_pic):
                    if len(all_comment_links) == 1:
                        # This is likely the exact comment container
                        return parent
                    elif len(all_comment_links) <= 2 and level < best_container_level:
                        # Save as potential best container
                        best_container = parent
                        best_container_level = level

            current = parent

        # Return the best container we found, or try fallback
        if best_container:
            return best_container

        # Fallback: Go up a fixed number of levels from the original element
        # This works when the DOM structure doesn't match expected patterns
        current = element
        for i in range(7):
            if current.parent and current.parent.name not in ['body', 'html', '[document]', 'article', 'main', 'ul']:
                current = current.parent
            else:
                break

        # Validate the fallback container has at least some content
        if current:
            text_content = current.get_text(strip=True)
            if len(text_content) > 5:  # Has some meaningful content
                return current

        return None

    def _parse_comment_container_direct(self, container, soup) -> Optional[CommentData]:
        """
        Parse a single comment container from direct URL view

        Instagram HTML structure (as of January 2026):
        ===============================================
        Comment Container (div with classes like x78zum5 xsag5q8...):
        ├── Profile Picture Area (div.xbmvrgn)
        │   └── a._a6hd[href="/username/"]
        │       └── img[alt="username's profile picture"][src="..."]
        │
        ├── Content Area (div with x78zum5 x1iyjqo2)
        │   ├── Username + Timestamp Row (div)
        │   │   ├── span._ap3a._aaco._aacw._aacx._aad7._aade (username text)
        │   │   │   └── inside: a.notranslate._a6hd[href="/username/"]
        │   │   └── a[href="/p/POST_ID/c/COMMENT_ID/"]
        │   │       └── time[datetime="ISO"][title="Date"]
        │   │
        │   ├── Comment Text Row (div with class x1cy8zhl)
        │   │   └── span[dir="auto"] with classes including x5n08af
        │   │
        │   └── Action Buttons Row (div with style --x-height: 16px)
        │       ├── div[role="button"] > span.xuxw1ft "10 likes"
        │       ├── div[role="button"] > span "Reply"
        │       └── div[role="button"] > span "See translation"
        │
        └── Like Heart Button (svg aria-label="Like")

        View Replies (sibling div with class xpdvgm7):
        └── div[role="button"] > span "View all 6 replies"
        """
        try:
            # ==================== EXTRACT COMMENT URL AND ID FIRST ====================
            # This is the most reliable identifier
            comment_url = ''
            comment_id = ''

            # Find comment permalink: /p/POST_ID/c/COMMENT_ID/
            comment_link = container.find('a', href=re.compile(r'/p/[^/]+/c/\d+/?'))
            if comment_link:
                href = comment_link.get('href', '')
                comment_url = 'https://www.instagram.com' + href
                match = re.search(r'/c/(\d+)/?', href)
                if match:
                    comment_id = match.group(1)

            # Skip if this is likely post caption (no comment permalink)
            if not comment_id:
                return None

            # ==================== EXTRACT USERNAME ====================
            username = ''
            profile_url = ''

            # Primary: Find username span with specific Instagram classes
            # Class pattern: _ap3a _aaco _aacw _aacx _aad7 _aade
            username_span = container.find('span', class_=lambda x: x and '_ap3a' in ' '.join(x) and '_aade' in ' '.join(x) if isinstance(x, list) else (x and '_ap3a' in x and '_aade' in x))
            if username_span:
                username = username_span.get_text(strip=True)
                # Also get profile URL from parent link
                parent_link = username_span.find_parent('a')
                if parent_link:
                    href = parent_link.get('href', '')
                    if href.startswith('/') and not href.startswith('/p/'):
                        profile_url = f'https://www.instagram.com{href}'

            # Fallback: Find from notranslate link
            if not username:
                username_link = container.find('a', class_=re.compile(r'notranslate'))
                if username_link:
                    href = username_link.get('href', '')
                    if href and href.startswith('/'):
                        parts = href.strip('/').split('/')
                        if parts and parts[0] not in ['p', 'reel', 'c', 'explore', 'reels']:
                            username = parts[0]
                            profile_url = f'https://www.instagram.com/{username}/'

            # Fallback 2: Find from profile picture link
            if not username:
                profile_pic = container.find('img', alt=re.compile(r"'s profile picture", re.I))
                if profile_pic:
                    alt_text = profile_pic.get('alt', '')
                    match = re.match(r"([^']+)'s profile picture", alt_text, re.I)
                    if match:
                        username = match.group(1)
                        # Find the parent link for profile URL
                        parent_link = profile_pic.find_parent('a')
                        if parent_link:
                            href = parent_link.get('href', '')
                            if href.startswith('/'):
                                profile_url = f'https://www.instagram.com{href}'

            # Skip if no username or system path
            if not username:
                return None
            if username in self.config.instagram_system_paths:
                return None
            # Skip if username looks like a URL path
            if re.match(r'^(p|reel|reels|c|\d+|explore|accounts)$', username):
                return None

            # ==================== EXTRACT PROFILE PICTURE ====================
            profile_pic_url = ''
            # Try exact username match first
            img_tag = container.find('img', alt=re.compile(rf"^{re.escape(username)}'s profile picture$", re.I))
            if not img_tag:
                # Try any profile picture
                img_tag = container.find('img', alt=re.compile(r"'s profile picture", re.I))
            if img_tag:
                profile_pic_url = img_tag.get('src', '')

            # ==================== CHECK VERIFIED STATUS ====================
            is_verified = container.find('svg', {'aria-label': 'Verified'}) is not None

            # ==================== EXTRACT TIMESTAMP ====================
            timestamp = ''
            timestamp_iso = ''

            # Find time element (usually inside the comment permalink)
            time_element = container.find('time', attrs={'datetime': True})
            if time_element:
                timestamp = time_element.get_text(strip=True)  # e.g., "3w"
                timestamp_iso = time_element.get('datetime', '')  # e.g., "2025-12-23T22:01:28.000Z"

            # ==================== EXTRACT COMMENT TEXT ====================
            comment_text = ''

            # Helper function to check if class list contains a specific class
            def has_class(element, class_name):
                """Check if element has a specific class"""
                if not element:
                    return False
                classes = element.get('class', [])
                if isinstance(classes, list):
                    return class_name in classes
                elif isinstance(classes, str):
                    return class_name in classes.split()
                return False

            # Strategy 1: Find div with x1cy8zhl class (comment text container)
            # This is the most reliable - the comment text div
            text_container = None
            for div in container.find_all('div'):
                if has_class(div, 'x1cy8zhl'):
                    text_container = div
                    break

            if text_container:
                # Get the first span with dir="auto" inside - this is the comment text
                text_span = text_container.find('span', attrs={'dir': 'auto'})
                if text_span:
                    # Get all text content from this span
                    comment_text = text_span.get_text(strip=True)

            # Strategy 2: Find span with x5n08af class (comment text marker)
            if not comment_text:
                for span in container.find_all('span'):
                    if has_class(span, 'x5n08af'):
                        text = span.get_text(strip=True)
                        # Validate it's actual comment text
                        if text and len(text) > 1:
                            text_lower = text.lower()
                            # Skip if it's username, timestamp, or button text
                            if text_lower != username.lower():
                                if not re.match(r'^\d+\s*likes?$', text_lower):
                                    if not re.match(r'^\d+[wdhms]$', text):
                                        if 'reply' not in text_lower and 'translation' not in text_lower:
                                            comment_text = text
                                            break

            # Strategy 3: Fallback - find spans with dir="auto" and filter carefully
            if not comment_text:
                # Known button/non-text patterns to skip
                skip_patterns = [
                    r'^\d+\s*likes?$',       # "10 likes", "1 like"
                    r'^reply$',               # "Reply"
                    r'^see\s+translation$',   # "See translation"
                    r'^view\s+all',           # "View all X replies"
                    r'^\d+[wdhms]$',          # "3w", "2d", "1h"
                    r'^original\s+audio$',    # "Original audio"
                    r'^follow$',              # "Follow"
                    r'^hide\s+replies?$',     # "Hide replies"
                ]

                for span in container.find_all('span', attrs={'dir': 'auto'}):
                    # Skip username span (has _ap3a and _aade classes)
                    if has_class(span, '_ap3a') and has_class(span, '_aade'):
                        continue

                    # Skip if has xuxw1ft class (this is for buttons like likes, reply)
                    if has_class(span, 'xuxw1ft'):
                        continue

                    # Skip if inside a time element
                    if span.find_parent('time'):
                        continue

                    # Skip if inside a comment permalink (timestamp area)
                    parent_a = span.find_parent('a')
                    if parent_a:
                        href = parent_a.get('href', '')
                        if '/c/' in href:
                            continue

                    text = span.get_text(strip=True)

                    # Skip empty or too short
                    if not text or len(text) <= 1:
                        continue

                    # Skip if exactly username
                    if text.lower() == username.lower():
                        continue

                    # Skip if matches any skip pattern
                    text_lower = text.lower().strip()
                    should_skip = False
                    for pattern in skip_patterns:
                        if re.match(pattern, text_lower, re.I):
                            should_skip = True
                            break

                    if should_skip:
                        continue

                    # Skip if looks like "username timestamp" combined
                    if re.match(rf'^{re.escape(username)}\s*\d+[wdhms]$', text, re.I):
                        continue

                    # This is likely the comment text
                    comment_text = text
                    break

            # ==================== EXTRACT LIKES COUNT ====================
            likes_count = 0

            # Strategy 1: Find spans with xuxw1ft class and check for likes pattern
            # The xuxw1ft class is used for "X likes", "Reply", "See translation" buttons
            # We need to find the one that matches "X likes" pattern
            for span in container.find_all('span'):
                if has_class(span, 'xuxw1ft'):
                    span_text = span.get_text(strip=True)
                    likes_match = re.match(r'^(\d+(?:,\d+)*)\s*likes?$', span_text, re.I)
                    if likes_match:
                        count_str = likes_match.group(1).replace(',', '')
                        likes_count = int(count_str)
                        break

            # Strategy 2: Find inside role="button" divs
            if likes_count == 0:
                for btn_div in container.find_all('div', attrs={'role': 'button'}):
                    btn_text = btn_div.get_text(strip=True)
                    likes_match = re.match(r'^(\d+(?:,\d+)*)\s*likes?$', btn_text, re.I)
                    if likes_match:
                        count_str = likes_match.group(1).replace(',', '')
                        likes_count = int(count_str)
                        break

            # Strategy 3: Search all spans for likes pattern (last resort)
            if likes_count == 0:
                for span in container.find_all('span'):
                    text = span.get_text(strip=True)
                    likes_match = re.match(r'^(\d+(?:,\d+)*)\s*likes?$', text, re.I)
                    if likes_match:
                        count_str = likes_match.group(1).replace(',', '')
                        likes_count = int(count_str)
                        break

            # ==================== CHECK TRANSLATION AVAILABLE ====================
            has_translation = False
            translation_span = container.find('span', string=re.compile(r'see\s+translation', re.I))
            if translation_span:
                has_translation = True

            # ==================== EXTRACT REPLY COUNT ====================
            reply_count = 0

            # Strategy 1: Find div with xpdvgm7 class (view replies container)
            for div in container.find_all('div'):
                if has_class(div, 'xpdvgm7'):
                    reply_text = div.get_text(strip=True)
                    reply_match = re.search(r'View\s+all\s+(\d+)\s+repl', reply_text, re.I)
                    if reply_match:
                        reply_count = int(reply_match.group(1))
                        break

            # Strategy 2: Check sibling elements for xpdvgm7 class
            # Reply button is often a sibling, not inside the container
            if reply_count == 0:
                next_sib = container.find_next_sibling()
                if next_sib and has_class(next_sib, 'xpdvgm7'):
                    reply_text = next_sib.get_text(strip=True)
                    reply_match = re.search(r'View\s+all\s+(\d+)\s+repl', reply_text, re.I)
                    if reply_match:
                        reply_count = int(reply_match.group(1))

            # Strategy 3: Search for "View all X replies" text in spans
            if reply_count == 0:
                for span in container.find_all('span'):
                    span_text = span.get_text(strip=True)
                    reply_match = re.search(r'View\s+all\s+(\d+)\s+repl', span_text, re.I)
                    if reply_match:
                        reply_count = int(reply_match.group(1))
                        break

            # Strategy 4: Check parent's siblings (reply div might be outside our container)
            if reply_count == 0 and container.parent:
                for sibling in container.parent.find_next_siblings():
                    if has_class(sibling, 'xpdvgm7'):
                        reply_text = sibling.get_text(strip=True)
                        reply_match = re.search(r'View\s+all\s+(\d+)\s+repl', reply_text, re.I)
                        if reply_match:
                            reply_count = int(reply_match.group(1))
                            break

            # ==================== CREATE RESULT ====================
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
        """
        Extract replies for a specific comment

        Instagram HTML structure for replies:
        =====================================
        Main comment container
        └── div.xpdvgm7 (View/Hide all replies button)
        └── ul.x2lah0s.xh8yej3 (replies list)
            ├── div > div (reply 1 container)
            ├── div > div (reply 2 container)
            └── ...

        Replies are loaded dynamically when "View all X replies" is clicked.
        They appear inside a <ul> element as sibling to the replies button.
        """
        replies = []

        try:
            from bs4 import BeautifulSoup

            # Helper function to check class
            def has_class(element, class_name):
                if not element:
                    return False
                classes = element.get('class', [])
                if isinstance(classes, list):
                    return class_name in classes
                elif isinstance(classes, str):
                    return class_name in classes.split()
                return False

            # Click "View replies" button if exists
            self._expand_replies(parent_comment_id)

            # Wait for replies to load
            time.sleep(self.config.comment_reply_load_delay)

            # Re-parse HTML to get replies
            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Strategy 1: Find replies inside <ul> element near the parent comment
            # The <ul> with class x2lah0s contains replies
            reply_containers = []
            seen_container_ids = set()

            # Find the xpdvgm7 div (view/hide replies button) and look for sibling <ul>
            replies_button = None
            for div in soup.find_all('div'):
                if has_class(div, 'xpdvgm7'):
                    # Check if this contains "Hide all replies" or "View all X replies"
                    div_text = div.get_text(strip=True).lower()
                    if 'replies' in div_text or 'reply' in div_text:
                        replies_button = div
                        break

            if replies_button:
                # Find the <ul> sibling that contains replies
                # It's usually the next sibling with class x2lah0s
                ul_element = replies_button.find_next_sibling('ul')
                if ul_element:
                    # Find all comment containers inside the <ul>
                    # Each reply is inside a div > div structure
                    for reply_link in ul_element.find_all('a', href=re.compile(r'/p/[^/]+/c/\d+/?')):
                        container = self._find_comment_container(reply_link)
                        if container:
                            container_id = id(container)
                            if container_id not in seen_container_ids:
                                seen_container_ids.add(container_id)
                                reply_containers.append(container)

            # Strategy 2: Fallback - find all comment links in the page that are NOT the parent
            if not reply_containers:
                all_reply_links = soup.find_all('a', href=re.compile(r'/p/[^/]+/c/\d+/?'))

                for link in all_reply_links:
                    try:
                        # Get comment ID from this link
                        href = link.get('href', '')
                        match = re.search(r'/c/(\d+)/?', href)
                        if not match:
                            continue

                        link_comment_id = match.group(1)

                        # Skip if this is the parent comment
                        if link_comment_id == parent_comment_id:
                            continue

                        # Check if this link is inside a <ul> (reply container)
                        parent_ul = link.find_parent('ul')
                        if parent_ul:
                            container = self._find_comment_container(link)
                            if container:
                                container_id = id(container)
                                if container_id not in seen_container_ids:
                                    seen_container_ids.add(container_id)
                                    reply_containers.append(container)

                    except Exception:
                        continue

            self.logger.debug(f"Found {len(reply_containers)} reply containers for comment {parent_comment_id}")

            for container in reply_containers:
                if max_replies and len(replies) >= max_replies:
                    break

                reply = self._parse_comment_container_direct(container, soup)
                if reply and reply.comment_id != parent_comment_id:
                    # Skip caption entries
                    if reply.comment_id.startswith('caption_'):
                        continue

                    # Check if this is not a duplicate
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

        Uses locators specific to Instagram's direct URL view.
        This is a backup when BeautifulSoup parsing fails.

        Key selectors based on HTML structure:
        - Comment permalinks: a[href*="/c/"] (most reliable marker)
        - Username: span with _ap3a _aaco _aacw _aacx _aad7 _aade classes
        - Profile picture: img[alt*="profile picture"]
        - Comment text: span[dir="auto"] (excluding username span)
        - Timestamp: time[datetime]
        - Likes: div[role="button"] with "X likes" text
        """
        comments = []

        try:
            # Primary strategy: Find comment permalinks (most reliable)
            comment_links = self.page.locator('a[href*="/c/"]').all()
            self.logger.debug(f"Playwright found {len(comment_links)} comment permalinks")

            for link in comment_links:
                try:
                    # Get comment ID from permalink
                    href = link.get_attribute('href', timeout=1000)
                    if not href:
                        continue

                    match = re.search(r'/c/(\d+)/?', href)
                    if not match:
                        continue

                    comment_id = match.group(1)

                    if comment_id in seen_ids:
                        continue

                    # Navigate to container (go up the DOM tree)
                    # The container should have username, text, timestamp
                    container = link.locator('xpath=ancestor::div[.//img[contains(@alt, "profile picture")]][1]')

                    if not container.count():
                        # Try alternative: go up 6-8 levels
                        container = link.locator('xpath=ancestor::div[8]')

                    if not container.count():
                        continue

                    # Extract username
                    username = ''
                    try:
                        # Try username span first
                        username_span = container.locator('span._ap3a._aaco._aacw._aacx._aad7._aade').first
                        username = username_span.inner_text(timeout=1000)
                    except:
                        pass

                    if not username:
                        try:
                            # Try from profile picture alt
                            profile_pic = container.locator('img[alt*="profile picture"]').first
                            alt_text = profile_pic.get_attribute('alt', timeout=1000)
                            if alt_text:
                                match = re.match(r"([^']+)'s profile picture", alt_text, re.I)
                                if match:
                                    username = match.group(1)
                        except:
                            pass

                    if not username or username in self.config.instagram_system_paths:
                        continue

                    # Extract profile picture URL
                    profile_pic_url = ''
                    try:
                        profile_pic = container.locator('img[alt*="profile picture"]').first
                        profile_pic_url = profile_pic.get_attribute('src', timeout=1000) or ''
                    except:
                        pass

                    # Extract comment text
                    comment_text = ''

                    # Skip patterns - texts that are NOT comment content
                    skip_patterns = [
                        r'^\d+\s*likes?$',          # "10 likes", "1 like"
                        r'^reply$',                  # "Reply"
                        r'^see\s+translation$',      # "See translation"
                        r'^view\s+all',              # "View all X replies"
                        r'^\d+[wdhms]$',             # "3w", "2d", "1h"
                        r'^original\s+audio$',       # "Original audio"
                        r'^follow$',                 # "Follow"
                        r'^load\s+more',             # "Load more"
                        r'^hide\s+replies?$',        # "Hide replies"
                    ]

                    try:
                        # Get all spans with dir="auto"
                        text_spans = container.locator('span[dir="auto"]').all()
                        for span in text_spans:
                            try:
                                text = span.inner_text(timeout=500)

                                # Skip empty or too short
                                if not text or len(text) <= 1:
                                    continue

                                # Skip if exactly the username
                                if text.lower() == username.lower():
                                    continue

                                # Skip if matches skip patterns
                                text_lower = text.lower().strip()
                                should_skip = False
                                for pattern in skip_patterns:
                                    if re.match(pattern, text_lower, re.I):
                                        should_skip = True
                                        break

                                if should_skip:
                                    continue

                                # Skip if it looks like username + timestamp combined
                                if re.match(rf'^{re.escape(username)}\s*\d+[wdhms]$', text, re.I):
                                    continue

                                # This is likely the comment text
                                comment_text = text
                                break
                            except:
                                continue
                    except:
                        pass

                    if not comment_text:
                        continue

                    # Extract timestamp
                    timestamp = ''
                    timestamp_iso = ''
                    try:
                        time_el = container.locator('time[datetime]').first
                        timestamp = time_el.inner_text(timeout=1000)
                        timestamp_iso = time_el.get_attribute('datetime', timeout=1000) or ''
                    except:
                        pass

                    # Extract likes count
                    likes_count = 0
                    try:
                        button_divs = container.locator('div[role="button"]').all()
                        for btn in button_divs:
                            try:
                                btn_text = btn.inner_text(timeout=500)
                                likes_match = re.match(r'^(\d+)\s*likes?$', btn_text.strip(), re.I)
                                if likes_match:
                                    likes_count = int(likes_match.group(1))
                                    break
                            except:
                                continue
                    except:
                        pass

                    # Extract reply count
                    reply_count = 0
                    try:
                        all_text = container.inner_text(timeout=1000)
                        reply_match = re.search(r'View\s+all\s+(\d+)\s+repl', all_text, re.I)
                        if reply_match:
                            reply_count = int(reply_match.group(1))
                    except:
                        pass

                    # Build comment URL
                    comment_url = f'https://www.instagram.com{href}' if href.startswith('/') else href

                    author = CommentAuthor(
                        username=username,
                        profile_url=f'https://www.instagram.com/{username}/',
                        profile_picture_url=profile_pic_url
                    )

                    comment = CommentData(
                        comment_id=comment_id,
                        author=author,
                        text=comment_text,
                        timestamp=timestamp,
                        timestamp_iso=timestamp_iso,
                        likes_count=likes_count,
                        reply_count=reply_count,
                        comment_url=comment_url,
                        is_reply=False
                    )

                    comments.append(comment)
                    self.logger.debug(f"Playwright extracted: @{username} - {comment_text[:30]}...")

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
