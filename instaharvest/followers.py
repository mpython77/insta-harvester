"""
Instagram Followers Collector
Professional class for collecting followers list with real-time output
"""

import time
import random
from typing import Optional, List, Set

from .base import BaseScraper
from .config import ScraperConfig


class FollowersCollector(BaseScraper):
    """
    Instagram Followers Collector

    Professional class for collecting followers list:
    - Real-time output as followers are discovered
    - Smart scrolling (stops when no new followers appear)
    - Duplicate detection
    - Configurable limit
    - Works with popup dialog

    Example:
        >>> collector = FollowersCollector()
        >>> collector.setup_browser(session_data)
        >>> followers = collector.get_followers('username', limit=100)
        >>> collector.close()
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize Followers Collector"""
        super().__init__(config)
        self.logger.info("✨ FollowersCollector initialized")

    def get_followers(
        self,
        username: str,
        limit: Optional[int] = None,
        print_realtime: bool = True
    ) -> List[str]:
        """
        Collect followers from a profile with real-time output

        Args:
            username: Instagram username (without @)
            limit: Maximum number of followers to collect (None = all)
            print_realtime: Print followers in real-time as they're discovered

        Returns:
            List of follower usernames

        Example:
            >>> followers = collector.get_followers('instagram', limit=50)
            >>> print(f"Collected {len(followers)} followers")
        """
        self.logger.info(f"📊 Collecting followers from @{username}...")

        try:
            # Navigate to profile
            profile_url = self.config.profile_url_pattern.format(username=username)
            if not self.goto_url(profile_url, delay=self.config.followers_profile_load_delay):
                self.logger.error(f"Failed to load profile: @{username}")
                return []

            # Click followers button to open popup
            if not self._click_followers_button():
                self.logger.error("Failed to open followers popup")
                return []

            # Wait for popup to load
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for popup to load...")
            time.sleep(self.config.popup_open_delay)

            # Collect followers with scrolling
            followers = self._collect_from_popup(
                limit=limit,
                print_realtime=print_realtime
            )

            self.logger.info(f"✅ Collected {len(followers)} followers from @{username}")

            return followers

        except Exception as e:
            self.logger.warning(f"get_followers error: {e}")
            raise

    def get_following(
        self,
        username: str,
        limit: Optional[int] = None,
        print_realtime: bool = True
    ) -> List[str]:
        """
        Collect following list from a profile with real-time output

        Args:
            username: Instagram username (without @)
            limit: Maximum number to collect (None = all)
            print_realtime: Print in real-time as they're discovered

        Returns:
            List of following usernames

        Example:
            >>> following = collector.get_following('instagram', limit=50)
            >>> print(f"Collected {len(following)} following")
        """
        self.logger.info(f"📊 Collecting following from @{username}...")

        try:
            # Navigate to profile
            profile_url = self.config.profile_url_pattern.format(username=username)
            if not self.goto_url(profile_url, delay=self.config.followers_profile_load_delay):
                self.logger.error(f"Failed to load profile: @{username}")
                return []

            # Click following button to open popup
            if not self._click_following_button():
                self.logger.error("Failed to open following popup")
                return []

            # Wait for popup to load
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for popup to load...")
            time.sleep(self.config.popup_open_delay)

            # Collect following with scrolling
            following = self._collect_from_popup(
                limit=limit,
                print_realtime=print_realtime
            )

            self.logger.info(f"✅ Collected {len(following)} following from @{username}")

            return following

        except Exception as e:
            self.logger.error(f"❌ Error collecting following: {e}")
            return []

    def _click_followers_button(self) -> bool:
        """
        Click the followers button to open popup

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            # Add random delay before clicking (allows page to fully load)
            delay_before = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before:.1f}s before clicking Followers button...")
            time.sleep(delay_before)

            # Find followers link - contains "followers" text
            followers_link = self.page.locator(self.config.selector_followers_link).first

            if followers_link.count() == 0:
                self.logger.warning("Followers button not found")
                return False

            # Click button
            followers_link.click(timeout=self.config.followers_link_timeout)

            # Wait for popup to open
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for popup to open...")
            time.sleep(self.config.popup_open_delay)

            self.logger.debug("✓ Followers popup opened")
            return True

        except Exception as e:
            self.logger.warning(f"Error clicking followers button: {e}")
            return False

    def _click_following_button(self) -> bool:
        """
        Click the following button to open popup

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            # Add random delay before clicking (allows page to fully load)
            delay_before = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before:.1f}s before clicking Following button...")
            time.sleep(delay_before)

            # Find following link - contains "following" text
            following_link = self.page.locator(self.config.selector_following_link).first

            if following_link.count() == 0:
                self.logger.warning("Following button not found")
                return False

            # Click button
            following_link.click(timeout=self.config.followers_link_timeout)

            # Wait for popup to open
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for popup to open...")
            time.sleep(self.config.popup_open_delay)

            self.logger.debug("✓ Following popup opened")
            return True

        except Exception as e:
            self.logger.warning(f"Error clicking following button: {e}")
            return False

    def _collect_from_popup(
        self,
        limit: Optional[int] = None,
        print_realtime: bool = True
    ) -> List[str]:
        """
        Collect usernames from popup with smart scrolling

        Args:
            limit: Maximum number to collect (None = all)
            print_realtime: Print usernames in real-time

        Returns:
            List of usernames
        """
        followers: List[str] = []
        seen_usernames: Set[str] = set()

        no_new_followers_count = 0
        max_no_new_attempts = self.config.followers_max_no_new_scrolls

        scroll_count = 0

        if print_realtime:
            print("\n" + "="*70)
            print("📋 COLLECTING FOLLOWERS (Real-time)")
            print("="*70)

        while True:
            # Check if limit reached
            if limit and len(followers) >= limit:
                self.logger.debug(f"✓ Limit reached: {limit}")
                break

            # Extract current followers from popup
            current_batch = self._extract_current_followers()

            # Count new followers
            new_count = 0
            for username in current_batch:
                if username not in seen_usernames:
                    seen_usernames.add(username)
                    followers.append(username)
                    new_count += 1

                    # Print in real-time
                    if print_realtime:
                        print(f"  {len(followers)}. @{username}")

                    # Check limit after each addition
                    if limit and len(followers) >= limit:
                        break

            # Check if we found new followers
            if new_count == 0:
                no_new_followers_count += 1
                self.logger.debug(
                    f"No new followers found (attempt {no_new_followers_count}/{max_no_new_attempts})"
                )

                # Stop if no new followers for max_no_new_attempts consecutive scrolls
                if max_no_new_attempts > 0 and no_new_followers_count >= max_no_new_attempts:
                    self.logger.debug("✓ No new followers detected, stopping")
                    break
            else:
                # Reset counter when new followers found
                no_new_followers_count = 0
                self.logger.debug(f"✓ Found {new_count} new followers")

            # Check limit again
            if limit and len(followers) >= limit:
                break

            # Scroll popup to load more
            scroll_count += 1
            self._scroll_popup()

            # Random delay between scrolls (allows content to load)
            scroll_delay = random.uniform(self.config.scroll_delay_min, self.config.scroll_delay_max)
            self.logger.debug(f"⏱️ Waiting {scroll_delay:.1f}s after scroll...")
            time.sleep(scroll_delay)

        if print_realtime:
            print("="*70)
            print(f"✅ Total collected: {len(followers)} followers")
            print("="*70)

        return followers

    def _extract_current_followers(self) -> List[str]:
        """
        Extract currently visible followers using robust selectors.
        
        Strategy:
        1. Primary: Find avatar links (44px style) - most reliable
        2. Fallback: Find username spans with specific classes
        3. Filter system paths and validate username format
        """
        usernames = []

        try:
            # Execute JS to get usernames using multiple strategies
            raw_usernames = self.page.evaluate(r'''() => {
                const usernames = [];
                const seen = new Set();
                
                // Strategy 1: Avatar links (44px profile pictures)
                // These are the most reliable - each user entry has a 44px avatar
                const avatarLinks = document.querySelectorAll('a[href^="/"]');
                for (const link of avatarLinks) {
                    // Check if this looks like a profile avatar link
                    const style = link.getAttribute('style') || '';
                    const hasSize = style.includes('44px') || style.includes('54px') || style.includes('56px');
                    
                    // Also check parent/child for size indicators
                    const img = link.querySelector('img');
                    const isAvatar = img && (
                        img.alt?.includes('profile picture') ||
                        hasSize ||
                        link.getAttribute('role') === 'link'
                    );
                    
                    if (isAvatar || hasSize) {
                        const href = link.getAttribute('href');
                        if (href && href.match(/^\/[a-zA-Z0-9._]+\/$/)) {
                            const username = href.replace(/\//g, '');
                            if (username && !seen.has(username)) {
                                seen.add(username);
                                usernames.push(username);
                            }
                        }
                    }
                }
                
                // Strategy 2: Username spans with specific Instagram classes
                // Fallback if avatar detection fails
                if (usernames.length === 0) {
                    const spans = document.querySelectorAll('span._ap3a._aaco._aacw._aacx._aad7._aade');
                    for (const span of spans) {
                        const text = span.textContent?.trim();
                        if (text && text.match(/^[a-zA-Z0-9._]+$/) && !seen.has(text)) {
                            seen.add(text);
                            usernames.push(text);
                        }
                    }
                }
                
                // Strategy 3: Any link that looks like /username/
                // Last resort fallback
                if (usernames.length === 0) {
                    const allLinks = document.querySelectorAll('a[href]');
                    for (const link of allLinks) {
                        const href = link.getAttribute('href');
                        if (!href) continue;
                        
                        try {
                            const url = new URL(href, document.baseURI);
                            const parts = url.pathname.split('/').filter(p => p.length > 0);
                            
                            if (parts.length === 1 && parts[0].match(/^[a-zA-Z0-9._]+$/)) {
                                const username = parts[0];
                                if (!seen.has(username)) {
                                    seen.add(username);
                                    usernames.push(username);
                                }
                            }
                        } catch (e) {
                            continue;
                        }
                    }
                }
                
                return usernames;
            }''')

            # Filter in Python - remove system paths
            for username in raw_usernames:
                if username in self.config.instagram_system_paths:
                    continue
                
                if username not in usernames:
                    usernames.append(username)

        except Exception as e:
            self.logger.debug(f"Error extracting followers: {e}")

        return usernames

    def _scroll_popup(self) -> None:
        """
        Scroll the followers/following popup to load more users.
        Uses Context-Aware Scroll (Header Detection) to target the specific popup 
        and avoid scrolling the background page.
        """
        try:
            # Execute JS to find and scroll the best candidate
            # Strategy: Find "Followers" or "Following" header, then find adjacent scrollable area
            scrolled = self.page.evaluate('''() => {
                // Helper to check if element is scrollable
                function isScrollable(el) {
                    const style = window.getComputedStyle(el);
                    // Explicitly check for scroll/auto overflow properties
                    const isScrollableStyle = style.overflowY === 'auto' || style.overflowY === 'scroll' || style.overflow === 'auto' || style.overflow === 'hidden auto';
                    const canScroll = el.scrollHeight > el.clientHeight;
                    return (isScrollableStyle || canScroll) && el.clientHeight > 0;
                }

                // 1. Detect Modal Header
                // Prioritize explicit headings to avoid matching buttons or other text
                const headings = Array.from(document.querySelectorAll('div[role="heading"], h1'));
                let targetHeading = headings.find(h => {
                    const text = h.textContent.trim();
                    return text.includes('Followers') || text.includes('Following') || text.includes('Likes');
                });
                
                // Fallback to spans if no formal heading found (unlikely but possible)
                if (!targetHeading) {
                     const spans = Array.from(document.querySelectorAll('span'));
                     targetHeading = spans.find(s => {
                        const text = s.textContent.trim();
                        // Strict check for spans to avoid matching "Following" buttons
                        return text === 'Followers' || text === 'Following' || text === 'Likes';
                     });
                }

                if (targetHeading) {
                    // Traverse up to find the container holding both header and list
                    let parent = targetHeading.parentElement;
                    let attempts = 0;
                    while (parent && attempts < 10) {
                        
                        // Look for a distinct scrollable container inside this parent
                        // We filter for divs that look like the list container
                        const candidates = Array.from(parent.querySelectorAll('div')).filter(div => {
                           const style = window.getComputedStyle(div);
                           // Must be strictly scrollable style
                           const hasOverflow = style.overflowY === 'auto' || style.overflowY === 'scroll' || style.overflow === 'hidden auto';
                           return hasOverflow && div.scrollHeight > div.clientHeight;
                        });

                        // If we found candidates, usually the one with the most content (largest scrollHeight) is the list
                        if (candidates.length > 0) {
                             candidates.sort((a, b) => b.scrollHeight - a.scrollHeight);
                             const target = candidates[0];
                             target.scrollTop = target.scrollHeight;
                             target.dispatchEvent(new Event('scroll'));
                             return true;
                        }
                        
                        parent = parent.parentElement;
                        attempts++;
                    }
                }

                // 2. Fallback: Find ANY superimposed scrollable modal
                // If header detection failed, look for scrollable divs with high Z-Index or specific modal-like properties
                const divs = document.querySelectorAll('div[style*="overflow"]');
                let bestCandidate = null;
                let maxZ = -1;

                for (const div of divs) {
                     if (isScrollable(div)) {
                         // Simple heuristic: Modals usually have specific styles or existing high z-index
                         // Here we just pick the one that is NOT the body/main html (usually clientHeight < window.innerHeight)
                         if (div.clientHeight < window.innerHeight - 50 && div.clientWidth > 200) {
                             bestCandidate = div;
                             break; // Found a likely modal
                         }
                     }
                }

                if (bestCandidate) {
                    bestCandidate.scrollTop = bestCandidate.scrollHeight;
                    bestCandidate.dispatchEvent(new Event('scroll'));
                    return true;
                }

                return false;
            }''')

            if scrolled:
                self.logger.debug("📜 Scrolled popup (targeted)")
            else:
                self.logger.debug("📜 Could not target popup scroll, attempting mouse wheel")
                # Last resort: hover center and scroll
                # This works if the mouse is over the modal
                vp = self.page.viewport_size
                if vp:
                    self.page.mouse.move(vp['width'] / 2, vp['height'] / 2)
                    self.page.mouse.wheel(0, 500)

        except Exception as e:
            self.logger.debug(f"Error scrolling popup: {e}")

    def scrape(self, *args, **kwargs):
        """Required by BaseScraper - not used in FollowersCollector"""
        raise NotImplementedError("FollowersCollector does not implement scrape()")
