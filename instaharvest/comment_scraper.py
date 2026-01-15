import time
import random
import re
from typing import List, Optional, Any
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

    def to_dict(self):
        return {
            'post_url': self.post_url,
            'post_id': self.post_id,
            'total_comments': self.total_comments_scraped,
            'comments': [c.to_dict() for c in self.comments],
            'duration': self.scraping_duration_seconds
        }

class CommentScraper(BaseScraper):
    def __init__(self, config: Optional[ScraperConfig] = None, enable_diagnostics: bool = True):
        super().__init__(config)
        self.parser = CommentParser()
        self.logger.info("Refactored CommentScraper Ready")

    def scrape(
        self, 
        post_url: str, 
        *, 
        max_comments: Optional[int] = None,
        include_replies: bool = True,
        max_replies_per_comment: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> PostCommentsData:
        start_time = time.time()
        self.logger.info(f"Scraping: {post_url}")
        
        self.goto_url(post_url)
        time.sleep(3) # Initial load
        
        # Scroll and Load
        self._load_all_comments(max_comments, include_replies)
        
        # Parse
        html = self.page.content()
        comments = self.parser.parse_html(html)
        
        # Post-process (filtering/limiting if needed)
        if max_comments:
            comments = comments[:max_comments]
            
        duration = time.time() - start_time
        
        return PostCommentsData(
            post_url=post_url,
            post_id=self._extract_post_id(post_url),
            total_comments_scraped=len(comments),
            total_replies_scraped=sum(c.reply_count for c in comments),
            comments=comments,
            scraping_duration_seconds=duration
        )

    def _extract_post_id(self, url: str) -> str:
        match = re.search(r'/(?:p|reel)/([A-Za-z0-9_-]+)/?', url)
        return match.group(1) if match else ''

    def _load_all_comments(self, max_comments: Optional[int], include_replies: bool):
        """
        Robustly scrolls, clicks 'Load more', and expands replies.
        Strategy: JS Scroll -> Mouse Wheel -> Keyboard -> Button Click
        """
        last_height = 0
        no_change_count = 0
        max_retries = 20
        
        while True:
            # 1. Expand Replies if requested (Do this frequently to keep DOM fresh)
            if include_replies:
                self._expand_replies()

            # 2. Check for "Load more comments" button (SVG with plus icon)
            try:
                load_more = self.page.locator('svg[aria-label="Load more comments"]')
                if load_more.count() > 0 and load_more.first.is_visible():
                    self.logger.info("Found 'Load more comments' button, clicking...")
                    load_more.first.click()
                    time.sleep(2)
                    no_change_count = 0
                    continue # Loop immediately to handle new content
            except: pass

            # 3. Scroll Strategy: Mixed Approach
            try:
                # A. Try JS Scroll on the dialog (Cleanest)
                scrolled_via_js = self.page.evaluate('''() => {
                    const dialog = document.querySelector('div[role="dialog"]');
                    if (!dialog) return false;
                    
                    // Find the scrollable list container
                    const list = dialog.querySelector('ul._a9z6, ul.x78zum5') || dialog.querySelector('div.x78zum5.xdt5ytf');
                    if (list) {
                        // Scroll that specific element
                        list.scrollIntoView({ behavior: "smooth", block: "end" });
                        return true;
                    }
                    
                    // Fallback to scrolling the dialog 
                    // (Often the dialog itself isn't scrollable, but a child div is)
                    const scrollables = dialog.querySelectorAll('div');
                    for (const s of scrollables) {
                        if (s.scrollHeight > s.clientHeight && (getComputedStyle(s).overflowY === 'auto' || getComputedStyle(s).overflowY === 'scroll')) {
                            s.scrollTop = s.scrollHeight;
                            return true;
                        }
                    }
                    return false;
                }''')
                
                # B. Mouse Wheel Simulation (Robust for lazy-loading)
                # Mouse over the center of the dialog and scroll down
                if not scrolled_via_js or no_change_count > 1:
                    dialog_box = self.page.locator('div[role="dialog"]').first
                    if dialog_box.is_visible():
                        box = dialog_box.bounding_box()
                        if box:
                            self.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                            self.page.mouse.wheel(0, 1000) # Big scroll down
                            time.sleep(0.5)
            
                # C. Keyboard fallback (Last resort)
                if no_change_count > 3:
                    self.page.keyboard.press("PageDown")

            except Exception as e:
                self.logger.debug(f"Scroll error: {e}")
                pass

            time.sleep(2.5) # Wait for network

            # 4. Check Progress
            current_comment_count = self.page.locator('a[href*="/c/"]').count()
            self.logger.info(f"Comments found: {current_comment_count} (Previous: {last_height})")
            
            if current_comment_count == last_height:
                no_change_count += 1
                self.logger.debug(f"No new comments. Attempt {no_change_count}/{max_retries}")
                
                if no_change_count > max_retries:
                    self.logger.info("No new comments found after many attempts. Stopping scroll.")
                    break
            else:
                if current_comment_count > last_height:
                    self.logger.info(f"Loaded {current_comment_count - last_height} new comments.")
                no_change_count = 0
                last_height = current_comment_count
                
            # 5. Max Check
            if max_comments and current_comment_count >= max_comments:
                self.logger.info(f"Reached max comments limit ({max_comments}).")
                break

    def _expand_replies(self):
        """
        Clicks "View replies" buttons to load nested content.
        Uses robust XPath to handle newlines and variations.
        """
        try:
            # XPath: Div role=button containing 'View' and 'replies' in text descendants
            # This handles "View all 8\n replies" correctly.
            xpath = '//div[@role="button"][contains(., "View") and contains(., "replies")]'
            
            buttons = self.page.locator(xpath).all()
            
            # Fallback to Span if no Divs found
            if not buttons:
                 xpath_span = '//span[contains(., "View") and contains(., "replies")]'
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
                time.sleep(3) # Wait longer for network response
        except Exception as e:
            self.logger.error(f"Error expanding replies: {e}")
