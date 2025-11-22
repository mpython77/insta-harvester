"""
Instagram Direct Message Manager
Professional class for sending Instagram DMs
"""

import time
import random
from typing import Optional

from .base import BaseScraper
from .config import ScraperConfig


class MessageManager(BaseScraper):
    """
    Instagram Direct Message Manager

    Professional class for sending Instagram direct messages:
    - Send DM to users
    - Batch send messages
    - Smart delays and rate limiting
    - Error handling

    Example:
        >>> manager = MessageManager()
        >>> manager.setup_browser(session_data)
        >>> result = manager.send_message("username", "Hello!")
        >>> manager.close()
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize Message Manager"""
        super().__init__(config)
        self.logger.info("✨ MessageManager initialized")

    def send_message(
        self,
        username: str,
        message: str,
        add_delay: bool = True
    ) -> dict:
        """
        Send a direct message to an Instagram user

        Args:
            username: Instagram username (without @)
            message: Message text to send
            add_delay: Add random delay after sending (rate limiting)

        Returns:
            dict with keys:
                - success (bool): Whether operation succeeded
                - status (str): 'sent', 'error'
                - message (str): Human-readable status message
                - username (str): Target username

        Example:
            >>> result = manager.send_message("instagram", "Hello!")
            >>> if result['success']:
            ...     print(f"✅ {result['message']}")
        """
        self.logger.info(f"📨 Sending message to @{username}")

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

            # Step 1: Click "Message" button
            if not self._click_message_button():
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Could not find Message button for @{username}',
                    'username': username
                }

            # Wait for message box to open
            time.sleep(2)

            # Step 2: Type message in input field
            if not self._type_message(message):
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Could not type message for @{username}',
                    'username': username
                }

            # Step 3: Click Send button
            if not self._click_send_button():
                return {
                    'success': False,
                    'status': 'error',
                    'message': f'Could not send message to @{username}',
                    'username': username
                }

            self.logger.info(f"✅ Successfully sent message to @{username}")

            # Add delay for rate limiting
            if add_delay:
                delay = random.uniform(3, 5)
                self.logger.debug(f"⏱️ Rate limit delay: {delay:.1f}s")
                time.sleep(delay)

            return {
                'success': True,
                'status': 'sent',
                'message': f'Successfully sent message to @{username}',
                'username': username
            }

        except Exception as e:
            self.logger.error(f"❌ Error sending message to @{username}: {e}")
            return {
                'success': False,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'username': username
            }

    def batch_send(
        self,
        usernames: list,
        message: str,
        delay_between: tuple = (3, 5),
        stop_on_error: bool = False
    ) -> dict:
        """
        Send message to multiple users

        Args:
            usernames: List of usernames to message
            message: Message text to send (same for all)
            delay_between: Random delay range between sends (min, max) in seconds
            stop_on_error: Stop if any send fails

        Returns:
            dict with keys:
                - total (int): Total users to message
                - succeeded (int): Successfully sent
                - failed (int): Failed attempts
                - results (list): Individual results for each user

        Example:
            >>> result = manager.batch_send(
            ...     ['user1', 'user2', 'user3'],
            ...     "Hello from bot!"
            ... )
            >>> print(f"Sent {result['succeeded']}/{result['total']} messages")
        """
        self.logger.info(f"📦 Batch send: {len(usernames)} messages")

        results = []
        succeeded = 0
        failed = 0

        for i, username in enumerate(usernames, 1):
            self.logger.info(f"[{i}/{len(usernames)}] Sending to @{username}")

            result = self.send_message(username, message, add_delay=False)
            results.append(result)

            if result['status'] == 'sent':
                succeeded += 1
            else:
                failed += 1
                if stop_on_error:
                    self.logger.warning(f"⚠️ Stopping due to error on @{username}")
                    break

            # Add delay between sends (except for last one)
            if i < len(usernames):
                delay = random.uniform(*delay_between)
                self.logger.debug(f"⏱️ Waiting {delay:.1f}s before next send...")
                time.sleep(delay)

        summary = {
            'total': len(usernames),
            'succeeded': succeeded,
            'failed': failed,
            'results': results
        }

        self.logger.info(
            f"✅ Batch send complete: "
            f"{succeeded} sent, {failed} failed"
        )

        return summary

    def _click_message_button(self) -> bool:
        """
        Click the "Message" button on profile

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            # Find Message button
            # Method 1: Look for button with text "Message"
            message_button = self.page.locator('div[role="button"]:has-text("Message")').first

            if message_button.count() == 0:
                # Method 2: Try with different selector
                message_button = self.page.locator('button:has-text("Message")').first

            if message_button.count() == 0:
                self.logger.warning("Message button not found")
                return False

            # Click button
            message_button.click(timeout=3000)
            time.sleep(1.5)  # Wait for message box to open

            self.logger.debug("✓ Message button clicked")
            return True

        except Exception as e:
            self.logger.warning(f"Error clicking Message button: {e}")
            return False

    def _type_message(self, message: str) -> bool:
        """
        Type message in the input field

        Args:
            message: Text to type

        Returns:
            True if typed successfully, False otherwise
        """
        try:
            # Find message input field
            # Method 1: contenteditable div with role="textbox"
            message_input = self.page.locator('div[role="textbox"][contenteditable="true"]').first

            if message_input.count() == 0:
                # Method 2: Try with aria-label
                message_input = self.page.locator('div[aria-label="Message"][contenteditable="true"]').first

            if message_input.count() == 0:
                self.logger.warning("Message input field not found")
                return False

            # Click to focus
            message_input.click(timeout=3000)
            time.sleep(0.5)

            # Type message
            message_input.type(message, delay=50)  # 50ms delay between characters (natural typing)
            time.sleep(0.5)

            self.logger.debug(f"✓ Typed message: {message[:50]}...")
            return True

        except Exception as e:
            self.logger.warning(f"Error typing message: {e}")
            return False

    def _click_send_button(self) -> bool:
        """
        Click the Send button

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            # Find Send button
            # Method 1: div with aria-label="Send"
            send_button = self.page.locator('div[aria-label="Send"][role="button"]').first

            if send_button.count() == 0:
                # Method 2: Look for SVG with aria-label="Send"
                send_button = self.page.locator('svg[aria-label="Send"]').locator('..').first

            if send_button.count() == 0:
                self.logger.warning("Send button not found")
                return False

            # Click button
            send_button.click(timeout=3000)
            time.sleep(1)  # Wait for message to send

            self.logger.debug("✓ Send button clicked")
            return True

        except Exception as e:
            self.logger.warning(f"Error clicking Send button: {e}")
            return False

    def scrape(self, *args, **kwargs):
        """Required by BaseScraper - not used in MessageManager"""
        raise NotImplementedError("MessageManager does not implement scrape()")
