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

        Uses targeted extraction to avoid highlights and other non-bio content:
        1. Bio text: Only from bio section (not highlights/other sections)
        2. External links: From link containers with specific attributes
        3. Fallback: Old bio section selector

        Returns:
            Complete bio text with all information or None if empty
        """
        try:
            bio_parts = []

            # Strategy 1: Extract bio text ONLY from bio section
            # Look for span._ap3a that is a direct child of bio section, not from highlights
            # We need to be more selective - only get first few span._ap3a (bio is usually first 1-2)
            bio_text_spans = self.page.locator(self.config.selector_profile_bio_text).all()

            # Filter: Only take first 2-3 bio text spans (bio is always at the top)
            # This avoids getting highlights names and other sections
            bio_span_count = 0
            max_bio_spans = 3  # Bio is usually within first 3 spans

            if bio_text_spans:
                for span in bio_text_spans:
                    try:
                        # Check if this span is inside a link container (skip if it is)
                        parent_html = span.evaluate('el => el.parentElement?.outerHTML || ""')
                        if 'svg' in parent_html or 'aria-label="Link icon"' in parent_html:
                            continue  # Skip spans inside link containers

                        # Check if this is inside a button/clickable area for bio (valid)
                        # or if it's a highlight/other section (invalid)
                        text = span.inner_text().strip()

                        # Skip if empty or already added
                        if not text or text in bio_parts:
                            continue

                        # Skip very short texts (likely not bio)
                        if len(text) < 3:
                            continue

                        # Only take first few spans (bio is at the top)
                        if bio_span_count >= max_bio_spans:
                            break

                        bio_parts.append(text)
                        bio_span_count += 1
                        self.logger.debug(f"✓ Found bio text #{bio_span_count}: {text[:50]}...")

                    except Exception as e:
                        self.logger.debug(f"Error extracting bio span: {e}")
                        continue

            # Strategy 2: Extract external links from bio
            # Look for div.html-div with Link icon (external links section)
            try:
                # Find divs with Link icon SVG (these are external link containers)
                link_containers = self.page.locator('div.html-div:has(svg[aria-label="Link icon"])').all()

                for container in link_containers:
                    try:
                        # Get link text from <a> tags inside this container
                        links = container.locator('a div._ap3a._aaco._aacw._atqw._aada._aade').all()
                        for link in links:
                            try:
                                link_text = link.inner_text().strip()
                                if link_text and link_text not in bio_parts:
                                    bio_parts.append(link_text)
                                    self.logger.debug(f"✓ Found external link: {link_text}")
                            except Exception:
                                continue
                    except Exception:
                        continue

                # Also get Threads links
                threads_links = self.page.locator('a[href*="threads.com"] span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62').all()
                for link in threads_links:
                    try:
                        link_text = link.inner_text().strip()
                        if link_text and link_text not in bio_parts:
                            bio_parts.append(link_text)
                            self.logger.debug(f"✓ Found Threads link: {link_text}")
                    except Exception:
                        continue

            except Exception as e:
                self.logger.debug(f"Error extracting links: {e}")

            # Strategy 3: Fallback - try old bio section selector
            if not bio_parts:
                self.logger.debug("Trying fallback bio section selector...")
                bio_section = self.page.locator(self.config.selector_profile_bio_section).first
                if bio_section.count() > 0:
                    bio_text = bio_section.inner_text().strip()
                    if bio_text:
                        bio_parts.append(bio_text)
                        self.logger.debug(f"✓ Bio extracted via fallback ({len(bio_text)} characters)")

            # Combine all bio parts
            if bio_parts:
                # Join parts with newline, remove duplicates
                full_bio = '\n'.join(bio_parts)
                # Clean up whitespace while preserving line breaks
                full_bio = '\n'.join(line.strip() for line in full_bio.split('\n') if line.strip())

                if full_bio:
                    self.logger.debug(f"✓ Complete bio extracted ({len(full_bio)} characters, {len(bio_parts)} parts)")
                    return full_bio

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
