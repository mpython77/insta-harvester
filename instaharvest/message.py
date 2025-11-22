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
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for message box to open...")
            time.sleep(self.config.popup_open_delay)

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
                delay = random.uniform(self.config.message_delay_min, self.config.message_delay_max)
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
                delay = random.uniform(self.config.batch_operation_delay_min, self.config.batch_operation_delay_max)
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
            # Add random delay before clicking (allows page to fully load)
            delay_before = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before:.1f}s before clicking Message button...")
            time.sleep(delay_before)

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

            # Wait for message box to open
            self.logger.debug(f"⏱️ Waiting {self.config.popup_open_delay}s for message box to open...")
            time.sleep(self.config.popup_open_delay)

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
            # Try multiple selectors for message input
            message_input = None

            selectors_to_try = [
                # Method 1: By role and contenteditable
                'div[role="textbox"][contenteditable="true"]',
                # Method 2: By aria-label
                'div[aria-label="Message"][contenteditable="true"]',
                # Method 3: By data attribute
                'div[data-lexical-editor="true"][contenteditable="true"]',
                # Method 4: By class and contenteditable
                'div.notranslate[contenteditable="true"]',
                # Method 5: Any contenteditable div with placeholder
                'div[contenteditable="true"][aria-placeholder="Message..."]',
                # Method 6: Generic contenteditable in message area
                'div[contenteditable="true"]',
            ]

            for selector in selectors_to_try:
                try:
                    input_field = self.page.locator(selector).first
                    if input_field.count() > 0:
                        # Check if visible
                        if input_field.is_visible(timeout=2000):
                            message_input = input_field
                            self.logger.debug(f"✓ Found message input using: {selector}")
                            break
                except Exception:
                    continue

            if message_input is None:
                self.logger.warning("Message input field not found")
                return False

            # Add small delay before clicking input (allows UI to stabilize)
            delay_before_input = random.uniform(self.config.input_before_type_delay_min, self.config.input_before_type_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before_input:.1f}s before clicking input field...")
            time.sleep(delay_before_input)

            # Click to focus
            try:
                message_input.click(timeout=3000)
                self.logger.debug("✓ Clicked message input field")
            except Exception as e:
                self.logger.warning(f"Could not click input field: {e}")
                # Try to focus anyway

            time.sleep(self.config.input_focus_delay)

            # Type message - try multiple methods
            try:
                # Method 1: Use Playwright's type method
                message_input.fill('')  # Clear any existing text
                message_input.type(message, delay=50)  # 50ms delay between characters
                self.logger.debug("✓ Typed message using type() method")
            except Exception as e1:
                self.logger.debug(f"type() failed: {e1}, trying fill()...")
                try:
                    # Method 2: Use fill method
                    message_input.fill(message)
                    self.logger.debug("✓ Typed message using fill() method")
                except Exception as e2:
                    self.logger.warning(f"Both type() and fill() failed: {e2}")
                    return False

            # Wait after typing (allows message to be processed)
            delay_after_type = random.uniform(self.config.input_after_type_delay_min, self.config.input_after_type_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_after_type:.1f}s after typing...")
            time.sleep(delay_after_type)

            self.logger.debug(f"✓ Typed message: {message[:50]}...")
            return True

        except Exception as e:
            self.logger.warning(f"Error typing message: {e}")
            return False

    def _click_send_button(self) -> bool:
        """
        Click the Send button
        Note: Send button only appears after typing message!

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            # Add random delay before clicking send (allows message to be ready)
            delay_before = random.uniform(self.config.action_delay_min, self.config.action_delay_max)
            self.logger.debug(f"⏱️ Waiting {delay_before:.1f}s before clicking Send button...")
            time.sleep(delay_before)

            # Try multiple selectors for Send button
            send_button = None

            selectors_to_try = [
                # Method 1: div with aria-label="Send" and role="button"
                'div[aria-label="Send"][role="button"]',
                # Method 2: Any element with aria-label="Send"
                '[aria-label="Send"][role="button"]',
                # Method 3: div with role=button containing Send SVG
                'div[role="button"]:has(svg[aria-label="Send"])',
                # Method 4: Parent of SVG with aria-label="Send"
                'svg[aria-label="Send"]',  # Will click parent
                # Method 5: Button with Send text
                'div[role="button"]:has-text("Send")',
                # Method 6: By Instagram button classes with Send
                'div.x1i10hfl[role="button"]:has(svg[aria-label="Send"])',
            ]

            for selector in selectors_to_try:
                try:
                    if selector == 'svg[aria-label="Send"]':
                        # Special case: find SVG then get parent
                        svg = self.page.locator(selector).first
                        if svg.count() > 0:
                            # Get parent div (the clickable button)
                            button = svg.locator('..').first
                            if button.count() > 0 and button.is_visible(timeout=2000):
                                send_button = button
                                self.logger.debug(f"✓ Found Send button using: {selector} (parent)")
                                break
                    else:
                        button = self.page.locator(selector).first
                        if button.count() > 0:
                            # Check if visible (send button only appears after typing!)
                            if button.is_visible(timeout=2000):
                                send_button = button
                                self.logger.debug(f"✓ Found Send button using: {selector}")
                                break
                except Exception as e:
                    self.logger.debug(f"Selector '{selector}' failed: {e}")
                    continue

            if send_button is None:
                self.logger.warning("Send button not found - did you type the message first?")
                return False

            # Click button
            try:
                send_button.click(timeout=3000)
                self.logger.debug("✓ Send button clicked")
            except Exception as e:
                self.logger.warning(f"Failed to click Send button: {e}")
                return False

            # Wait for message to send
            self.logger.debug(f"⏱️ Waiting {self.config.button_click_delay}s for message to send...")
            time.sleep(self.config.button_click_delay)

            self.logger.debug("✓ Message sent successfully")
            return True

        except Exception as e:
            self.logger.warning(f"Error clicking Send button: {e}")
            return False

    def scrape(self, *args, **kwargs):
        """Required by BaseScraper - not used in MessageManager"""
        raise NotImplementedError("MessageManager does not implement scrape()")
