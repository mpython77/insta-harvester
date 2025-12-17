"""
Instagram Scraper - Profile data scraper
Extract posts, followers, and following counts from Instagram profiles
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import ProfileNotFoundError, HTMLStructureChangedError


@dataclass
class ProfileData:
    """Profile data structure"""
    username: str
    posts: str
    followers: str
    following: str
    is_verified: bool = False  # Whether the account has verified badge
    category: Optional[str] = None  # Profile category (Actor, Model, Photographer, etc.)
    bio: Optional[str] = None  # Complete bio with all information (links, emails, mentions, text)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ProfileScraper(BaseScraper):
    """
    Instagram profile scraper

    Features:
    - Extract posts count
    - Extract followers count
    - Extract following count
    - Check verified badge status
    - Extract profile category (Actor, Model, Photographer, etc.)
    - Extract complete bio (text, links, emails, mentions, contact info)
    - HTML structure change detection
    - Parallel execution support
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize profile scraper"""
        super().__init__(config)
        self.logger.info("ProfileScraper ready")

    def scrape(
        self,
        username: str,
        *,
        get_posts: bool = True,
        get_followers: bool = True,
        get_following: bool = True
    ) -> ProfileData:
        """
        Scrape profile data

        Args:
            username: Instagram username (without @)
            get_posts: Extract posts count
            get_followers: Extract followers count
            get_following: Extract following count

        Returns:
            ProfileData object with verified status

        Raises:
            ProfileNotFoundError: If profile doesn't exist
            HTMLStructureChangedError: If HTML structure changed
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"Starting profile scrape for: @{username}")

        # Check if browser is already setup (SharedBrowser mode)
        is_shared_browser = self.page is not None and self.browser is not None

        if is_shared_browser:
            self.logger.debug("Using existing browser session (SharedBrowser mode)")
        else:
            # Load session and setup browser (standalone mode)
            self.logger.debug("Setting up new browser session (standalone mode)")
            session_data = self.load_session()
            self.setup_browser(session_data)

        try:
            # Navigate to profile
            profile_url = self.config.profile_url_pattern.format(username=username)
            self.goto_url(profile_url)

            # Check if profile exists
            if not self._profile_exists():
                raise ProfileNotFoundError(f"Profile @{username} not found")

            # Wait for profile stats to load
            self._wait_for_profile_stats()

            # Extract data
            data = ProfileData(
                username=username,
                posts=self.get_posts_count() if get_posts else 'N/A',
                followers=self.get_followers_count() if get_followers else 'N/A',
                following=self.get_following_count() if get_following else 'N/A',
                is_verified=self._check_verified(),
                category=self._get_category(),
                bio=self._get_bio()
            )

            verified_status = "✓ Verified" if data.is_verified else "Not verified"
            category_info = f", Category: {data.category}" if data.category else ""
            self.logger.info(
                f"Profile scrape complete: {data.posts} posts, "
                f"{data.followers} followers, {data.following} following, {verified_status}{category_info}"
            )

            return data

        finally:
            # Only close browser if not in SharedBrowser mode
            if not is_shared_browser:
                self.close()
            else:
                self.logger.debug("Keeping browser open (SharedBrowser mode)")

    def _profile_exists(self) -> bool:
        """Check if profile exists"""
        try:
            content = self.page.content()
            for not_found_string in self.config.profile_not_found_strings:
                if not_found_string in content:
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking profile existence: {e}")
            return False

    def _wait_for_profile_stats(self) -> None:
        """Wait for profile statistics to load"""
        self.logger.debug("Waiting for profile stats...")
        try:
            self.page.wait_for_selector(
                self.config.selector_posts_count,
                timeout=self.config.posts_count_timeout
            )
            # Additional delay for stability
            time.sleep(self.config.ui_stability_delay)
        except Exception as e:
            self.logger.warning(f"Profile stats selector timeout: {e}")
            # Fallback delay
            time.sleep(self.config.page_stability_delay)

    def _check_verified(self) -> bool:
        """
        Check if account has verified badge

        Returns:
            True if account is verified, False otherwise
        """
        try:
            verified_badge = self.page.locator(self.config.selector_verified_badge).first
            is_verified = verified_badge.count() > 0
            if is_verified:
                self.logger.debug("✓ Account is verified")
            return is_verified
        except Exception as e:
            self.logger.debug(f"Verified check failed (account not verified or error): {e}")
            return False

    def _get_category(self) -> Optional[str]:
        """
        Extract profile category (Actor, Model, Photographer, etc.)

        Returns:
            Profile category string or None if not set
        """
        try:
            category_element = self.page.locator(self.config.selector_profile_category).first
            if category_element.count() > 0:
                category = category_element.inner_text().strip()
                if category:
                    self.logger.debug(f"✓ Profile category: {category}")
                    return category
            self.logger.debug("No profile category found")
            return None
        except Exception as e:
            self.logger.debug(f"Category extraction failed: {e}")
            return None

    def _get_bio(self) -> Optional[str]:
        """
        Extract complete bio information including text, links, emails, mentions, and contact info

        Returns:
            Complete bio text with all information or None if empty
        """
        try:
            bio_section = self.page.locator(self.config.selector_profile_bio_section).first
            if bio_section.count() > 0:
                # Get all text content from bio section
                bio_text = bio_section.inner_text().strip()
                if bio_text:
                    # Remove excessive whitespace but preserve line breaks
                    bio_text = '\n'.join(line.strip() for line in bio_text.split('\n') if line.strip())
                    self.logger.debug(f"✓ Bio extracted ({len(bio_text)} characters)")
                    return bio_text
            self.logger.debug("No bio found")
            return None
        except Exception as e:
            self.logger.debug(f"Bio extraction failed: {e}")
            return None

    def get_posts_count(self) -> str:
        """
        Extract posts count

        Returns:
            Posts count as string (e.g., "1870")
        """
        selector = self.config.selector_posts_count

        def extract():
            posts_element = self.page.locator(selector).first
            posts_text = posts_element.locator(self.config.selector_html_span).first.inner_text()
            return posts_text.strip().replace(',', '')

        result = self.safe_extract(
            extract,
            element_name='posts_count',
            selector=selector,
            default='N/A'
        )

        if result == 'N/A':
            raise HTMLStructureChangedError(
                'posts_count',
                selector,
                "Cannot find posts count. Instagram may have changed their HTML structure."
            )

        return result

    def get_followers_count(self) -> str:
        """
        Extract followers count

        Returns:
            Followers count as string (e.g., "32757")
        """
        selector = self.config.selector_followers_link

        def extract():
            followers_link = self.page.locator(selector).first
            # Try title attribute first (exact count)
            title_span = followers_link.locator('span[title]').first
            if title_span:
                return title_span.get_attribute('title').replace(',', '')
            # Fallback to visible text
            return followers_link.locator(self.config.selector_html_span).first.inner_text().replace(',', '')

        result = self.safe_extract(
            extract,
            element_name='followers_count',
            selector=selector,
            default='N/A'
        )

        if result == 'N/A':
            raise HTMLStructureChangedError(
                'followers_count',
                selector,
                "Cannot find followers count. Instagram may have changed their HTML structure."
            )

        return result

    def get_following_count(self) -> str:
        """
        Extract following count

        Returns:
            Following count as string (e.g., "5447")
        """
        selector = self.config.selector_following_link

        def extract():
            following_link = self.page.locator(selector).first
            return following_link.locator(self.config.selector_html_span).first.inner_text().replace(',', '')

        result = self.safe_extract(
            extract,
            element_name='following_count',
            selector=selector,
            default='N/A'
        )

        if result == 'N/A':
            raise HTMLStructureChangedError(
                'following_count',
                selector,
                "Cannot find following count. Instagram may have changed their HTML structure."
            )

        return result
