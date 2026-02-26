"""
Instagram Scraper - Profile data scraper
Extract posts, followers, and following counts from Instagram profiles
"""
import os
import logging
import re
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import ProfileNotFoundError, HTMLStructureChangedError


@dataclass
class ProfileData:
    """
    Profile data structure
    
    Attributes:
        username: Instagram username
        posts: Number of posts
        followers: Number of followers
        following: Number of following
        is_verified: True if account is verified
        is_private: True if account is private
        category: Profile category (e.g. "Musician")
        bio: Biography text
        external_links: List of external links found in bio
        threads_profile: Threads profile username/URL if available
    """
    username: str
    posts: int  # Changed to int for consistency
    followers: int
    following: int
    is_verified: bool = False
    is_private: bool = False  # New field
    category: Optional[str] = None
    bio: Optional[str] = None
    external_links: List[str] = field(default_factory=list)
    threads_profile: Optional[str] = None
    engagement_rate: Optional[float] = None  # Calculated from post data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def calculate_engagement_rate(self, avg_likes: float, avg_comments: float = 0) -> float:
        """
        Calculate engagement rate from average post metrics

        Formula: (avg_likes + avg_comments) / followers * 100

        Args:
            avg_likes: Average number of likes per post
            avg_comments: Average number of comments per post (default: 0)

        Returns:
            Engagement rate as percentage (e.g. 3.25 means 3.25%)
        """
        if self.followers <= 0:
            self.engagement_rate = 0.0
            return 0.0
        self.engagement_rate = round((avg_likes + avg_comments) / self.followers * 100, 2)
        return self.engagement_rate


class ProfileScraper(BaseScraper):
    """
    Instagram profile scraper

    Features:
    - Extract posts, followers, following counts (integers)
    - Check verified badge status
    - Detect PRIVATE accounts
    - Extract profile category
    - Extract complete bio
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

        Returns:
            ProfileData object
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

            # Check if Private
            is_private = self._is_private_account()
            if is_private:
                self.logger.warning(f"⚠️ Account @{username} is PRIVATE")

            # Wait for profile stats to load
            self._wait_for_profile_stats()

            # Extract data
            # Use safe_extract with parse_number directly
            posts = self.get_posts_count() if get_posts else 0
            followers = self.get_followers_count() if get_followers else 0
            following = self.get_following_count() if get_following else 0

            # Get complete bio data
            bio_data = self._get_bio_data()

            data = ProfileData(
                username=username,
                posts=posts,
                followers=followers,
                following=following,
                is_verified=self._check_verified(),
                is_private=is_private,
                category=self._get_category(),
                bio=bio_data['bio'],
                external_links=bio_data['external_links'],
                threads_profile=bio_data['threads_profile']
            )

            verified_status = "✓ Verified" if data.is_verified else "Not verified"
            private_status = "🔒 Private" if data.is_private else "🔓 Public"

            self.logger.info(
                f"Profile scrape complete: {data.posts} posts, "
                f"{data.followers} followers, {data.following} following, "
                f"{verified_status}, {private_status}"
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

    def _is_private_account(self) -> bool:
        """
        Check if account is private
        
        Returns:
            True if private, False otherwise
        """
        try:
            # Method 1: Check for Private icon
            private_icon = self.page.locator(self.config.selector_private_icon).first
            if private_icon.count() > 0:
                self.logger.debug("✓ Private account detected (icon)")
                return True
                
            # Method 2: Check for text indicators
            # Use body inner_text to normalize whitespace
            try:
                body_text = self.page.locator("body").inner_text()
                for indicator in self.config.selector_private_text_indicators:
                    if indicator in body_text:
                        self.logger.debug(f"✓ Private account detected (text: '{indicator}')")
                        return True
            except Exception:
                # Fallback to content check
                content = self.page.content()
                for indicator in self.config.selector_private_text_indicators:
                    if indicator in content:
                        self.logger.debug(f"✓ Private account detected (raw content: '{indicator}')")
                        return True
            
            # Method 3: Check title
            title_elem = self.page.locator(self.config.selector_private_title)
            count = title_elem.count()
            for i in range(count):
                if "Private" in title_elem.nth(i).inner_text():
                    self.logger.debug("✓ Private account detected (title)")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.debug(f"Private check error: {e}")
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

    def _get_bio_data(self) -> Dict[str, Any]:
        """
        Extract complete bio information including text, links, and threads profile
        
        Returns:
            Dictionary with 'bio', 'external_links', 'threads_profile'
        """
        result = {
            'bio': None,
            'external_links': [],
            'threads_profile': None
        }
        
        try:
            # 0. CLICK "MORE" BUTTON IF EXISTS (to expand full bio)
            # Language-agnostic approach: find button after "..." text
            try:
                clicked = self.page.evaluate('''() => {
                    // Strategy 1: Find span containing "..." followed by inline button
                    const spans = document.querySelectorAll('span');
                    for (const span of spans) {
                        // Check if this span's text ends with "..."
                        const text = span.textContent || '';
                        if (text.includes('...')) {
                            // Look for role="button" sibling or descendant
                            const buttons = span.querySelectorAll('[role="button"]');
                            for (const btn of buttons) {
                                // Must be visible and inline (part of bio expansion)
                                const style = window.getComputedStyle(btn);
                                if (style.display.includes('inline') && btn.offsetParent !== null) {
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                    }
                    
                    // Strategy 2: Find inline button with common "more" translations
                    const moreTexts = ['more', 'ещё', 'еще', 'ko\'proq', 'devamı', 'mehr', 'plus', 'más', 'altro', '更多', '続きを読む'];
                    const allButtons = document.querySelectorAll('[role="button"]');
                    for (const btn of allButtons) {
                        const btnText = (btn.textContent || '').trim().toLowerCase();
                        const style = window.getComputedStyle(btn);
                        if (style.display.includes('inline') && moreTexts.includes(btnText)) {
                            btn.click();
                            return true;
                        }
                    }
                    
                    return false;
                }''')
                
                if clicked:
                    self.logger.debug("📖 Found and clicked 'more' button to expand bio")
                    time.sleep(0.5)  # Wait for expansion animation
                    self.logger.debug("✓ Bio expanded")
            except Exception as e:
                self.logger.debug(f"More button not found or click failed (normal for short bios): {e}")
            
            # 1. EXTRACT BIO TEXT
            bio_parts = []
            seen_text = set()  # Track seen content to avoid duplicates
            bio_elements = self.page.locator(self.config.selector_profile_bio_text).all()
            
            # Common "more" button texts across languages
            more_button_texts = {'more', 'ещё', 'еще', "ko'proq", 'devamı', 'mehr', 'plus', 'más', 'altro', '更多', '続きを読む', '...'}
            
            for span in bio_elements:
                try:
                    text = span.inner_text().strip()
                    if not text or len(text) < 2:
                        continue
                    
                    # Skip "more" button text
                    if text.lower() in more_button_texts:
                        continue
                    
                    # Skip text ending with "..." followed by "more" (truncated text)
                    if text.endswith('...') or '... ' in text:
                        continue
                        
                    # Skip if it is the link container ("Link icon") button itself or inside it
                    # We used to check parentHTML, but that caught the section parent.
                    # Now check if we are inside the specific link button.
                    is_link_btn = span.evaluate('''el => {
                        const btn = el.closest('button') || el.closest('[role="button"]');
                        return btn && btn.querySelector('svg[aria-label="Link icon"]');
                    }''')
                    if is_link_btn:
                        continue
                    
                    # Skip if inside a role="button" element (e.g., the "more" button container)
                    is_inside_button = span.evaluate('el => el.closest(\'[role="button"]\') !== null')
                    if is_inside_button:
                        # But allow if it's the main bio container which might have role="button" for expand
                        parent_classes = span.evaluate('el => el.closest(\'[role="button"]\')?.className || ""')
                        if 'inline' in parent_classes.lower() or len(text) < 10:
                            continue

                    # Check if inside a link (anchor tag)
                    closest_a_href = span.evaluate('el => el.closest("a")?.href || ""')
                    if closest_a_href:
                        href_lower = closest_a_href.lower()
                        # Skip Threads, Followers, Following links
                        # Uses config ignore list
                        if any(x in href_lower for x in self.config.bio_extraction_ignore_list):
                            continue
                    
                    # Filter out stats like "100 posts" or "500 followers"
                    # Simple regex to catch digits followed by posts/followers/following
                    if re.match(r'^\d+(\.\d+)?[KkMm]?\s*(posts|followers|following)$', text, re.IGNORECASE):
                        continue
                        
                    # Filter out Highlights (Storeee, About me, etc.)
                    # These are typically in ul > li structures or specific highlight containers.
                    # Simple heuristic: Check if any parent is an LI or UL
                    is_list_item = span.evaluate('el => el.closest("li") !== null || el.closest("ul") !== null')
                    if is_list_item:
                        continue

                    # Skip if text is a substring of already added content (or vice versa)
                    text_lower = text.lower()
                    is_duplicate = False
                    for seen in seen_text:
                        if text_lower in seen or seen in text_lower:
                            is_duplicate = True
                            break
                    if is_duplicate:
                        continue
                    
                    seen_text.add(text_lower)
                    bio_parts.append(text)
                except Exception as e:
                   continue
            
            if bio_parts:
                result['bio'] = "\n".join(bio_parts)
                self.logger.debug(f"✓ Bio text found: {len(bio_parts)} parts")

            # 2. EXTRACT EXTERNAL LINKS
            # 2a. Look for embedded links in bio (e.g. @mentions)
            try:
                bio_links = self.page.locator('header section span[dir="auto"] a').all()
                for link in bio_links:
                    href = link.get_attribute('href')
                    text = link.inner_text()
                    if href and text and text not in result['external_links']:
                        # Filter out internal Instagram nav links
                        if any(x in href for x in ['/followers/', '/following/', 'threads.net']):
                            continue
                        result['external_links'].append(text)
            except Exception as e:
                self.logger.debug(f"Embedded link extraction error: {e}")

            # 2b. Look for button with Link icon
            try:
                # Find all Link Icons (universal anchor point)
                link_icons = self.page.locator(self.config.selector_bio_link_container).all()
                
                for icon in link_icons:
                    found_text = None
                    ancestor = icon
                    for i in range(4): # Check 4 levels up
                        ancestor = ancestor.locator('xpath=..')
                        
                        # 1. Check if this ancestor IS an anchor or HAS an anchor
                        # This is more reliable than text scraping
                        href = ancestor.get_attribute('href')
                        if href and href not in ['#', '', 'javascript:void(0);']:
                            # Use text if available, else href
                            text = ancestor.inner_text().strip() or href
                            found_text = text
                            break
                            
                        # Also check if it wraps an anchor (sometimes div > a > div > svg)
                        nested_a = ancestor.locator('a[href]').first
                        if nested_a.count() > 0:
                            href = nested_a.get_attribute('href')
                            if href and not 'facebook.com' in href: # Verify not a share button
                                found_text = nested_a.inner_text().strip() or href
                                break

                        # 2. Text-based heuristic (Original fallback)
                        text = ancestor.inner_text().strip()
                        if len(text) > 3 and '.' in text:
                            # Verify it's not just "Message" or "Follow"
                            if any(x in text.lower() for x in ['message', 'follow', 'contact']):
                                continue
                            found_text = text
                            break
                    
                    if found_text:
                            # Split by newline and look for the link part
                        parts = found_text.split('\n')
                        for part in parts:
                            clean_part = part.strip()
                            clean_part = clean_part.split(' and ')[0] # "and 1 more" cleanup
                            
                            if '.' in clean_part and len(clean_part) > 3:
                                # Exclude common non-link text
                                if clean_part.lower() == 'link': continue
                                
                                if clean_part not in result['external_links']:
                                        result['external_links'].append(clean_part)
            except Exception as e:
                self.logger.debug(f"Link extraction error: {e}")

            # 3. EXTRACT THREADS PROFILE
            try:
                threads_badge = self.page.locator(self.config.selector_threads_badge).first
                if threads_badge.count() > 0:
                    # Get parent anchor
                    anchor = threads_badge.locator('xpath=./ancestor::a').first
                    if anchor.count() > 0:
                        href = anchor.get_attribute('href')
                        if href and ('threads.net' in href or 'threads.com' in href):
                             # Extract username from URL
                             parts = href.split('@')
                             if len(parts) > 1:
                                 # Remove query params
                                 username = parts[1].split('?')[0]
                                 result['threads_profile'] = f"@{username}"
                                 self.logger.debug(f"✓ Threads profile found: {result['threads_profile']}")
            except Exception as e:
                 self.logger.debug(f"Threads extraction error: {e}")

            return result
            
        except Exception as e:
            self.logger.error(f"Bio extraction error: {e}")
            return result

    def _get_bio(self) -> Optional[str]:
        """Legacy wrapper - use _get_bio_data instead"""
        data = self._get_bio_data()
        return data['bio']

    def get_posts_count(self) -> int:
        """
        Extract posts count

        Returns:
            Posts count as integer
        """
        selector = self.config.selector_posts_count

        def extract():
            posts_element = self.page.locator(selector).first
            posts_text = posts_element.locator(self.config.selector_html_span).first.inner_text()
            return self.parse_number(posts_text)

        result = self.safe_extract(
            extract,
            element_name='posts_count',
            selector=selector,
            default=0
        )

        return result

    def get_followers_count(self) -> int:
        """
        Extract followers count

        Returns:
            Followers count as integer
        """
        selector = self.config.selector_followers_link

        def extract():
            followers_link = self.page.locator(selector).first
            # Try title attribute first (exact count)
            title_span = followers_link.locator('span[title]').first
            if title_span.count() > 0:
                text = title_span.get_attribute('title')
                return self.parse_number(text)
            
            # Fallback to visible text
            text = followers_link.locator(self.config.selector_html_span).first.inner_text()
            return self.parse_number(text)

        result = self.safe_extract(
            extract,
            element_name='followers_count',
            selector=selector,
            default=0
        )

        return result

    def get_following_count(self) -> int:
        """
        Extract following count

        Returns:
            Following count as integer
        """
        selector = self.config.selector_following_link

        def extract():
            following_link = self.page.locator(selector).first
            text = following_link.locator(self.config.selector_html_span).first.inner_text()
            return self.parse_number(text)

        result = self.safe_extract(
            extract,
            element_name='following_count',
            selector=selector,
            default=0
        )

        return result
