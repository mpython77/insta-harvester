"""
Instagram Interaction Manager
Handles Liking, Commenting, and Reels Navigation.

All selectors are centralized in config.py for easy maintenance.
"""
import time
import random
from typing import Optional, List, Dict
from .config import ScraperConfig

class InteractionManager:
    """
    Manages active interactions with Instagram:
    - Liking posts/reels
    - Commenting on posts/reels
    - Liking comments
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
        
        Uses height="24" filtered selectors to avoid clicking comment like buttons.
        """
        if url:
            self.page.goto(url)
            time.sleep(random.uniform(2, 4))

        try:
            # Check if already liked using config selectors (height=24 = post only)
            first_like = self.page.locator(self.config.selector_like_svg).first
            first_unlike = self.page.locator(self.config.selector_unlike_svg).first
            
            if first_unlike.count() > 0 and first_like.count() == 0:
                self.logger.info("❤️ Post already liked.")
                return True

            # Try multiple strategies from config (all use height="24")
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
            
            # Fallback: JavaScript click (with height filter)
            self.logger.debug("Trying JavaScript click fallback...")
            self.page.evaluate('''() => {
                const svg = document.querySelector('svg[aria-label="Like"][height="24"]');
                if (svg) {
                    svg.click();
                    if (svg.parentElement) svg.parentElement.click();
                    if (svg.parentElement?.parentElement) svg.parentElement.parentElement.click();
                }
            }''')
            
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

    def like_comment(self, username: Optional[str] = None, index: int = 0, url: Optional[str] = None) -> bool:
        """
        Like a specific comment on the current post.
        
        Args:
            username: Like the comment by this username. If None, uses index.
            index: Like the Nth comment (0-based). Only used if username is None.
            url: Navigate to this post URL first (optional).
            
        Returns:
            True if comment was liked successfully, False otherwise.
            
        Example:
            >>> manager.like_comment(username="johndoe")  # Like johndoe's comment
            >>> manager.like_comment(index=0)              # Like the first comment
            >>> manager.like_comment(index=2)              # Like the third comment
        """
        if url:
            self.page.goto(url)
            time.sleep(random.uniform(2, 4))

        try:
            # Find all comment items on the page
            comment_items = self.page.locator(self.config.selector_comment_item_wrapper)
            total = comment_items.count()
            
            if total == 0:
                self.logger.warning("⚠️ No comments found on this post.")
                return False
            
            self.logger.debug(f"Found {total} comments on page")
            
            target_item = None
            target_username = None
            
            if username:
                # Find comment by username
                for i in range(total):
                    item = comment_items.nth(i)
                    author_link = item.locator(self.config.selector_comment_author_link).first
                    if author_link.count() > 0:
                        author_text = author_link.inner_text(timeout=2000).strip()
                        if author_text.lower() == username.lower():
                            target_item = item
                            target_username = author_text
                            break
                
                if target_item is None:
                    self.logger.warning(f"⚠️ Comment by @{username} not found.")
                    return False
            else:
                # Use index (skip first item which is the post caption)
                # Caption is usually at index 0, first real comment at index 1
                actual_index = index + 1 if total > 1 else index
                if actual_index >= total:
                    self.logger.warning(f"⚠️ Comment index {index} out of range (max: {total - 2}).")
                    return False
                target_item = comment_items.nth(actual_index)
                author_link = target_item.locator(self.config.selector_comment_author_link).first
                if author_link.count() > 0:
                    target_username = author_link.inner_text(timeout=2000).strip()
                else:
                    target_username = f"comment#{index}"
            
            # Find the like button within this comment (height=12)
            like_btn = target_item.locator(self.config.selector_comment_like_svg).first
            unlike_btn = target_item.locator(self.config.selector_comment_unlike_svg).first
            
            # Check if already liked
            if unlike_btn.count() > 0:
                self.logger.info(f"❤️ Comment by @{target_username} already liked.")
                return True
            
            if like_btn.count() == 0:
                self.logger.warning(f"⚠️ Like button not found for comment by @{target_username}.")
                return False
            
            # Click the comment like button
            like_btn.click(timeout=2000)
            time.sleep(random.uniform(0.3, 0.8))
            
            # Verify
            unlike_verify = target_item.locator(self.config.selector_comment_unlike_svg).first
            if unlike_verify.count() > 0:
                self.logger.info(f"💜 Liked comment by @{target_username}!")
                return True
            else:
                # Force click fallback
                like_btn_retry = target_item.locator(self.config.selector_comment_like_svg).first
                if like_btn_retry.count() > 0:
                    like_btn_retry.click(force=True, timeout=2000)
                    time.sleep(0.5)
                    if target_item.locator(self.config.selector_comment_unlike_svg).count() > 0:
                        self.logger.info(f"💜 Liked comment by @{target_username}! (force)")
                        return True
                
                self.logger.warning(f"⚠️ Failed to verify like on comment by @{target_username}.")
                return False

        except Exception as e:
            self.logger.error(f"Failed to like comment: {e}")
            return False

    def like_all_comments(self, max_comments: int = 10, url: Optional[str] = None, 
                          delay_min: float = 0.5, delay_max: float = 1.5) -> Dict[str, int]:
        """
        Like multiple comments on the current post.
        
        Args:
            max_comments: Maximum number of comments to like.
            url: Navigate to this post URL first (optional).
            delay_min: Minimum delay between likes (seconds).
            delay_max: Maximum delay between likes (seconds).
            
        Returns:
            Dict with keys: 'liked', 'already_liked', 'failed', 'total'
            
        Example:
            >>> result = manager.like_all_comments(max_comments=5)
            >>> print(f"Liked: {result['liked']}/{result['total']}")
        """
        if url:
            self.page.goto(url)
            time.sleep(random.uniform(2, 4))

        results = {'liked': 0, 'already_liked': 0, 'failed': 0, 'total': 0}

        try:
            comment_items = self.page.locator(self.config.selector_comment_item_wrapper)
            total = comment_items.count()
            
            if total == 0:
                self.logger.warning("⚠️ No comments found on this post.")
                return results
            
            # Skip first item (usually the caption)
            start_index = 1 if total > 1 else 0
            end_index = min(start_index + max_comments, total)
            results['total'] = end_index - start_index
            
            self.logger.info(f"💜 Liking {results['total']} comments...")
            
            for i in range(start_index, end_index):
                try:
                    item = comment_items.nth(i)
                    
                    # Get username
                    author_link = item.locator(self.config.selector_comment_author_link).first
                    username = "unknown"
                    if author_link.count() > 0:
                        username = author_link.inner_text(timeout=2000).strip()
                    
                    # Check if already liked
                    unlike_btn = item.locator(self.config.selector_comment_unlike_svg).first
                    if unlike_btn.count() > 0:
                        self.logger.debug(f"  Already liked: @{username}")
                        results['already_liked'] += 1
                        continue
                    
                    # Find and click like button
                    like_btn = item.locator(self.config.selector_comment_like_svg).first
                    if like_btn.count() > 0:
                        like_btn.click(timeout=2000)
                        time.sleep(random.uniform(0.3, 0.6))
                        
                        # Verify
                        if item.locator(self.config.selector_comment_unlike_svg).count() > 0:
                            self.logger.debug(f"  💜 Liked: @{username}")
                            results['liked'] += 1
                        else:
                            self.logger.debug(f"  ⚠️ Unverified: @{username}")
                            results['failed'] += 1
                    else:
                        results['failed'] += 1
                    
                    # Human-like delay between likes
                    time.sleep(random.uniform(delay_min, delay_max))
                    
                except Exception as e:
                    self.logger.debug(f"  Error liking comment {i}: {e}")
                    results['failed'] += 1
                    continue
            
            self.logger.info(
                f"💜 Comments liked: {results['liked']} | "
                f"Already: {results['already_liked']} | "
                f"Failed: {results['failed']} | "
                f"Total: {results['total']}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to like comments: {e}")
        
        return results

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

