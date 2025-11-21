"""
Instagram Scraper - Main Orchestrator
Coordinates all scraping operations in a single workflow
"""

import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import ScraperConfig
from .profile import ProfileScraper, ProfileData
from .post_links import PostLinksScraper
from .post_data import PostDataScraper, PostData
from .logger import setup_logger


class InstagramOrchestrator:
    """
    Main orchestrator for complete Instagram scraping workflow

    Workflow:
    1. Scrape profile (posts, followers, following)
    2. Collect all post links
    3. Scrape data from each post (tags, likes, timestamp)

    Features:
    - Complete end-to-end scraping
    - Progress tracking
    - Error resilience
    - Data export
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize orchestrator

        Args:
            config: Scraper configuration
        """
        self.config = config or ScraperConfig()
        self.logger = setup_logger(
            name='InstagramOrchestrator',
            log_file=self.config.log_file,
            level=self.config.log_level,
            log_to_console=self.config.log_to_console
        )

        self.logger.info("=" * 60)
        self.logger.info("Instagram Scraper Orchestrator Initialized")
        self.logger.info("=" * 60)

    def scrape_complete_profile(
        self,
        username: str,
        scrape_posts: bool = True,
        export_results: bool = True
    ) -> Dict[str, Any]:
        """
        Complete scraping workflow for a profile

        Args:
            username: Instagram username
            scrape_posts: Whether to scrape individual post data
            export_results: Export results to files

        Returns:
            Dictionary with all scraped data
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Starting complete profile scrape: @{username}")
        self.logger.info(f"{'='*60}\n")

        results = {
            'username': username,
            'profile': None,
            'post_links': [],
            'posts_data': []
        }

        # Step 1: Scrape profile stats
        self.logger.info("STEP 1: Scraping profile stats...")
        profile_data = self._scrape_profile_stats(username)
        results['profile'] = profile_data.to_dict()
        self.logger.info(f"✓ Profile stats scraped")

        # Step 2: Collect post links
        self.logger.info("\nSTEP 2: Collecting post links...")
        post_links = self._collect_post_links(username)
        results['post_links'] = post_links
        self.logger.info(f"✓ Collected {len(post_links)} post links")

        # Step 3: Scrape post data
        if scrape_posts and post_links:
            self.logger.info(f"\nSTEP 3: Scraping data from {len(post_links)} posts...")
            posts_data = self._scrape_posts_data(post_links)
            results['posts_data'] = [p.to_dict() for p in posts_data]
            self.logger.info(f"✓ Scraped {len(posts_data)} posts")

        # Export results
        if export_results:
            self.logger.info("\nExporting results...")
            self._export_results(results)
            self.logger.info("✓ Results exported")

        self.logger.info(f"\n{'='*60}")
        self.logger.info("SCRAPING COMPLETE!")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Profile: {results['profile']}")
        self.logger.info(f"Post links: {len(results['post_links'])}")
        self.logger.info(f"Posts scraped: {len(results['posts_data'])}")
        self.logger.info(f"{'='*60}\n")

        return results

    def _scrape_profile_stats(self, username: str) -> ProfileData:
        """Scrape profile statistics"""
        scraper = ProfileScraper(self.config)
        return scraper.scrape(username)

    def _collect_post_links(self, username: str) -> List[str]:
        """Collect all post links from profile"""
        scraper = PostLinksScraper(self.config)
        return scraper.scrape(
            username,
            save_to_file=True
        )

    def _scrape_posts_data(self, post_links: List[str]) -> List[PostData]:
        """Scrape data from all posts"""
        scraper = PostDataScraper(self.config)
        return scraper.scrape_multiple(
            post_links,
            delay_between_posts=True
        )

    def _export_results(self, results: Dict[str, Any]) -> None:
        """Export results to JSON file"""
        import json

        output_file = Path(f"instagram_data_{results['username']}.json")

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Results saved to: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to export results: {e}")


def quick_scrape(username: str, config: Optional[ScraperConfig] = None) -> Dict[str, Any]:
    """
    Quick scrape function for simple use cases

    Args:
        username: Instagram username
        config: Optional configuration

    Returns:
        Complete scraping results

    Example:
        >>> results = quick_scrape('cristiano')
        >>> print(results['profile'])
    """
    orchestrator = InstagramOrchestrator(config)
    return orchestrator.scrape_complete_profile(username)
