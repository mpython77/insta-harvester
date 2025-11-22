"""
Instagram Follow Manager
Professional class for following and unfollowing Instagram accounts
"""

import time
import random
from typing import Optional, Literal

from .base import BaseScraper
from .config import ScraperConfig


class FollowManager(BaseScraper):
    """
    Instagram Follow/Unfollow Manager

    Professional class for managing Instagram follow operations:
    - Follow users
    - Unfollow users
    - Check following status
    - Batch operations
    - Smart delays and rate limiting

    Example:
        >>> manager = FollowManager()
        >>> manager.setup_browser(session_data)
        >>> result = manager.follow("username")
        >>> manager.close()
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize Follow Manager"""
        super().__init__(config)
        self.logger.info("✨ FollowManager initialized")

    def follow(
        self,
        username: str,
        check_status: bool = True,
        add_delay: bool = True
    ) -> dict:
        """
        Follow an Instagram user

        Args:
            username: Instagram username (without @)
            check_status: Check if already following before attempting
            add_delay: Add random delay after action (rate limiting)

        Returns:
            dict with keys:
                - success (bool): Whether operation succeeded
                - status (str): 'followed', 'already_following', 'error'
                - message (str): Human-readable message
                - username (str): Target username

        Example:
            >>> result = manager.follow("instagram")
            >>> if result['success']:
            ...     print(f"✅ {result['message']}")
        """
        self.logger.info(f"📌 Follow request: @{username}")

        try:
            # Navigate to profile
            profile_url = f"https://www.instagram.com/{username}/"
            if not self.goto_url(profile_url, delay=2):
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Failed to load profile: @{username}',
                    'username': username
                }

            # Check if already following (optional)
            if check_status:
                current_status = self._get_follow_status()
                if current_status == 'following':
                    self.logger.info(f"ℹ️ Already following @{username}")
                    return {
                        'success': True,
                        'status': 'already_following',
                        'message': f'Already following @{username}',
                        'username': username
                    }

            # Find and click Follow button
            follow_clicked = self._click_follow_button()

            if follow_clicked:
                self.logger.info(f"✅ Successfully followed @{username}")

                # Add delay for rate limiting
                if add_delay:
                    delay = random.uniform(self.config.follow_delay_min, self.config.follow_delay_max)
                    self.logger.debug(f"⏱️ Rate limit delay: {delay:.1f}s")
                    time.sleep(delay)

                return {
                    'success': True,
                    'status': 'followed',
                    'message': f'Successfully followed @{username}',
                    'username': username
                }
            else:
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Could not find Follow button for @{username}',
                    'username': username
                }

        except Exception as e:
            self.logger.error(f"❌ Error following @{username}: {e}")
            return {
                'success': False,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'username': username
            }

    def unfollow(
        self,
        username: str,
        confirm: bool = True,
        add_delay: bool = True
    ) -> dict:
        """
        Unfollow an Instagram user

        Args:
            username: Instagram username (without @)
            confirm: Confirm unfollow in popup dialog
            add_delay: Add random delay after action (rate limiting)

        Returns:
            dict with keys:
                - success (bool): Whether operation succeeded
                - status (str): 'unfollowed', 'not_following', 'error'
                - message (str): Human-readable message
                - username (str): Target username

        Example:
            >>> result = manager.unfollow("instagram")
            >>> if result['success']:
            ...     print(f"✅ {result['message']}")
        """
        self.logger.info(f"📌 Unfollow request: @{username}")

        try:
            # Navigate to profile
            profile_url = f"https://www.instagram.com/{username}/"
            if not self.goto_url(profile_url, delay=2):
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Failed to load profile: @{username}',
                    'username': username
                }

            # Check if currently following
            current_status = self._get_follow_status()
            if current_status != 'following':
                self.logger.info(f"ℹ️ Not following @{username}")
                return {
                    'success': True,
                    'status': 'not_following',
                    'message': f'Not following @{username}',
                    'username': username
                }

            # Click Following button to open menu
            unfollow_clicked = self._click_unfollow_button(confirm=confirm)

            if unfollow_clicked:
                self.logger.info(f"✅ Successfully unfollowed @{username}")

                # Add delay for rate limiting
                if add_delay:
                    delay = random.uniform(self.config.follow_delay_min, self.config.follow_delay_max)
                    self.logger.debug(f"⏱️ Rate limit delay: {delay:.1f}s")
                    time.sleep(delay)

                return {
                    'success': True,
                    'status': 'unfollowed',
                    'message': f'Successfully unfollowed @{username}',
                    'username': username
                }
            else:
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Could not unfollow @{username}',
                    'username': username
                }

        except Exception as e:
            self.logger.error(f"❌ Error unfollowing @{username}: {e}")
            return {
                'success': False,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'username': username
            }

    def is_following(self, username: str) -> dict:
        """
        Check if you are following a user

        Args:
            username: Instagram username (without @)

        Returns:
            dict with keys:
                - success (bool): Whether check succeeded
                - following (bool): True if following, False if not
                - status (str): 'following', 'not_following', 'error'
                - message (str): Human-readable message
                - username (str): Target username

        Example:
            >>> result = manager.is_following("instagram")
            >>> if result['following']:
            ...     print(f"✅ You are following @{result['username']}")
        """
        self.logger.info(f"🔍 Checking follow status: @{username}")

        try:
            # Navigate to profile
            profile_url = f"https://www.instagram.com/{username}/"
            if not self.goto_url(profile_url, delay=2):
                return {
                    'success': False,
                    'following': False,
                    'status': 'error',
                    'message': f'Failed to load profile: @{username}',
                    'username': username
                }

            # Get follow status
            status = self._get_follow_status()

            if status == 'following':
                return {
                    'success': True,
                    'following': True,
                    'status': 'following',
                    'message': f'You are following @{username}',
                    'username': username
                }
            elif status == 'not_following':
                return {
                    'success': True,
                    'following': False,
                    'status': 'not_following',
                    'message': f'You are not following @{username}',
                    'username': username
                }
            else:
                return {
                    'success': False,
                    'following': False,
                    'status': 'error',
                    'message': f'Could not determine status for @{username}',
                    'username': username
                }

        except Exception as e:
            self.logger.error(f"❌ Error checking status for @{username}: {e}")
            return {
                'success': False,
                'following': False,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'username': username
            }

    def batch_follow(
        self,
        usernames: list,
        delay_between: tuple = (2, 4),
        stop_on_error: bool = False
    ) -> dict:
        """
        Follow multiple users with delays

        Args:
            usernames: List of usernames to follow
            delay_between: Random delay range between follows (min, max) in seconds
            stop_on_error: Stop if any follow fails

        Returns:
            dict with keys:
                - total (int): Total users to follow
                - succeeded (int): Successfully followed
                - already_following (int): Already following
                - failed (int): Failed attempts
                - results (list): Individual results for each user

        Example:
            >>> result = manager.batch_follow(['user1', 'user2', 'user3'])
            >>> print(f"Followed {result['succeeded']}/{result['total']} users")
        """
        self.logger.info(f"📦 Batch follow: {len(usernames)} users")

        results = []
        succeeded = 0
        already_following = 0
        failed = 0

        for i, username in enumerate(usernames, 1):
            self.logger.info(f"[{i}/{len(usernames)}] Processing @{username}")

            result = self.follow(username, add_delay=False)
            results.append(result)

            if result['status'] == 'followed':
                succeeded += 1
            elif result['status'] == 'already_following':
                already_following += 1
            else:
                failed += 1
                if stop_on_error:
                    self.logger.warning(f"⚠️ Stopping due to error on @{username}")
                    break

            # Add delay between follows (except for last one)
            if i < len(usernames):
                delay = random.uniform(self.config.batch_operation_delay_min, self.config.batch_operation_delay_max)
                self.logger.debug(f"⏱️ Waiting {delay:.1f}s before next follow...")
                time.sleep(delay)

        summary = {
            'total': len(usernames),
            'succeeded': succeeded,
            'already_following': already_following,
            'failed': failed,
            'results': results
        }

        self.logger.info(
            f"✅ Batch follow complete: "
            f"{succeeded} followed, {already_following} already following, {failed} failed"
        )

        return summary

    def _get_follow_status(self) -> Literal['following', 'not_following', 'unknown']:
        """
        Get current follow status by checking button text

        Returns:
            'following' - Already following this user
            'not_following' - Not following this user
            'unknown' - Could not determine status
        """
        try:
            # Method 1: Look for "Following" button with down chevron
            # This indicates user is already following
            following_button = self.page.locator('button:has-text("Following")').first
            if following_button.count() > 0:
                self.logger.debug("✓ Status: Following (found 'Following' button)")
                return 'following'

            # Method 2: Look for "Follow" button
            # This indicates user is not following yet
            follow_button = self.page.locator('button:has-text("Follow")').first
            if follow_button.count() > 0:
                # Make sure it's not "Follow Back"
                button_text = follow_button.inner_text(timeout=2000)
                if button_text.strip() == "Follow":
                    self.logger.debug("✓ Status: Not following (found 'Follow' button)")
                    return 'not_following'

            # Method 3: Look for "Follow Back" button
            follow_back_button = self.page.locator('button:has-text("Follow Back")').first
            if follow_back_button.count() > 0:
                self.logger.debug("✓ Status: Not following (found 'Follow Back' button)")
                return 'not_following'

            self.logger.warning("⚠️ Could not determine follow status")
            return 'unknown'

        except Exception as e:
            self.logger.warning(f"Error checking follow status: {e}")
            return 'unknown'

    def _click_follow_button(self) -> bool:
        """
        Click the Follow button

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            # Find Follow button
            follow_button = self.page.locator('button:has-text("Follow")').first

            if follow_button.count() == 0:
                self.logger.warning("Follow button not found")
                return False

            # Make sure it's the main Follow button (not "Follow Back")
            button_text = follow_button.inner_text(timeout=2000)
            if button_text.strip() not in ["Follow", "Follow Back"]:
                self.logger.warning(f"Unexpected button text: {button_text}")
                return False

            # Add random delay before clicking (allows page to fully load)
            delay_before = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before:.1f}s before clicking Follow button...")
            time.sleep(delay_before)

            # Click button
            follow_button.click(timeout=3000)

            # Wait for action to complete
            self.logger.debug(f"⏱️ Waiting {self.config.button_click_delay}s for action to complete...")
            time.sleep(self.config.button_click_delay)

            self.logger.debug("✓ Follow button clicked")
            return True

        except Exception as e:
            self.logger.warning(f"Error clicking Follow button: {e}")
            return False

    def _click_unfollow_button(self, confirm: bool = True) -> bool:
        """
        Click the Following button and confirm unfollow

        Args:
            confirm: Confirm unfollow in dialog

        Returns:
            True if unfollowed successfully, False otherwise
        """
        try:
            # Add random delay before clicking (allows page to fully load)
            delay_before = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before:.1f}s before clicking Following button...")
            time.sleep(delay_before)

            # Step 1: Click "Following" button
            following_button = self.page.locator('button:has-text("Following")').first

            if following_button.count() == 0:
                self.logger.warning("Following button not found")
                return False

            following_button.click(timeout=3000)

            # Wait for popup dialog to appear
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for popup dialog to appear...")
            time.sleep(self.config.popup_open_delay)

            self.logger.debug("✓ Following button clicked, dialog opened")

            # Step 2: Confirm unfollow in dialog (if requested)
            if confirm:
                # Add another delay before clicking confirmation button
                delay_confirm = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
                self.logger.debug(f"⏱️ Waiting {delay_confirm:.1f}s before clicking Unfollow confirmation...")
                time.sleep(delay_confirm)

                # Try to find unfollow button with multiple selectors (different languages/HTML structures)
                # Instagram uses both <button> and <div role="button"> elements!
                unfollow_confirm_button = None

                selectors_to_try = [
                    # Method 1: Playwright text selector (most reliable, works with any element!)
                    'text="Unfollow"',

                    # Method 2: Try div elements with role="button" (Instagram's NEW structure!)
                    'div[role="dialog"] div[role="button"]:has-text("Unfollow")',
                    'div[role="dialog"] [role="button"]:has-text("Unfollow")',
                    'div[role="button"]:has-text("Unfollow")',

                    # Method 3: Any element with "Unfollow" text
                    '*:has-text("Unfollow")',

                    # Method 4: Traditional button elements
                    'button:has-text("Unfollow")',
                    'div[role="dialog"] button',

                    # Method 5: By position - first clickable element in dialog
                    'div[role="dialog"] [role="button"]:first-child',
                    'div[role="dialog"] div[role="button"]',

                    # Method 6: Instagram's CSS class for buttons
                    'div[role="dialog"] .x1i10hfl[role="button"]',
                    'div.x1i10hfl[role="button"]',

                    # Method 7: Any element with role=button in dialog
                    'div[role="dialog"] [role="button"]',
                ]

                for selector in selectors_to_try:
                    try:
                        button = self.page.locator(selector).first
                        if button.count() > 0:
                            # Found a button, check if it's visible
                            try:
                                if button.is_visible(timeout=1000):
                                    unfollow_confirm_button = button
                                    self.logger.debug(f"✓ Found unfollow button using selector: {selector}")
                                    break
                            except Exception:
                                # is_visible failed, try next selector
                                continue
                    except Exception as e:
                        self.logger.debug(f"Selector '{selector}' failed: {e}")
                        continue

                if unfollow_confirm_button is None or unfollow_confirm_button.count() == 0:
                    # Last resort: Get all buttons/divs in dialog and click the first one
                    try:
                        # Try div[role="button"] first
                        dialog_buttons = self.page.locator('div[role="dialog"] [role="button"]')
                        if dialog_buttons.count() == 0:
                            # Fallback to regular buttons
                            dialog_buttons = self.page.locator('div[role="dialog"] button')

                        if dialog_buttons.count() > 0:
                            unfollow_confirm_button = dialog_buttons.first
                            self.logger.debug(f"✓ Using first clickable element in dialog (found {dialog_buttons.count()} elements)")
                        else:
                            self.logger.warning("Unfollow confirmation button not found - no clickable elements in dialog")
                            return False
                    except Exception as e:
                        self.logger.warning(f"Unfollow confirmation button not found: {e}")
                        return False

                # Click the button
                try:
                    unfollow_confirm_button.click(timeout=3000)
                    self.logger.debug("✓ Unfollow button clicked")
                except Exception as e:
                    self.logger.warning(f"Failed to click unfollow button: {e}")
                    return False

                # Wait for action to complete
                self.logger.debug(f"⏱️ Waiting {self.config.button_click_delay}s for unfollow action to complete...")
                time.sleep(self.config.button_click_delay)

                self.logger.debug("✓ Unfollow confirmed")

            return True

        except Exception as e:
            self.logger.warning(f"Error clicking Unfollow button: {e}")
            return False

    def scrape(self, *args, **kwargs):
        """Required by BaseScraper - not used in FollowManager"""
        raise NotImplementedError("FollowManager does not implement scrape()")
