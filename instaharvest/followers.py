"""
Instagram Followers Collector
Professional class for collecting followers list with real-time output
"""

import time
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
            profile_url = f"https://www.instagram.com/{username}/"
            if not self.goto_url(profile_url, delay=2):
                self.logger.error(f"Failed to load profile: @{username}")
                return []

            # Click followers button to open popup
            if not self._click_followers_button():
                self.logger.error("Failed to open followers popup")
                return []

            # Wait for popup to load
            time.sleep(2)

            # Collect followers with scrolling
            followers = self._collect_from_popup(
                limit=limit,
                print_realtime=print_realtime
            )

            self.logger.info(f"✅ Collected {len(followers)} followers from @{username}")

            return followers

        except Exception as e:
            self.logger.error(f"❌ Error collecting followers: {e}")
            return []

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
            profile_url = f"https://www.instagram.com/{username}/"
            if not self.goto_url(profile_url, delay=2):
                self.logger.error(f"Failed to load profile: @{username}")
                return []

            # Click following button to open popup
            if not self._click_following_button():
                self.logger.error("Failed to open following popup")
                return []

            # Wait for popup to load
            time.sleep(2)

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
            # Find followers link - contains "followers" text
            followers_link = self.page.locator('a[href*="/followers/"]').first

            if followers_link.count() == 0:
                self.logger.warning("Followers button not found")
                return False

            # Click button
            followers_link.click(timeout=3000)
            time.sleep(1.5)  # Wait for popup to open

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
            # Find following link - contains "following" text
            following_link = self.page.locator('a[href*="/following/"]').first

            if following_link.count() == 0:
                self.logger.warning("Following button not found")
                return False

            # Click button
            following_link.click(timeout=3000)
            time.sleep(1.5)  # Wait for popup to open

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
        max_no_new_attempts = 3  # Stop after 3 scrolls with no new followers

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

                # Stop if no new followers for 3 consecutive scrolls
                if no_new_followers_count >= max_no_new_attempts:
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

            # Small delay between scrolls
            time.sleep(1.0)

        if print_realtime:
            print("="*70)
            print(f"✅ Total collected: {len(followers)} followers")
            print("="*70)

        return followers

    def _extract_current_followers(self) -> List[str]:
        """
        Extract currently visible followers from popup

        Instagram structure:
        - Each user: div with class containing "x1qnrgzn x1cek8b2 xb10e19..."
        - Inside: span with class="xjp7ctv"
        - Inside: a with href="/username/"

        Returns:
            List of usernames currently visible
        """
        usernames = []

        try:
            # Find all user containers
            # Using the specific class combination for user rows
            user_containers = self.page.locator('div.x1qnrgzn.x1cek8b2.xb10e19.x19rwo8q.x1lliihq.x193iq5w.xh8yej3').all()

            for container in user_containers:
                try:
                    # Find span.xjp7ctv inside this container
                    span = container.locator('span.xjp7ctv').first

                    if span.count() == 0:
                        continue

                    # Find link inside span
                    link = span.locator('a[href]').first

                    if link.count() == 0:
                        continue

                    # Get href attribute
                    href = link.get_attribute('href', timeout=1000)

                    if not href:
                        continue

                    # Extract username from href="/username/"
                    username = href.strip('/').split('/')[-1]

                    # Filter out system paths
                    if username in ['explore', 'direct', 'accounts', 'p', 'reel', 'tv', 'stories', 'followers', 'following']:
                        continue

                    if username and username not in usernames:
                        usernames.append(username)

                except Exception as e:
                    # Skip this container if error
                    continue

        except Exception as e:
            self.logger.debug(f"Error extracting followers: {e}")

        return usernames

    def _scroll_popup(self) -> None:
        """
        Scroll the followers/following popup to load more users

        The popup has a scrollable container
        """
        try:
            # Method 1: Find scrollable dialog and scroll it
            # The dialog usually has overflow: auto
            dialog = self.page.locator('div[role="dialog"]').first

            if dialog.count() > 0:
                # Scroll inside dialog
                dialog.evaluate('(element) => element.scrollTop = element.scrollHeight')
            else:
                # Method 2: Scroll the popup container
                # Find div with overflow: auto
                scrollable = self.page.locator('div[style*="overflow"]').first
                if scrollable.count() > 0:
                    scrollable.evaluate('(element) => element.scrollTop = element.scrollHeight')

            self.logger.debug("✓ Scrolled popup")

        except Exception as e:
            self.logger.debug(f"Error scrolling popup: {e}")

    def scrape(self, *args, **kwargs):
        """Required by BaseScraper - not used in FollowersCollector"""
        raise NotImplementedError("FollowersCollector does not implement scrape()")
