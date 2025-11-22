"""
Instagram Scraper - Main Orchestrator
Coordinates all scraping operations in a single workflow
"""

import time
import signal
import sys
import atexit
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import ScraperConfig
from .profile import ProfileScraper, ProfileData
from .post_links import PostLinksScraper
from .post_data import PostDataScraper, PostData
from .reel_links import ReelLinksScraper
from .reel_data import ReelDataScraper, ReelData
from .parallel_scraper import ParallelPostDataScraper
from .excel_export import ExcelExporter
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

        # Graceful shutdown tracking
        self.shutdown_requested = False
        self.excel_exporter = None
        self.current_results = None
        self.current_username = None

        # Register signal handlers for Ctrl+C and SIGTERM
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Register cleanup on exit
        atexit.register(self._cleanup)

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

    def _collect_post_links(self, username: str) -> List[Dict[str, str]]:
        """
        Collect all post/reel links from profile

        Returns:
            List of dictionaries with 'url' and 'type' keys
        """
        scraper = PostLinksScraper(self.config)
        return scraper.scrape(
            username,
            save_to_file=True
        )

    def _collect_reel_links(self, username: str) -> List[str]:
        """
        Collect all REEL links from {username}/reels/ page (SEPARATE from posts)

        Returns:
            List of reel URLs
        """
        scraper = ReelLinksScraper(self.config)
        return scraper.scrape(
            username,
            save_to_file=True
        )

    def _scrape_posts_data(self, post_links: List[Dict[str, str]]) -> List[PostData]:
        """
        Scrape data from all posts

        Args:
            post_links: List of dictionaries with 'url' and 'type' keys
        """
        scraper = PostDataScraper(self.config)
        # Extract URLs from dictionaries
        urls = [link['url'] for link in post_links]
        return scraper.scrape_multiple(
            urls,
            delay_between_posts=True
        )

    def _scrape_reels_data(self, reel_links: List[str]) -> List[ReelData]:
        """
        Scrape data from all REELS (SEPARATE from posts)

        Args:
            reel_links: List of reel URLs
        """
        scraper = ReelDataScraper(self.config)
        return scraper.scrape_multiple(
            reel_links,
            delay_between_reels=True
        )

    def scrape_complete_profile_advanced(
        self,
        username: str,
        parallel: Optional[int] = None,
        save_excel: bool = False,
        export_json: bool = True
    ) -> Dict[str, Any]:
        """
        Advanced complete scraping with parallel processing and Excel export

        Args:
            username: Instagram username
            parallel: Number of parallel contexts (None = sequential, 3 = 3 tabs)
            save_excel: Save to Excel in real-time
            export_json: Export to JSON file

        Returns:
            Dictionary with all scraped data

        Example:
            >>> orchestrator = InstagramOrchestrator()
            >>> results = orchestrator.scrape_complete_profile_advanced(
            ...     'cristiano',
            ...     parallel=3,
            ...     save_excel=True
            ... )
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ADVANCED PROFILE SCRAPE: @{username}")
        self.logger.info(f"Parallel: {parallel if parallel else 'Sequential'}")
        self.logger.info(f"Excel Export: {save_excel}")
        self.logger.info(f"{'='*60}\n")

        results = {
            'username': username,
            'profile': None,
            'post_links': [],
            'reel_links': [],
            'posts_data': [],
            'reels_data': []
        }

        # Track current state for graceful shutdown
        self.current_username = username
        self.current_results = results

        # Initialize Excel exporter if needed
        excel_exporter = None
        if save_excel:
            excel_filename = f"instagram_data_{username}.xlsx"
            excel_exporter = ExcelExporter(excel_filename, self.logger)
            self.excel_exporter = excel_exporter
            self.logger.info(f"Excel exporter initialized: {excel_filename}")

        # STEP 1: Scrape profile stats
        self.logger.info("STEP 1: Scraping profile stats...")
        profile_data = self._scrape_profile_stats(username)
        results['profile'] = profile_data.to_dict()
        self.current_results = results  # Update for graceful shutdown
        self.logger.info(
            f"✓ Profile: {profile_data.posts} posts, "
            f"{profile_data.followers} followers, "
            f"{profile_data.following} following"
        )

        # Check for shutdown request
        if self.shutdown_requested:
            self.logger.warning("Shutdown requested after STEP 1")
            return results

        # STEP 2: Collect post links
        self.logger.info("\nSTEP 2: Collecting post links...")
        post_links = self._collect_post_links(username)
        results['post_links'] = post_links
        self.current_results = results  # Update for graceful shutdown
        self.logger.info(f"✓ Collected {len(post_links)} post links")

        # Check for shutdown request
        if self.shutdown_requested:
            self.logger.warning("Shutdown requested after STEP 2")
            return results

        # STEP 2.5: Collect REEL links (SEPARATE from posts)
        self.logger.info("\nSTEP 2.5: Collecting REEL links from /reels/ page...")
        reel_links = self._collect_reel_links(username)
        results['reel_links'] = reel_links
        self.current_results = results  # Update for graceful shutdown
        self.logger.info(f"✓ Collected {len(reel_links)} reel links")

        # Check for shutdown request
        if self.shutdown_requested:
            self.logger.warning("Shutdown requested after STEP 2.5")
            return results

        # STEP 3: Scrape post data (parallel or sequential)
        if post_links:
            self.logger.info(
                f"\nSTEP 3: Scraping {len(post_links)} posts "
                f"({'parallel=' + str(parallel) if parallel else 'sequential'})..."
            )

            if parallel and parallel > 1:
                # Parallel scraping
                posts_data = self._scrape_posts_parallel(
                    post_links,
                    parallel,
                    excel_exporter
                )
            else:
                # Sequential scraping
                posts_data = self._scrape_posts_sequential(
                    post_links,
                    excel_exporter
                )

            results['posts_data'] = [p.to_dict() for p in posts_data]
            self.logger.info(f"✓ Scraped {len(posts_data)} posts")

        # Check for shutdown request
        if self.shutdown_requested:
            self.logger.warning("Shutdown requested after STEP 3")
            if excel_exporter:
                excel_exporter.finalize()
            return results

        # STEP 3.5: Scrape REEL data (SEPARATE from posts)
        if reel_links:
            self.logger.info(
                f"\nSTEP 3.5: Scraping {len(reel_links)} REELS "
                f"(sequential - reels only)..."
            )

            # Note: Reels are always scraped sequentially using ReelDataScraper
            reels_data = self._scrape_reels_sequential(
                reel_links,
                excel_exporter
            )

            results['reels_data'] = [r.to_dict() for r in reels_data]
            self.logger.info(f"✓ Scraped {len(reels_data)} reels")

        # Finalize Excel
        if excel_exporter:
            excel_exporter.finalize()
            self.logger.info(f"✓ Excel file finalized: {excel_exporter.filename}")

        # Export JSON
        if export_json:
            self.logger.info("\nExporting JSON...")
            self._export_results(results)

        self.logger.info(f"\n{'='*60}")
        self.logger.info("ADVANCED SCRAPING COMPLETE!")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Profile: {results['profile']}")
        self.logger.info(f"Post links: {len(results['post_links'])}")
        self.logger.info(f"Reel links: {len(results['reel_links'])}")
        self.logger.info(f"Posts scraped: {len(results['posts_data'])}")
        self.logger.info(f"Reels scraped: {len(results['reels_data'])}")
        self.logger.info(f"{'='*60}\n")

        return results

    def _scrape_posts_parallel(
        self,
        post_links: List[Dict[str, str]],
        parallel: int,
        excel_exporter: Optional[ExcelExporter] = None
    ) -> List[PostData]:
        """
        Scrape posts in parallel with REAL-TIME Excel writing

        Args:
            post_links: List of dictionaries with 'url' and 'type' keys
            parallel: Number of parallel contexts
            excel_exporter: Optional Excel exporter for real-time save

        Returns:
            List of PostData objects
        """
        self.logger.info(f"🚀 Starting parallel scraping with {parallel} workers...")
        self.logger.info(f"📊 Real-time Excel writing: {'ENABLED' if excel_exporter else 'DISABLED'}")

        scraper = ParallelPostDataScraper(self.config)
        # Pass full link dictionaries (with content_type info)
        posts_data = scraper.scrape_multiple(
            post_links,  # Changed: Now passing full dictionaries!
            parallel=parallel,
            session_file=self.config.session_file,
            excel_exporter=excel_exporter  # Pass to enable real-time writing!
        )

        # NO need to save to Excel here - already done in real-time!
        if excel_exporter:
            self.logger.info("✓ Excel writing completed in real-time")

        return posts_data

    def _scrape_posts_sequential(
        self,
        post_links: List[Dict[str, str]],
        excel_exporter: Optional[ExcelExporter] = None
    ) -> List[PostData]:
        """
        Scrape posts sequentially with real-time Excel export

        Args:
            post_links: List of dictionaries with 'url' and 'type' keys
            excel_exporter: Optional Excel exporter

        Returns:
            List of PostData objects
        """
        posts_data = []

        scraper = PostDataScraper(self.config)
        scraper.load_session()
        scraper.setup_browser(scraper.load_session())

        try:
            for i, link_data in enumerate(post_links, 1):
                # Extract URL from dictionary
                url = link_data['url']
                content_type = link_data.get('type', 'Unknown')

                # Check for shutdown request before each post
                if self.shutdown_requested:
                    self.logger.warning(f"Shutdown requested at post {i}/{len(post_links)}")
                    break

                self.logger.info(f"[{i}/{len(post_links)}] Scraping [{content_type}]: {url}")

                try:
                    data = scraper.scrape(url)
                    posts_data.append(data)

                    # Update current results immediately (for graceful shutdown)
                    if self.current_results is not None:
                        self.current_results['posts_data'] = [p.to_dict() for p in posts_data]

                    # Save to Excel immediately (real-time saving)
                    if excel_exporter:
                        excel_exporter.add_row(
                            post_url=data.url,
                            tagged_accounts=data.tagged_accounts,
                            likes=data.likes,
                            post_date=data.timestamp,
                            content_type=data.content_type
                        )

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    posts_data.append(PostData(
                        url=url,
                        tagged_accounts=[],
                        likes='ERROR',
                        timestamp='N/A'
                    ))

                # Delay
                if i < len(post_links):
                    import random
                    time.sleep(random.uniform(2, 4))

        finally:
            scraper.close()

        return posts_data

    def _scrape_reels_sequential(
        self,
        reel_links: List[str],
        excel_exporter: Optional[ExcelExporter] = None
    ) -> List[ReelData]:
        """
        Scrape REELS sequentially with real-time Excel export (SEPARATE from posts)

        Args:
            reel_links: List of reel URLs
            excel_exporter: Optional Excel exporter

        Returns:
            List of ReelData objects
        """
        reels_data = []

        scraper = ReelDataScraper(self.config)
        scraper.load_session()
        scraper.setup_browser(scraper.load_session())

        try:
            for i, url in enumerate(reel_links, 1):
                # Check for shutdown request before each reel
                if self.shutdown_requested:
                    self.logger.warning(f"Shutdown requested at reel {i}/{len(reel_links)}")
                    break

                self.logger.info(f"[{i}/{len(reel_links)}] Scraping [Reel]: {url}")

                try:
                    data = scraper.scrape(url)
                    reels_data.append(data)

                    # Update current results immediately (for graceful shutdown)
                    if self.current_results is not None:
                        self.current_results['reels_data'] = [r.to_dict() for r in reels_data]

                    # Save to Excel immediately (real-time saving)
                    if excel_exporter:
                        excel_exporter.add_row(
                            post_url=data.url,
                            tagged_accounts=data.tagged_accounts,
                            likes=data.likes,
                            post_date=data.timestamp,
                            content_type='Reel'
                        )

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    reels_data.append(ReelData(
                        url=url,
                        tagged_accounts=[],
                        likes='ERROR',
                        timestamp='N/A',
                        content_type='Reel'
                    ))

                # Delay
                if i < len(reel_links):
                    import random
                    time.sleep(random.uniform(2, 4))

        finally:
            scraper.close()

        return reels_data

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

    def _signal_handler(self, signum, frame):
        """
        Handle Ctrl+C (SIGINT) and SIGTERM gracefully

        This ensures data is saved and browsers are closed properly
        """
        signal_name = 'SIGINT (Ctrl+C)' if signum == signal.SIGINT else 'SIGTERM'

        print("\n")
        self.logger.warning(f"{'='*60}")
        self.logger.warning(f"{signal_name} received - Graceful shutdown initiated")
        self.logger.warning(f"{'='*60}")

        self.shutdown_requested = True

        # Save current progress immediately
        if self.current_results:
            self.logger.info("Saving current progress...")
            try:
                self._export_results(self.current_results)
                self.logger.info("✓ Progress saved successfully")
            except Exception as e:
                self.logger.error(f"Failed to save progress: {e}")

        # Finalize Excel if exists
        if self.excel_exporter:
            try:
                self.excel_exporter.finalize()
                self.logger.info(f"✓ Excel finalized: {self.excel_exporter.filename}")
            except Exception as e:
                self.logger.error(f"Failed to finalize Excel: {e}")

        self.logger.warning("Shutdown complete. Exiting...")
        sys.exit(0)

    def _cleanup(self):
        """
        Cleanup function called on program exit (atexit)

        Ensures all resources are properly released
        """
        if self.excel_exporter:
            try:
                self.excel_exporter.finalize()
            except Exception:
                pass


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
