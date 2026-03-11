import time
import random
import re
from typing import List, Optional, Any, Callable
from dataclasses import dataclass, field

from .base import BaseScraper
from .config import ScraperConfig
from .parser import CommentParser
from .models import Comment, CommentAuthor

@dataclass
class PostCommentsData:
    """All comments for a single post"""
    post_url: str
    post_id: str
    total_comments_scraped: int
    total_replies_scraped: int
    comments: List[Comment]
    scraped_at: str = ''
    scraping_duration_seconds: float = 0.0
    collaborators: List[Any] = field(default_factory=list)

    def to_dict(self):
        return {
            'post_url': self.post_url,
            'post_id': self.post_id,
            'total_comments': self.total_comments_scraped,
            'comments': [c.model_dump() for c in self.comments],
            'duration': self.scraping_duration_seconds
        }

    def get_all_comments_flat(self):
        """Yields all comments and replies in a flat sequence (Parent -> Replies)"""
        for comment in self.comments:
            yield comment
            for reply in comment.replies:
                yield reply

class CommentScraper(BaseScraper):
    def __init__(self, config: Optional[ScraperConfig] = None, enable_diagnostics: bool = True):
        super().__init__(config)
        self.parser = CommentParser()
        self.logger.info("Refactored CommentScraper Ready")

    def scrape_stream(
        self,
        post_url: str,
        *,
        target_count: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_replies: bool = True
    ):
        """
        Generator that yields comments incrementally as they are scraped.
        Fixes 'DOM Explosion' by allowing data to be processed/saved in real-time.
        """
        self.logger.info(f"Starting Stream Scrape: {post_url}")
        
        # ═══════ AUTO BROWSER SETUP (standalone mode) ═══════
        is_shared_browser = self.page is not None and self.browser is not None
        if not is_shared_browser:
            self.logger.debug("Setting up new browser session (standalone mode)")
            session_data = self.load_session()
            self.setup_browser(session_data)

        self.goto_url(post_url)
        time.sleep(self.config.comment_initial_load_delay) # Initial load

        # ═══════ OPEN COMMENTS DIALOG (Feed View Detection) ═══════
        # Instagram sometimes shows posts in feed view where comments
        # are hidden. We need to click "View all X comments" to open
        # the comments dialog/panel.
        self._open_comments_dialog()

        seen_ids = set()
        last_height = 0
        no_change_count = 0
        max_retries = 8
        total_yielded = 0

        # Loop until max reached or no new content
        while True:
            # 1. Expand Replies & Load More
            if include_replies:
                self._expand_replies()

            try:
                load_more = self.page.locator(self.config.comment_ui_text['load_more'])
                if load_more.count() > 0 and load_more.first.is_visible():
                    load_more.first.click()
                    time.sleep(2)
                    no_change_count = 0
            except Exception: pass

            # 2. Scroll logic
            self._smart_scroll()

            # 3. Parse *current* DOM state
            html = self.page.content()
            current_batch = self.parser.parse_html(html)
            
            self.logger.debug(f"DEBUG: parser returned {len(current_batch)} comments.")
            
            # 4. Filter and Yield New Comments
            new_comments_in_batch = []
            for comment in current_batch:
                if comment.id not in seen_ids:
                    seen_ids.add(comment.id)
                    new_comments_in_batch.append(comment)
                    
                    # Also track replies
                    for reply in comment.replies:
                        seen_ids.add(reply.id)
            
            # Yield new comments
            if new_comments_in_batch:
                self.logger.info(f"Yielding {len(new_comments_in_batch)} new comments...")
                for c in new_comments_in_batch:
                    yield c
                    total_yielded += 1
                    
                    if target_count is not None and total_yielded >= target_count:
                        self.logger.info("Reached max comments limit via stream.")
                        return

                no_change_count = 0
            else:
                no_change_count += 1
                self.logger.debug(f"No new comments via stream. Attempt {no_change_count}/{max_retries}")
                if no_change_count > max_retries:
                    break

            # Check total count for exit condition
            # Use time tags as proxy since /c/ permalinks no longer exist
            if target_count is not None and total_yielded >= target_count:
                return

    def scrape(
        self, 
        post_url: str, 
        *, 
        target_count: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_replies: bool = True,
        max_replies_per_comment: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> PostCommentsData:
        """
        Legacy method wrapper around scrape_stream for backward compatibility.
        """
        start_time = time.time()
        comments = []
        
        # Consume the stream
        for comment in self.scrape_stream(
            post_url, 
            target_count=target_count, 
            date_from=date_from,
            date_to=date_to,
            include_replies=include_replies
        ):
            comments.append(comment)
            
        duration = time.time() - start_time
        
        return PostCommentsData(
            post_url=post_url,
            post_id=self._extract_post_id(post_url),
            total_comments_scraped=len(comments),
            total_replies_scraped=sum(c.reply_count for c in comments),
            comments=comments,
            scraping_duration_seconds=duration
        )

    def _smart_scroll(self):
        """Helper for scrolling logic"""
        try:
            # Try JS Scroll on dialog
            scrolled = self.page.evaluate('''() => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return false;
                const list = dialog.querySelector('ul._a9z6, ul.x78zum5') || dialog.querySelector('div.x78zum5.xdt5ytf');
                if (list) {
                    list.scrollIntoView({ behavior: "smooth", block: "end" });
                    return true;
                }
                const scrollables = dialog.querySelectorAll('div');
                for (const s of scrollables) {
                    if (s.scrollHeight > s.clientHeight && (getComputedStyle(s).overflowY === 'auto' || getComputedStyle(s).overflowY === 'scroll')) {
                        s.scrollTop = s.scrollHeight;
                        return true;
                    }
                }
                return false;
            }''')
            
            if not scrolled:
                # Mouse fallback
                dialog_box = self.page.locator('div[role="dialog"]').first
                if dialog_box.is_visible():
                    box = dialog_box.bounding_box()
                    if box:
                        self.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                        self.page.mouse.wheel(0, 1000)
                else:
                    self.page.keyboard.press("PageDown")
                    
            time.sleep(2.5)
        except Exception: pass

    def _open_comments_dialog(self):
        """
        Detects if the post is in feed view (no comments visible) and clicks
        'View all X comments' to open the comments dialog.
        
        Instagram sometimes loads posts in a feed layout where comments
        are hidden behind a 'View all X comments' link.
        """
        try:
            # Check if comments dialog is already open
            dialog = self.page.locator('div[role="dialog"]')
            if dialog.count() > 0 and dialog.first.is_visible():
                self.logger.info("Comments dialog already open.")
                return

            # Strategy 1: Click "View all X comments" link 
            # This appears in feed view as a clickable text
            view_all_selectors = [
                # XPath: any element containing "View all" and "comments"
                '//a[contains(text(), "View all") and contains(text(), "comment")]',
                '//span[contains(text(), "View all") and contains(text(), "comment")]',
                '//div[@role="button"][contains(., "View all") and contains(., "comment")]',
                # Direct text match
                'a:has-text("View all")',
                'span:has-text("View all")',
            ]
            
            clicked = False
            for selector in view_all_selectors:
                try:
                    el = self.page.locator(selector)
                    if el.count() > 0:
                        for i in range(el.count()):
                            txt = el.nth(i).text_content() or ""
                            if "comment" in txt.lower():
                                self.logger.info(f"Found 'View all comments' button: '{txt.strip()}'")
                                el.nth(i).click()
                                clicked = True
                                break
                    if clicked:
                        break
                except Exception:
                    continue
            
            if clicked:
                self.logger.info("Clicked 'View all comments'. Waiting for dialog to load...")
                time.sleep(self.config.comment_dialog_open_delay)  # Wait for comments dialog to open and load
                
                # Verify dialog opened
                try:
                    self.page.wait_for_selector('div[role="dialog"]', timeout=5000)
                    self.logger.info("Comments dialog opened successfully.")
                except Exception:
                    # Dialog might not appear, comments might load inline
                    self.logger.debug("No dialog appeared, comments may load inline.")
            else:
                # Strategy 2: Click the comment icon (speech bubble SVG)
                # This also opens the comments section
                try:
                    comment_icon = self.page.locator('svg[aria-label="Comment"]')
                    if comment_icon.count() > 0:
                        self.logger.info("Clicking comment icon to open comments...")
                        comment_icon.first.click()
                        time.sleep(self.config.comment_network_wait_delay)
                except Exception:
                    pass
                    
                self.logger.debug("No 'View all comments' button found. Post may already show comments or have none.")
                
        except Exception as e:
            self.logger.error(f"Error opening comments dialog: {e}")

    def _extract_post_id(self, url: str) -> str:
        match = re.search(r'/(?:p|reel)/([A-Za-z0-9_-]+)/?', url)
        return match.group(1) if match else ''

    def _expand_replies(self):
        """
        Clicks "View replies" buttons to load nested content.
        Uses robust XPath to handle newlines and variations.
        """
        try:
            # XPath: Div role=button containing 'View' and 'replies' in text descendants
            # This handles "View all 8\n replies" correctly.
            # Constructed dynamically from config for localization
            view_text = self.config.comment_ui_text['view_replies'][0]
            replies_text = self.config.comment_ui_text['view_replies'][1]
            
            xpath = f'//div[@role="button"][contains(., "{view_text}") and contains(., "{replies_text}")]'
            
            buttons = self.page.locator(xpath).all()
            
            # Fallback to Span if no Divs found
            if not buttons:
                 xpath_span = f'//span[contains(., "{view_text}") and contains(., "{replies_text}")]'
                 buttons = self.page.locator(xpath_span).all()

            if buttons:
                # Log this clearly so we know if selectors work
                self.logger.info(f"Found {len(buttons)} potential 'View replies' buttons.")

            clicked_count = 0
            for i, btn in enumerate(buttons):
                try:
                    if btn.is_visible():
                        txt = btn.text_content().strip()
                        if "Hide" in txt: 
                            continue
                        
                        # Ensure interaction
                        btn.scroll_into_view_if_needed()
                        btn.click()
                        clicked_count += 1
                        time.sleep(0.5) 
                except Exception as e:
                    self.logger.debug(f"Failed to click button {i}: {e}")
                    continue
            
            if clicked_count > 0:
                self.logger.info(f"Clicked {clicked_count} 'View replies' buttons. Waiting for load...")
                time.sleep(self.config.comment_network_wait_delay) # Wait longer for network response
        except Exception as e:
            self.logger.error(f"Error expanding replies: {e}")
