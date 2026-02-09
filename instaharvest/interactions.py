"""
Instagram Interaction Manager
Handles Liking, Commenting, and Reels Navigation.

All selectors are centralized in config.py for easy maintenance.
"""
import time
import random
from typing import Optional
from .config import ScraperConfig

class InteractionManager:
    """
    Manages active interactions with Instagram:
    - Liking posts/reels
    - Commenting on posts/reels
    - Reels navigation
    """
    
    def __init__(self, page, logger, config: Optional[ScraperConfig] = None):
        self.page = page
        self.logger = logger
        self.config = config or ScraperConfig()

    def like_post(self, url: Optional[str] = None) -> bool:
        """
        Like the current post (or navigate to url first).
        Returns True if successful (or already liked), False otherwise.
        
        Selectors used (from config.py):
        - selector_like_svg
        - selector_unlike_svg
        - selector_like_strategies
        - selector_unlike_verify
        """
        if url:
            self.page.goto(url)
            time.sleep(random.uniform(2, 4))

        try:
            # Check if already liked using config selectors
            first_like = self.page.locator(self.config.selector_like_svg).first
            first_unlike = self.page.locator(self.config.selector_unlike_svg).first
            
            if first_unlike.count() > 0 and first_like.count() == 0:
                self.logger.info("❤️ Post already liked.")
                return True

            # Try multiple strategies from config
            for selector, name in self.config.selector_like_strategies:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0:
                        self.logger.debug(f"Trying strategy: {name}")
                        elem.click(timeout=2000)
                        time.sleep(0.5)
                        
                        # Verify success using config selector
                        main_unlike = self.page.locator(self.config.selector_unlike_verify).first
                        if main_unlike.count() > 0:
                            self.logger.info(f"❤️ Liked post! (via {name})")
                            return True
                except Exception:
                    continue
            
            # Fallback: JavaScript click
            self.logger.debug("Trying JavaScript click fallback...")
            like_svg_selector = self.config.selector_like_svg
            self.page.evaluate(f'''() => {{
                const svg = document.querySelector('{like_svg_selector}');
                if (svg) {{
                    svg.click();
                    if (svg.parentElement) svg.parentElement.click();
                    if (svg.parentElement?.parentElement) svg.parentElement.parentElement.click();
                }}
            }}''')
            
            time.sleep(0.5)
            if self.page.locator(self.config.selector_unlike_svg).count() > 0:
                self.logger.info("❤️ Liked post! (via JS)")
                return True
            
            # Last resort: force click
            like_svg = self.page.locator(self.config.selector_like_svg).first
            if like_svg.count() > 0:
                like_svg.click(force=True)
                time.sleep(0.5)
                if self.page.locator(self.config.selector_unlike_svg).count() > 0:
                    self.logger.info("❤️ Liked post! (force)")
                    return True
            
            self.logger.warning("Like button found but click didn't register.")
            return False

        except Exception as e:
            self.logger.error(f"Failed to like post: {e}")
            return False

    def comment_post(self, text: str, url: Optional[str] = None) -> bool:
        """
        Comment on the current post.
        
        Selectors used (from config.py):
        - selector_comment_textarea
        - selector_comment_textarea_fallback
        - selector_comment_post_button
        """
        if url:
            self.page.goto(url)
            time.sleep(random.uniform(2, 4))
            
        try:
            # Find comment box using config selector
            comment_box = self.page.locator(self.config.selector_comment_textarea).first
            
            if comment_box.count() == 0:
                # Try fallback selector
                comment_box = self.page.locator(self.config.selector_comment_textarea_fallback).first
            
            if comment_box.count() == 0:
                 self.logger.warning(f"Comment box not found. Selector: {self.config.selector_comment_textarea}")
                 return False

            # Focus and type
            comment_box.click()
            time.sleep(random.uniform(0.5, 1))
            
            # Human-like typing
            self.page.keyboard.type(text, delay=random.randint(50, 150))
            time.sleep(random.uniform(1, 2))

            # Click Post button using config selector
            post_btn = self.page.locator(self.config.selector_comment_post_button).first
            
            if post_btn.count() > 0 and post_btn.is_visible():
                post_btn.click()
                self.logger.info(f"💬 Commented: '{text}'")
                time.sleep(random.uniform(2, 4))
                return True
            else:
                self.logger.warning(f"Post button not found. Selector: {self.config.selector_comment_post_button}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to comment: {e}")
            return False

    def like_reel(self) -> bool:
        """Like the currently viewing Reel"""
        return self.like_post()

    def comment_reel(self, text: str) -> bool:
        """Comment on current Reel"""
        return self.comment_post(text)

    def next_reel(self):
        """Navigate to next reel via keyboard"""
        self.logger.info("⬇️ Scrolling to next reel...")
        self.page.keyboard.press("ArrowDown")
        time.sleep(random.uniform(0.5, 1.0))
        time.sleep(random.uniform(2, 4))
