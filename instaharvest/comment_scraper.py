"""
Instagram Scraper - Comment Data Extractor
Full comment scraping with likes, replies, timestamps, and user info

PROFESSIONAL VERSION with:
- Full comment extraction (text, likes, timestamp, reply count)
- User info extraction (username, profile picture)
- Reply extraction (nested comments)
- Real-time progress tracking
- Intelligent scrolling for all comments
- Error recovery and retry logic
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
    Instagram Comment Scraper - PROFESSIONAL VERSION

    Extracts full comment data from Instagram posts:
    - Comment text
    - Author info (username, profile pic, verified status)
    - Likes count
    - Timestamp (human readable + ISO format)
    - Reply count
    - Nested replies
    - Comment URL/ID

    Features:
    - Intelligent scrolling to load all comments
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

        self.logger.info("CommentScraper ready (Professional Mode)")

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
            PostCommentsData object with all comments
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

    def _scrape_all_comments(
        self,
        max_comments: Optional[int],
        include_replies: bool,
        max_replies_per_comment: Optional[int],
        progress_callback: Optional[callable]
    ) -> List[CommentData]:
        """
        Scrape all comments with intelligent scrolling and button clicking

        Algorithm:
        1. Extract visible comments
        2. Try to click "Load more comments" plus (+) button if exists
        3. If button clicked, wait for comments to load, repeat from step 1
        4. If no button, try scrolling to reveal more comments
        5. If no new comments AND no button for 3 consecutive attempts, stop

        Uses intelligent scrolling to load and extract all comments
        """
        comments = []
        seen_comment_ids = set()
        no_progress_count = 0  # Count of attempts with no new comments AND no button
        scroll_attempt = 0
        max_no_progress = 3  # Stop after 3 attempts with no progress

        self.logger.info("Starting comment extraction...")

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
                    # Check max limit
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

            # Try to click "Load more comments" plus button
            button_exists = self._check_load_more_button_exists()
            clicked_button = False

            if button_exists:
                clicked_button = self._load_more_comments()
                if clicked_button:
                    self.logger.debug(f"Clicked 'Load more comments' button, waiting for comments to load...")
                    # Wait for comments to load after clicking button
                    time.sleep(random.uniform(
                        self.config.comment_scroll_delay_min,
                        self.config.comment_scroll_delay_max
                    ))
                    # Reset no progress counter since we clicked button
                    no_progress_count = 0
                    continue  # Go back to extract new comments

            # If no button found, try scrolling
            if not clicked_button:
                self._scroll_comment_section()
                self.logger.debug("Scrolled comment section to load more")
                # Wait for content to load after scroll
                time.sleep(random.uniform(
                    self.config.comment_scroll_delay_min,
                    self.config.comment_scroll_delay_max
                ))

            # Check if we made any progress (new comments or button click)
            if not found_new_comments and not clicked_button and not button_exists:
                no_progress_count += 1
                self.logger.debug(
                    f"No progress attempt {no_progress_count}/{max_no_progress} "
                    f"(no new comments, no button)"
                )

                # Stop if no progress after max attempts
                if no_progress_count >= max_no_progress:
                    self.logger.info(
                        f"No new comments and no 'Load more' button after "
                        f"{no_progress_count} attempts, comments exhausted"
                    )
                    break
            else:
                # Reset counter if we found something
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
        Extract all currently visible comments

        Uses BeautifulSoup for reliable extraction
        """
        comments = []

        try:
            from bs4 import BeautifulSoup

            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Find comment containers
            # Based on user-provided HTML structure
            comment_containers = soup.find_all('ul', class_='_a9ym')

            for container in comment_containers:
                try:
                    comment = self._parse_comment_container(container, soup)

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

        except ImportError:
            self.logger.warning("BeautifulSoup not available, using Playwright extraction")
            comments = self._extract_comments_playwright(seen_ids)
        except Exception as e:
            self.logger.error(f"Comment extraction failed: {e}")

        return comments

    def _parse_comment_container(self, container, soup) -> Optional[CommentData]:
        """
        Parse a single comment container element

        Based on the HTML structure provided by user:
        - Container: ul._a9ym > li._a9zj._a9zl
        - Username: a[href="/username/"] inside h3
        - Profile pic: img[alt="username's profile picture"]
        - Comment text: span._ap3a._aaco._aacu._aacx._aad7._aade[dir="auto"]
        - Timestamp: time._a9ze._a9zf[datetime][title]
        - Likes: button._a9ze with "X like" or "X likes"
        - Comment link: a[href="/p/POST_ID/c/COMMENT_ID/"]
        """
        try:
            # Find the li element (main comment container)
            li_element = container.find('li', class_='_a9zj')
            if not li_element:
                # Try to find li with both classes
                li_element = container.find('li', class_=re.compile(r'_a9zj'))
                if not li_element:
                    return None

            # Extract username from h3 > div > span > a
            username = ''
            # Method 1: Find in h3 tag
            h3_tag = li_element.find('h3')
            if h3_tag:
                username_link = h3_tag.find('a', href=re.compile(r'^/[^/]+/$'))
                if username_link:
                    href = username_link.get('href', '')
                    username = href.strip('/').split('/')[-1]

            # Method 2: Fallback - find first a tag with username pattern
            if not username:
                all_links = li_element.find_all('a', href=re.compile(r'^/[^/]+/$'))
                for link in all_links:
                    href = link.get('href', '')
                    potential_username = href.strip('/').split('/')[-1]
                    # Filter out system paths and post/comment links
                    if potential_username and potential_username not in self.config.instagram_system_paths:
                        if not re.match(r'^\d+$', potential_username):  # Not just numbers
                            username = potential_username
                            break

            # Filter out system paths
            if username in self.config.instagram_system_paths:
                return None

            if not username:
                return None

            # Extract profile picture URL
            profile_pic_url = ''
            img_tag = li_element.find('img', alt=re.compile(rf"{re.escape(username)}'s profile picture", re.IGNORECASE))
            if img_tag:
                profile_pic_url = img_tag.get('src', '')
            else:
                # Fallback: any profile picture img
                img_tag = li_element.find('img', alt=re.compile(r"'s profile picture"))
                if img_tag:
                    profile_pic_url = img_tag.get('src', '')

            # Check verified status
            is_verified = li_element.find('svg', {'aria-label': 'Verified'}) is not None

            # Extract comment text - specific selector from HTML
            comment_text = ''
            # Method 1: Exact class match
            text_span = li_element.find('span', class_='_ap3a _aaco _aacu _aacx _aad7 _aade')
            if text_span:
                comment_text = text_span.get_text(strip=True)

            # Method 2: Partial class match
            if not comment_text:
                text_span = li_element.find('span', class_=re.compile(r'_ap3a'))
                if text_span and text_span.get('dir') == 'auto':
                    comment_text = text_span.get_text(strip=True)

            # Method 3: Look for div.xt0psk2 > span with dir="auto"
            if not comment_text:
                text_div = li_element.find('div', class_='xt0psk2')
                if text_div:
                    text_span = text_div.find('span', {'dir': 'auto'})
                    if text_span:
                        comment_text = text_span.get_text(strip=True)

            # Method 4: Fallback - any span with dir="auto" that's not empty
            if not comment_text:
                auto_spans = li_element.find_all('span', {'dir': 'auto'})
                for span in auto_spans:
                    text = span.get_text(strip=True)
                    # Skip if it's just a username or timestamp
                    if text and len(text) > 1 and text != username:
                        # Check if this span doesn't contain a link (usernames have links)
                        if not span.find('a'):
                            comment_text = text
                            break

            # Extract timestamp - time._a9ze._a9zf
            timestamp = ''
            timestamp_iso = ''
            time_element = li_element.find('time', class_=re.compile(r'_a9ze'))
            if time_element:
                timestamp = time_element.get('title', '') or time_element.get_text(strip=True)
                timestamp_iso = time_element.get('datetime', '')
            else:
                # Fallback: any time element
                time_element = li_element.find('time')
                if time_element:
                    timestamp = time_element.get('title', '') or time_element.get_text(strip=True)
                    timestamp_iso = time_element.get('datetime', '')

            # Extract comment URL and ID from link like /p/POST_ID/c/COMMENT_ID/
            comment_url = ''
            comment_id = ''
            comment_link = li_element.find('a', href=re.compile(r'/p/[^/]+/c/\d+/'))
            if comment_link:
                href = comment_link.get('href', '')
                comment_url = 'https://www.instagram.com' + href
                # Extract comment ID from URL
                match = re.search(r'/c/(\d+)/', href)
                if match:
                    comment_id = match.group(1)

            # Generate comment ID if not found
            if not comment_id:
                comment_id = f"{username}_{abs(hash(comment_text))}"

            # Extract likes count from button._a9ze
            likes_count = 0
            # Find all buttons with class _a9ze
            buttons = li_element.find_all('button', class_='_a9ze')
            for button in buttons:
                button_text = button.get_text(strip=True)
                # Match "1 like", "2 likes", etc.
                likes_match = re.search(r'(\d+)\s*like', button_text, re.IGNORECASE)
                if likes_match:
                    likes_count = int(likes_match.group(1))
                    break

            # Fallback: search all spans for like count
            if likes_count == 0:
                all_spans = li_element.find_all('span')
                for span in all_spans:
                    text = span.get_text(strip=True)
                    if 'like' in text.lower():
                        match = re.search(r'(\d+)', text)
                        if match:
                            likes_count = int(match.group(1))
                            break

            # Check if has "See translation" option
            has_translation = False
            translation_div = li_element.find(string=re.compile(r'See\s*translation', re.IGNORECASE))
            if translation_div:
                has_translation = True

            # Extract reply count (if "View X replies" is shown)
            reply_count = 0
            view_replies = li_element.find(string=re.compile(r'View.*repl', re.IGNORECASE))
            if view_replies:
                match = re.search(r'(\d+)', str(view_replies))
                if match:
                    reply_count = int(match.group(1))

            # Create author object
            author = CommentAuthor(
                username=username,
                profile_url=f'https://www.instagram.com/{username}/',
                profile_picture_url=profile_pic_url,
                is_verified=is_verified
            )

            # Create comment object
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
            # Click "View replies" button if exists
            self._expand_replies(parent_comment_id)

            # Wait for replies to load
            time.sleep(self.config.comment_reply_load_delay)

            # Re-parse HTML to get replies
            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Find reply containers (usually nested under main comment)
            # Look for nested comment structures
            reply_containers = soup.find_all('ul', class_='_a9ym')

            for container in reply_containers:
                if max_replies and len(replies) >= max_replies:
                    break

                reply = self._parse_comment_container(container, soup)
                if reply and reply.comment_id != parent_comment_id:
                    reply.is_reply = True
                    reply.parent_comment_id = parent_comment_id
                    replies.append(reply)

        except Exception as e:
            self.logger.debug(f"Reply extraction error: {e}")

        return replies

    def _expand_replies(self, comment_id: str) -> bool:
        """Click 'View replies' button for a comment"""
        try:
            # Look for "View replies" or "View X replies" button
            view_replies_buttons = self.page.locator(
                'button:has-text("View"), span:has-text("View")'
            ).filter(has_text=re.compile(r'repl', re.IGNORECASE))

            count = view_replies_buttons.count()
            for i in range(count):
                try:
                    button = view_replies_buttons.nth(i)
                    if button.is_visible():
                        button.click(timeout=2000)
                        time.sleep(self.config.popup_animation_delay)
                        return True
                except:
                    continue

        except Exception as e:
            self.logger.debug(f"Expand replies failed: {e}")

        return False

    def _load_more_comments(self) -> bool:
        """
        Click 'Load more comments' button (plus button) to load more comments

        Instagram shows a plus (+) button with:
        - Button class: _abl-
        - SVG with aria-label="Load more comments"
        - Title: "Load more comments"

        Returns:
            True if button was found and clicked (more comments loading)
        """
        try:
            # Method 1: Find button by SVG aria-label (most reliable)
            # The plus button has SVG with aria-label="Load more comments"
            load_more_button = self.page.locator('button:has(svg[aria-label="Load more comments"])').first

            try:
                if load_more_button.is_visible(timeout=1000):
                    load_more_button.click(timeout=2000)
                    self.logger.debug("Clicked 'Load more comments' plus button (via SVG aria-label)")
                    time.sleep(self.config.popup_animation_delay)
                    return True
            except:
                pass

            # Method 2: Find by button class _abl-
            try:
                plus_button = self.page.locator('button._abl-').first
                if plus_button.is_visible(timeout=1000):
                    plus_button.click(timeout=2000)
                    self.logger.debug("Clicked 'Load more comments' plus button (via class _abl-)")
                    time.sleep(self.config.popup_animation_delay)
                    return True
            except:
                pass

            # Method 3: Find by SVG title element
            try:
                title_button = self.page.locator('button:has(svg title:has-text("Load more comments"))').first
                if title_button.is_visible(timeout=1000):
                    title_button.click(timeout=2000)
                    self.logger.debug("Clicked 'Load more comments' plus button (via title)")
                    time.sleep(self.config.popup_animation_delay)
                    return True
            except:
                pass

            # Method 4: Fallback - Various text patterns for loading more comments
            load_more_patterns = [
                'View all',
                'Load more',
                'more comments',
                'View previous'
            ]

            for pattern in load_more_patterns:
                try:
                    button = self.page.locator(f'button:has-text("{pattern}")').first
                    if button.is_visible(timeout=500):
                        button.click(timeout=2000)
                        self.logger.debug(f"Clicked '{pattern}' button")
                        time.sleep(self.config.popup_animation_delay)
                        return True
                except:
                    continue

            # Method 5: Try clicking any visible "View" button in comment section
            try:
                view_buttons = self.page.locator('div[role="button"]:has-text("View")').all()
                for btn in view_buttons[:3]:  # Try first 3
                    try:
                        if btn.is_visible():
                            btn.click(timeout=1000)
                            time.sleep(self.config.ui_animation_delay)
                            return True
                    except:
                        continue
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Load more comments failed: {e}")

        return False

    def _check_load_more_button_exists(self) -> bool:
        """
        Check if 'Load more comments' plus button exists on page

        Returns:
            True if the button is visible
        """
        try:
            # Check by SVG aria-label
            button = self.page.locator('button:has(svg[aria-label="Load more comments"])')
            if button.count() > 0 and button.first.is_visible(timeout=500):
                return True
        except:
            pass

        try:
            # Check by button class
            button = self.page.locator('button._abl-')
            if button.count() > 0 and button.first.is_visible(timeout=500):
                return True
        except:
            pass

        return False

    def _scroll_comment_section(self) -> None:
        """
        Scroll within the comment section to load more comments

        Instagram's comment section structure:
        - The comment list (ul._a9z6._a9za) is NOT scrollable
        - The scrollable container is a parent div with overflow-y: auto/scroll
        - We need to find and scroll that parent container

        Multiple scroll strategies are used for robustness
        """
        scroll_success = False

        # Strategy 1: Find scrollable parent of comment section
        try:
            scroll_success = self.page.evaluate('''() => {
                // Find the comment list
                const commentList = document.querySelector('ul._a9z6._a9za');
                if (!commentList) return false;

                // Find scrollable parent by traversing up the DOM
                let parent = commentList.parentElement;
                let scrolled = false;

                while (parent && parent !== document.body) {
                    const style = window.getComputedStyle(parent);
                    const overflowY = style.overflowY;
                    const overflow = style.overflow;

                    // Check if this element is scrollable
                    if (overflowY === 'auto' || overflowY === 'scroll' ||
                        overflow === 'auto' || overflow === 'scroll') {
                        // Check if it actually has scrollable content
                        if (parent.scrollHeight > parent.clientHeight) {
                            const scrollAmount = parent.clientHeight * 0.7;
                            parent.scrollTop += scrollAmount;
                            scrolled = true;
                            break;
                        }
                    }
                    parent = parent.parentElement;
                }

                return scrolled;
            }''')

            if scroll_success:
                self.logger.debug("Scrolled comment section via scrollable parent")
                return
        except Exception as e:
            self.logger.debug(f"Scrollable parent strategy failed: {e}")

        # Strategy 2: Scroll dialog container (for modal views)
        try:
            dialog = self.page.locator('div[role="dialog"]').first
            if dialog.is_visible():
                scroll_success = dialog.evaluate('''el => {
                    // Find scrollable div inside dialog
                    const scrollableDivs = el.querySelectorAll('div');
                    for (const div of scrollableDivs) {
                        const style = window.getComputedStyle(div);
                        if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                            div.scrollHeight > div.clientHeight) {
                            div.scrollTop += div.clientHeight * 0.7;
                            return true;
                        }
                    }
                    return false;
                }''')

                if scroll_success:
                    self.logger.debug("Scrolled comment section via dialog container")
                    return
        except Exception as e:
            self.logger.debug(f"Dialog scroll strategy failed: {e}")

        # Strategy 3: Scroll to last comment element to trigger lazy loading
        try:
            last_comment = self.page.locator('ul._a9ym').last
            if last_comment.is_visible():
                last_comment.scroll_into_view_if_needed()
                self.logger.debug("Scrolled to last comment element")
                return
        except Exception as e:
            self.logger.debug(f"Scroll to last comment failed: {e}")

        # Strategy 4: Find any scrollable element with comments
        try:
            scroll_success = self.page.evaluate('''() => {
                // Find all potentially scrollable containers
                const allDivs = document.querySelectorAll('div');
                for (const div of allDivs) {
                    const style = window.getComputedStyle(div);
                    // Check if scrollable and contains comments
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                        div.scrollHeight > div.clientHeight &&
                        div.querySelector('ul._a9ym')) {
                        div.scrollTop += div.clientHeight * 0.7;
                        return true;
                    }
                }
                return false;
            }''')

            if scroll_success:
                self.logger.debug("Scrolled via generic scrollable container with comments")
                return
        except Exception as e:
            self.logger.debug(f"Generic scrollable container strategy failed: {e}")

        # Strategy 5: Keyboard scroll (Page Down)
        try:
            self.page.keyboard.press('PageDown')
            self.logger.debug("Used keyboard PageDown for scroll")
            return
        except Exception as e:
            self.logger.debug(f"Keyboard scroll failed: {e}")

        # Strategy 6: Window scroll as last resort
        try:
            self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.5)')
            self.logger.debug("Used window scroll fallback")
        except Exception as e:
            self.logger.debug(f"Window scroll fallback failed: {e}")

    def _extract_comments_playwright(self, seen_ids: set) -> List[CommentData]:
        """
        Extract comments using Playwright (fallback method)

        Used when BeautifulSoup is not available
        """
        comments = []

        try:
            # Find all comment containers
            containers = self.page.locator('ul._a9ym').all()

            for container in containers:
                try:
                    # Extract username
                    username_link = container.locator('a[href^="/"]').first
                    href = username_link.get_attribute('href', timeout=1000)
                    username = href.strip('/').split('/')[-1] if href else ''

                    if not username or username in self.config.instagram_system_paths:
                        continue

                    # Extract comment text
                    text_span = container.locator('span[dir="auto"]').first
                    comment_text = text_span.inner_text(timeout=1000) if text_span.count() > 0 else ''

                    # Extract timestamp
                    time_el = container.locator('time').first
                    timestamp = time_el.get_attribute('title', timeout=1000) if time_el.count() > 0 else ''
                    timestamp_iso = time_el.get_attribute('datetime', timeout=1000) if time_el.count() > 0 else ''

                    # Generate ID
                    comment_id = f"{username}_{hash(comment_text)}"

                    if comment_id in seen_ids:
                        continue

                    # Create author
                    author = CommentAuthor(
                        username=username,
                        profile_url=f'https://www.instagram.com/{username}/'
                    )

                    # Create comment
                    comment = CommentData(
                        comment_id=comment_id,
                        author=author,
                        text=comment_text,
                        timestamp=timestamp,
                        timestamp_iso=timestamp_iso,
                        likes_count=0,
                        reply_count=0,
                        comment_url='',
                        is_reply=False
                    )

                    comments.append(comment)

                except Exception as e:
                    self.logger.debug(f"Playwright comment extraction error: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Playwright extraction failed: {e}")

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
                        comments=[]
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

        self.logger.info(f"\n{'='*60}")
        self.logger.info("COMMENT SCRAPING COMPLETE!")
        self.logger.info(f"Posts processed: {len(results)}")
        self.logger.info(f"Total comments: {total_comments}")
        self.logger.info(f"Total replies: {total_replies}")
        self.logger.info(f"{'='*60}")

        return results
