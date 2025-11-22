"""
Instagram Scraper - Reel data extractor
Extract tags, likes, and timestamps from individual reels

ALOHIDA FAYL - FAQAT REELS UCHUN!
"""

import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import HTMLStructureChangedError


@dataclass
class ReelData:
    """Reel data structure"""
    url: str
    tagged_accounts: List[str]
    likes: str
    timestamp: str
    content_type: str = 'Reel'  # Always 'Reel'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ReelDataScraper(BaseScraper):
    """
    Instagram REEL data scraper - FAQAT REELS!

    Features:
    - Extract tagged accounts from reels (via popup button)
    - Extract likes count
    - Extract reel timestamp
    - Multiple fallback methods
    - Error handling
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize reel data scraper"""
        super().__init__(config)
        self.logger.info("ReelDataScraper ready (REELS ONLY)")

    def scrape(
        self,
        reel_url: str,
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True
    ) -> ReelData:
        """
        Scrape data from a single REEL

        Args:
            reel_url: URL of the reel (must contain /reel/)
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract reel timestamp

        Returns:
            ReelData object
        """
        # Validate it's a reel URL
        if '/reel/' not in reel_url:
            raise ValueError(f"Invalid reel URL: {reel_url} (must contain /reel/)")

        self.logger.info(f"🎬 Scraping REEL: {reel_url}")

        # Navigate to reel
        self.goto_url(reel_url)

        # CRITICAL: Wait for content to load
        time.sleep(self.config.reel_open_delay)

        # Extract data
        tagged_accounts = self.get_tagged_accounts() if get_tags else []
        likes = self.get_likes_count() if get_likes else 'N/A'
        timestamp = self.get_timestamp() if get_timestamp else 'N/A'

        data = ReelData(
            url=reel_url,
            tagged_accounts=tagged_accounts,
            likes=likes,
            timestamp=timestamp,
            content_type='Reel'
        )

        self.logger.info(
            f"✅ Extracted [Reel]: {len(data.tagged_accounts)} tags, "
            f"{data.likes} likes, {data.timestamp}"
        )

        return data

    def scrape_multiple(
        self,
        reel_urls: List[str],
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True,
        delay_between_reels: bool = True
    ) -> List[ReelData]:
        """
        Scrape multiple reels sequentially

        Args:
            reel_urls: List of reel URLs
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract reel timestamp
            delay_between_reels: Add delay between reels (rate limiting)

        Returns:
            List of ReelData objects
        """
        self.logger.info(f"🎬 Scraping {len(reel_urls)} reels...")

        # Load session and setup browser
        session_data = self.load_session()
        self.setup_browser(session_data)

        results = []
        start_time = time.time()

        try:
            for i, url in enumerate(reel_urls, 1):
                self.logger.info(f"[{i}/{len(reel_urls)}] Processing Reel: {url}")

                try:
                    data = self.scrape(
                        url,
                        get_tags=get_tags,
                        get_likes=get_likes,
                        get_timestamp=get_timestamp
                    )
                    results.append(data)

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    # Add placeholder data
                    results.append(ReelData(
                        url=url,
                        tagged_accounts=[],
                        likes='ERROR',
                        timestamp='N/A',
                        content_type='Reel'
                    ))

                # Delay between reels (rate limiting)
                if delay_between_reels and i < len(reel_urls):
                    delay = random.uniform(
                        self.config.post_scrape_delay_min,
                        self.config.post_scrape_delay_max
                    )
                    self.logger.debug(f"⏱️ Waiting {delay:.1f}s...")
                    time.sleep(delay)

            # Print final statistics
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.likes != 'ERROR')

            self.logger.info(
                f"\n{'='*70}\n"
                f"📊 REEL SCRAPING COMPLETE\n"
                f"{'='*70}\n"
                f"Total Reels: {len(reel_urls)}\n"
                f"Successfully scraped: {success_count}/{len(reel_urls)} "
                f"({(success_count/len(reel_urls)*100):.1f}%)\n"
                f"Failed: {len(reel_urls) - success_count}\n"
                f"Total time: {total_time:.2f}s\n"
                f"Average time per reel: {total_time/len(reel_urls):.2f}s\n"
                f"{'='*70}"
            )

            return results

        finally:
            self.close()

    # ==================== REEL-SPECIFIC EXTRACTION METHODS ====================

    def get_likes_count(self) -> str:
        """
        Extract likes count from REEL

        Reel likes location:
        <span class="x1ypdohk x1s688f x2fvf9 xe9ewy2" role="button" tabindex="0">3</span>

        Returns:
            Likes count as string
        """
        # Method 1: Reel-specific selector
        try:
            likes_span = self.page.locator('span.x1ypdohk.x1s688f.x2fvf9.xe9ewy2[role="button"]').first
            likes_text = likes_span.inner_text(timeout=3000).strip()
            if likes_text:
                self.logger.debug(f"✓ Found reel likes: {likes_text}")
                return likes_text.replace(',', '')
        except Exception as e:
            self.logger.debug(f"Reel likes method 1 failed: {e}")

        # Method 2: General span with role=button (first one is usually likes)
        try:
            spans = self.page.locator('span[role="button"]').all()
            for span in spans[:3]:  # Check first 3
                try:
                    text = span.inner_text(timeout=2000).strip()
                    # Check if it looks like a number
                    if text and (text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit() or 'K' in text or 'M' in text):
                        self.logger.debug(f"✓ Found reel likes (method 2): {text}")
                        return text.replace(',', '')
                except:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 2 failed: {e}")

        # Method 3: Try any span with number-like content
        try:
            section = self.page.locator('section').first
            spans = section.locator('span').all()
            for span in spans[:10]:  # Check first 10 spans
                try:
                    text = span.inner_text(timeout=1000).strip()
                    # Check if it's purely numeric or has K/M notation
                    if text and len(text) < 20:  # Reasonable length for likes
                        clean_text = text.replace(',', '').replace('.', '')
                        if clean_text.replace('K', '').replace('M', '').isdigit():
                            self.logger.debug(f"✓ Found reel likes (method 3): {text}")
                            return text.replace(',', '')
                except:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 3 failed: {e}")

        self.logger.warning("Failed to extract reel likes count")
        return 'N/A'

    def get_timestamp(self) -> str:
        """
        Extract timestamp from REEL

        Reel timestamp location:
        <time class="x1p4m5qa" datetime="2025-07-23T12:34:14.000Z" title="Jul 23, 2025">July 23</time>

        Returns:
            Timestamp string
        """
        # Method 1: time.x1p4m5qa selector (reel-specific)
        try:
            time_element = self.page.locator('time.x1p4m5qa').first

            # Try title attribute first (most readable)
            title = time_element.get_attribute('title', timeout=3000)
            if title:
                self.logger.debug(f"✓ Found reel timestamp (title): {title}")
                return title

            # Try datetime attribute
            datetime_str = time_element.get_attribute('datetime', timeout=3000)
            if datetime_str:
                self.logger.debug(f"✓ Found reel timestamp (datetime): {datetime_str}")
                return datetime_str

            # Fallback to text
            text = time_element.inner_text(timeout=3000)
            if text:
                self.logger.debug(f"✓ Found reel timestamp (text): {text}")
                return text
        except Exception as e:
            self.logger.debug(f"Reel timestamp method 1 failed: {e}")

        # Method 2: Any time element (fallback)
        try:
            time_element = self.page.locator('time').first

            # Try title first
            title = time_element.get_attribute('title')
            if title:
                self.logger.debug(f"✓ Found reel timestamp (fallback title): {title}")
                return title

            # Try datetime
            datetime_str = time_element.get_attribute('datetime')
            if datetime_str:
                self.logger.debug(f"✓ Found reel timestamp (fallback datetime): {datetime_str}")
                return datetime_str

            # Try text
            text = time_element.inner_text()
            if text:
                self.logger.debug(f"✓ Found reel timestamp (fallback text): {text}")
                return text
        except Exception as e:
            self.logger.debug(f"Reel timestamp method 2 failed: {e}")

        self.logger.warning("Failed to extract reel timestamp")
        return 'N/A'

    def get_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from REEL via popup button

        Reel tag extraction:
        1. Find tag button: <button> with <svg aria-label="Tags">
        2. Click the button to open popup
        3. Extract href attributes from popup: href="/username/"
        4. Close popup

        Returns:
            List of usernames (without @)
        """
        tagged = []

        try:
            # Step 1: Find and click tag button
            self.logger.debug("Looking for reel tag button...")

            # Look for button with Tags SVG
            tag_button = self.page.locator('button:has(svg[aria-label="Tags"])').first

            # Check if button exists
            if tag_button.count() == 0:
                self.logger.debug("No tag button found - reel has no tags")
                return ['No tags']

            # Click the tag button
            self.logger.debug("Clicking tag button...")
            tag_button.click(timeout=3000)

            # Step 2: Wait for popup to appear
            time.sleep(self.config.ui_animation_delay)

            # Step 3: Extract tagged accounts from popup (EXCLUDE comment section!)
            self.logger.debug("Extracting tagged accounts from popup...")

            # Method 1: Links ONLY from popup container (NOT from comment section!)
            try:
                # Wait for popup content to load
                time.sleep(self.config.popup_content_load_delay)

                # CRITICAL FIX: Extract links ONLY from within popup container
                # Popup class: x1cy8zhl x9f619 x78zum5 xl56j7k x2lwn1j xeuugli x47corl
                self.logger.debug("Looking for popup container...")

                # Find popup container - look for div with these specific classes
                popup_container = self.page.locator('div.x1cy8zhl.x9f619.x78zum5.xl56j7k.x2lwn1j.xeuugli.x47corl').first

                if popup_container.count() == 0:
                    self.logger.debug("Popup container not found, trying alternative selectors...")
                    # Alternative: any div with role="dialog" or similar popup indicators
                    popup_container = self.page.locator('div[role="dialog"]').first

                # Extract links ONLY from within the popup container
                links = popup_container.locator('a[href^="/"]').all()
                self.logger.debug(f"Found {len(links)} links in popup")

                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=1000)
                        if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                            username = href.strip('/').split('/')[-1]

                            # Filter out Instagram system paths
                            if username in ['explore', 'direct', 'accounts', 'p', 'reel', 'tv', 'stories']:
                                continue

                            if username not in tagged:
                                tagged.append(username)
                                self.logger.debug(f"✓ Added tag: {username}")
                    except:
                        continue

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags in reel: {tagged}")

                    # Close popup by clicking close button
                    try:
                        close_button = self.page.locator('button:has(svg[aria-label="Close"])').first
                        close_button.click(timeout=2000)
                        time.sleep(self.config.popup_close_delay)
                    except:
                        # Try pressing Escape
                        try:
                            self.page.keyboard.press('Escape')
                            time.sleep(self.config.popup_close_delay)
                        except:
                            pass

                    return tagged
            except Exception as e:
                self.logger.debug(f"Reel tag extraction from popup failed: {e}")

            # If no tags found but popup opened, close it
            try:
                self.page.keyboard.press('Escape')
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Reel tag button click failed: {e}")

        # Fallback: Try looking for div._aa1y (post-style tags)
        try:
            self.logger.debug("Fallback: Looking for post-style tags in reel...")
            tag_containers = self.page.locator('div._aa1y').all()
            for container in tag_containers:
                try:
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href', timeout=2000)
                    if href:
                        username = href.strip('/').split('/')[-1]
                        if username and username not in tagged:
                            tagged.append(username)
                except:
                    continue

            if tagged:
                self.logger.info(f"✓ Found {len(tagged)} tags (fallback method): {tagged}")
                return tagged
        except Exception as e:
            self.logger.debug(f"Fallback tag extraction failed: {e}")

        self.logger.warning("No tags found in reel")
        return ['No tags']
