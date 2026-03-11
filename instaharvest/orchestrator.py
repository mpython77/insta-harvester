"""
Instagram Scraper - Main Orchestrator
Coordinates all scraping operations in a single workflow
"""

import time
import signal
import sys
import atexit
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import ScraperConfig
from .profile import ProfileScraper, ProfileData
from .post_links import PostLinksScraper
from .post_data import PostDataScraper, PostData, PostLocation, PostOwner, CarouselSlide
from .reel_links import ReelLinksScraper
from .reel_data import ReelDataScraper, ReelData
from .parallel_scraper import ParallelPostDataScraper
from .tagged_posts import TaggedPostsScraper, TaggedPostData, TaggedPostsResult
from .highlight_scraper import HighlightsScraper, HighlightResult, HighlightsListResult
from .comment_scraper import CommentScraper, PostCommentsData
from .models import CommentData
from .exporters import CommentsExporter, export_comments_to_json, export_comments_to_excel, ExcelExporter
from .logging_config import get_logger
from .interactions import InteractionManager
from .story_scraper import StoryScraper, StoryResult, StorySlideInfo
from .shared_browser import SharedBrowser


class InstagramOrchestrator:
    """
    Main orchestrator for complete Instagram scraping workflow

    Workflow (COMPLETE SEPARATION OF POSTS AND REELS):
    1. Scrape profile stats (posts, followers, following)
    2. Collect POST links from main profile (POSTS ONLY)
    3. Collect REEL links from /reels/ page (REELS ONLY - SEPARATE!)
    4. Scrape data from posts (tags, likes, timestamp)
    5. Scrape data from reels (tags, likes, timestamp - SEPARATE!)
    6. (Optional) Scrape comments with full data (text, likes, replies, author info)
    7. (Optional) Scrape stories with tag extraction (JSON-first architecture)
    8. (Optional) Scrape tagged posts — who tags this account
    9. (Optional) Scrape highlights — full slide data with stickers

    Features:
    - Complete end-to-end scraping
    - Separate handling of posts and reels (no mixing!)
    - Full comment scraping with replies
    - Story scraping with per-slide tag mapping
    - Progress tracking
    - Error resilience
    - Real-time data export (JSON + Excel)
    - Data export with Type column (Post/Reel)
    """

    def __init__(self, config: Optional[ScraperConfig] = None, shared_browser: Optional[SharedBrowser] = None):
        """
        Initialize orchestrator

        Args:
            config: Scraper configuration
            shared_browser: Optional SharedBrowser instance for reusing a single browser
        """
        self.config = config or ScraperConfig()
        self.logger = get_logger("InstagramOrchestrator")
        self.shared_browser = shared_browser

        # Graceful shutdown tracking
        self.shutdown_requested = False
        self.excel_exporter = None
        self.current_results = None
        self.current_username = None

        # Signal handling delegated to individual components
        # signal.signal(signal.SIGINT, self._signal_handler)
        # signal.signal(signal.SIGTERM, self._signal_handler)

        # Register cleanup on exit
        atexit.register(self._cleanup)

        mode = "SharedBrowser" if shared_browser else "Standalone"
        self.logger.info("=" * 60)
        self.logger.info(f"Instagram Scraper Orchestrator Initialized ({mode})")
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

            # Step 3.5: Calculate Engagement Rate
            if posts_data and profile_data.followers > 0:
                try:
                    likes_values = []
                    for p in posts_data:
                        try:
                            likes_val = int(str(p.likes).replace(',', '').replace('.', ''))
                            likes_values.append(likes_val)
                        except (ValueError, TypeError):
                            pass
                    if likes_values:
                        avg_likes = sum(likes_values) / len(likes_values)
                        er = profile_data.calculate_engagement_rate(avg_likes)
                        results['profile'] = profile_data.to_dict()
                        self.logger.info(f"📊 Engagement Rate: {er}% (avg {avg_likes:.0f} likes / {profile_data.followers} followers)")
                except Exception as e:
                    self.logger.debug(f"Engagement rate calculation error: {e}")

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
        if profile_data.engagement_rate is not None:
            self.logger.info(f"Engagement Rate: {profile_data.engagement_rate}%")
        self.logger.info(f"{'='*60}\n")

        return results

    def _scrape_profile_stats(self, username: str) -> ProfileData:
        """Scrape profile statistics"""
        scraper = ProfileScraper(self.config)
        return scraper.scrape(username)

    def _collect_post_links(self, username: str) -> List[Dict[str, str]]:
        """
        Collect all POST links from main profile (POSTS ONLY - NO REELS!)

        Returns:
            List of dictionaries with 'url' and 'type' keys (all type='Post')

        NOTE: Reels are collected separately by _collect_reel_links()
        """
        scraper = PostLinksScraper(self.config)
        results = scraper.scrape(
            username,
            save_to_file=True
        )
        if scraper.interrupted:
             self.logger.warning("⚠️ Scraping interrupted during post link collection")
             self.shutdown_requested = True
        return results

    def _collect_reel_links(self, username: str) -> List[str]:
        """
        Collect all REEL links from {username}/reels/ page (SEPARATE from posts)

        Returns:
            List of reel URLs
        """
        scraper = ReelLinksScraper(self.config)
        results = scraper.scrape(
            username,
            save_to_file=True
        )
        if scraper.interrupted:
             self.logger.warning("⚠️ Scraping interrupted during reel link collection")
             self.shutdown_requested = True
        return results

    def _scrape_posts_data(self, post_links: List[Dict[str, str]]) -> List[PostData]:
        """
        Scrape data from all posts

        Args:
            post_links: List of dictionaries with 'url' and 'type' keys
        """
        urls = [link['url'] for link in post_links]
        if self.shared_browser:
            return self.shared_browser.post_data_scraper.scrape_multiple(
                urls, delay_between_posts=True
            )
        scraper = PostDataScraper(self.config)
        return scraper.scrape_multiple(
            urls, delay_between_posts=True
        )

    def _scrape_reels_data(self, reel_links: List[str]) -> List[ReelData]:
        """
        Scrape data from all REELS (SEPARATE from posts)

        Args:
            reel_links: List of reel URLs
        """
        if self.shared_browser:
            return self.shared_browser.reel_data_scraper.scrape_multiple(
                reel_links, delay_between_reels=True
            )
        scraper = ReelDataScraper(self.config)
        return scraper.scrape_multiple(
            reel_links, delay_between_reels=True
        )

    def scrape_complete_profile_advanced(
        self,
        username: str,
        parallel: Optional[int] = None,
        save_excel: bool = False,
        export_json: bool = True,
        scrape_comments: bool = False,
        max_comments_per_post: Optional[int] = None,
        include_replies: bool = True,
        scrape_stories: bool = False,
        story_challenge_delay: int = 10
    ) -> Dict[str, Any]:
        """
        Advanced complete scraping with parallel processing and Excel export

        Args:
            username: Instagram username
            parallel: Number of parallel contexts (None = sequential, 3 = 3 tabs)
            save_excel: Save to Excel in real-time
            export_json: Export to JSON file
            scrape_comments: Enable full comment scraping
            max_comments_per_post: Max comments per post (None = all)
            include_replies: Include replies in comment scraping
            scrape_stories: Enable story scraping with tag extraction
            story_challenge_delay: Seconds to wait for challenge solving (default: 10)

        Returns:
            Dictionary with all scraped data

        Example:
            >>> orchestrator = InstagramOrchestrator()
            >>> results = orchestrator.scrape_complete_profile_advanced(
            ...     'cristiano',
            ...     parallel=3,
            ...     save_excel=True,
            ...     scrape_comments=True,
            ...     scrape_stories=True,
            ...     max_comments_per_post=100
            ... )
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ADVANCED PROFILE SCRAPE: @{username}")
        self.logger.info(f"Parallel: {parallel if parallel else 'Sequential'}")
        self.logger.info(f"Excel Export: {save_excel}")
        self.logger.info(f"Comment Scraping: {scrape_comments}")
        self.logger.info(f"Story Scraping: {scrape_stories}")
        self.logger.info(f"{'='*60}\n")

        results = {
            'username': username,
            'profile': None,
            'post_links': [],
            'reel_links': [],
            'posts_data': [],
            'reels_data': [],
            'comments_data': [],
            'story_data': None  # Story scraping result
        }

        # Track current state for graceful shutdown
        self.current_username = username
        self.current_results = results

        # Initialize Excel exporter if needed
        excel_exporter = None
        if save_excel:
            # Construct Excel path using base_output_dir
            if self.config.base_output_dir:
                base_dir = Path(self.config.base_output_dir)
                base_dir.mkdir(parents=True, exist_ok=True)
                excel_filename = str(base_dir / self.config.excel_filename_pattern.format(username=username))
            else:
                 excel_filename = self.config.excel_filename_pattern.format(username=username)

            excel_exporter = ExcelExporter(excel_filename, self.logger, self.config)
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

        # STEP 3.5: Scrape REEL data (SEPARATE from posts) - NOW WITH PARALLEL!
        if reel_links:
            self.logger.info(
                f"\nSTEP 3.5: Scraping {len(reel_links)} REELS "
                f"({'parallel=' + str(parallel) if parallel and parallel > 1 else 'sequential'})..."
            )

            if parallel and parallel > 1:
                # Parallel scraping for reels (NEW!)
                reels_data = self._scrape_reels_parallel(
                    reel_links,
                    parallel,
                    excel_exporter
                )
            else:
                # Sequential scraping for reels
                reels_data = self._scrape_reels_sequential(
                    reel_links,
                    excel_exporter
                )

            results['reels_data'] = [r.to_dict() for r in reels_data]
            self.logger.info(f"✓ Scraped {len(reels_data)} reels")

        # Check for shutdown request
        if self.shutdown_requested:
            self.logger.warning("Shutdown requested after STEP 3.5")
            if excel_exporter:
                excel_exporter.finalize()
            return results

        # STEP 4: Scrape comments (if enabled)
        comments_exporter = None
        if scrape_comments and post_links:
            self.logger.info(
                f"\nSTEP 4: Scraping comments from {len(post_links)} posts..."
            )
            self.logger.info(f"Max comments per post: {max_comments_per_post or 'All'}")
            self.logger.info(f"Include replies: {include_replies}")

            # Initialize comments exporter
            if save_excel:
                comments_exporter = CommentsExporter(
                    username=username,
                    logger=self.logger,
                    config=self.config,
                    export_json=export_json,
                    export_excel=True
                )

            # Scrape comments from all posts
            comments_data = self._scrape_comments(
                post_links=[link['url'] for link in post_links],
                max_comments_per_post=max_comments_per_post,
                include_replies=include_replies,
                comments_exporter=comments_exporter
            )

            results['comments_data'] = [c.to_dict() for c in comments_data]
            self.current_results = results

            # Calculate totals
            total_comments = sum(c.total_comments_scraped for c in comments_data)
            total_replies = sum(c.total_replies_scraped for c in comments_data)
            self.logger.info(f"✓ Scraped {total_comments} comments, {total_replies} replies")

            # Finalize comments exporter
            if comments_exporter:
                comments_exporter.finalize()

        # STEP 5: Scrape stories (if enabled)
        if scrape_stories:
            self.logger.info(f"\nSTEP 5: Scraping stories for @{username}...")
            try:
                story_result = self._scrape_stories(
                    username,
                    challenge_delay=story_challenge_delay
                )
                results['story_data'] = story_result.to_dict()
                self.current_results = results

                if story_result.has_stories:
                    self.logger.info(
                        f"✅ Stories: {story_result.story_count} slides, "
                        f"{len(story_result.all_tagged_accounts)} tags"
                    )
                    if story_result.all_tagged_accounts:
                        self.logger.info(f"   Tags: {story_result.all_tagged_accounts}")
                    if story_result.slides:
                        tagged_slides = [s for s in story_result.slides if s.has_tags]
                        self.logger.info(
                            f"   {len(story_result.slides)} slide, "
                            f"{len(tagged_slides)} tasida tag bor"
                        )
                else:
                    self.logger.info(f"ℹ️ @{username} has no active stories")

            except Exception as e:
                self.logger.error(f"Story scraping failed: {e}")
                results['story_data'] = {'error': str(e), 'has_stories': False}

        # Finalize Excel
        if excel_exporter:
            excel_exporter.finalize()
            self.logger.info(f"✓ Excel file finalized: {excel_exporter.filename}")

        # Export JSON
        if export_json:
            self.logger.info("\nExporting JSON...")
            self._export_results(results)

        # Calculate comment stats for summary
        total_comments_scraped = 0
        total_replies_scraped = 0
        if results.get('comments_data'):
            total_comments_scraped = sum(c.get('total_comments_scraped', 0) for c in results['comments_data'])
            total_replies_scraped = sum(c.get('total_replies_scraped', 0) for c in results['comments_data'])

        self.logger.info(f"\n{'='*60}")
        self.logger.info("ADVANCED SCRAPING COMPLETE!")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Profile: {results['profile']}")
        self.logger.info(f"Post links: {len(results['post_links'])}")
        self.logger.info(f"Reel links: {len(results['reel_links'])}")
        self.logger.info(f"Posts scraped: {len(results['posts_data'])}")
        self.logger.info(f"Reels scraped: {len(results['reels_data'])}")
        if scrape_comments:
            self.logger.info(f"Comments scraped: {total_comments_scraped}")
            self.logger.info(f"Replies scraped: {total_replies_scraped}")
        if scrape_stories and results.get('story_data'):
            story_d = results['story_data']
            self.logger.info(f"Story slides: {story_d.get('story_count', 0)}")
            self.logger.info(f"Story tags: {story_d.get('all_tagged_accounts', [])}")
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
        if self.shared_browser:
            scraper.page = self.shared_browser.page
            scraper.browser = self.shared_browser.browser
            scraper.context = self.shared_browser.context
        posts_data = scraper.scrape_multiple(
            post_links,
            parallel=parallel,
            session_file=self.config.session_file,
            excel_exporter=excel_exporter
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

        if self.shared_browser:
            scraper = self.shared_browser.post_data_scraper
        else:
            scraper = PostDataScraper(self.config)
            session_data = scraper.load_session()
            scraper.setup_browser(session_data)

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
                        timestamp='N/A',
                        content_type=content_type  # Use detected type from link_data
                    ))
                except KeyboardInterrupt:  # [NEW]
                    self.logger.warning("\n⚠️ Interrupted by user during post scraping!")
                    self.shutdown_requested = True
                    break

                # Delay
                if i < len(post_links):
                    import random
                    time.sleep(random.uniform(self.config.batch_operation_delay_min, self.config.batch_operation_delay_max))

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
        session_data = scraper.load_session()
        scraper.setup_browser(session_data)

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
                except KeyboardInterrupt:  # [NEW]
                    self.logger.warning("\n⚠️ Interrupted by user during reel scraping!")
                    self.shutdown_requested = True
                    break

                # Delay
                if i < len(reel_links):
                    import random
                    time.sleep(random.uniform(self.config.batch_operation_delay_min, self.config.batch_operation_delay_max))

        finally:
            scraper.close()

        return reels_data

    def _scrape_reels_parallel(
        self,
        reel_links: List[str],
        parallel: int,
        excel_exporter: Optional[ExcelExporter] = None
    ) -> List[ReelData]:
        """
        Scrape REELS in parallel with REAL-TIME Excel writing (NEW!)

        Args:
            reel_links: List of reel URLs
            parallel: Number of parallel contexts
            excel_exporter: Optional Excel exporter for real-time save

        Returns:
            List of ReelData objects
        """
        self.logger.info(f"🚀 Starting parallel scraping for REELS with {parallel} workers...")
        self.logger.info(f"📊 Real-time Excel writing: {'ENABLED' if excel_exporter else 'DISABLED'}")

        # Convert reel URLs to dict format (required by ParallelPostDataScraper)
        reel_links_dict = [{'url': url, 'type': 'Reel'} for url in reel_links]

        # Use ParallelPostDataScraper (it handles both posts and reels!)
        scraper = ParallelPostDataScraper(self.config)
        if self.shared_browser:
            scraper.page = self.shared_browser.page
            scraper.browser = self.shared_browser.browser
            scraper.context = self.shared_browser.context
        results = scraper.scrape_multiple(
            reel_links_dict,
            parallel=parallel,
            session_file=self.config.session_file,
            excel_exporter=excel_exporter
        )

        # Convert PostData to ReelData (they have same structure)
        reels_data = []
        for post_data in results:
            reel_data = ReelData(
                url=post_data.url,
                tagged_accounts=post_data.tagged_accounts,
                likes=post_data.likes,
                timestamp=post_data.timestamp,
                content_type='Reel'
            )
            reels_data.append(reel_data)

        if excel_exporter:
            self.logger.info("Excel writing completed in real-time")

        return reels_data

    def _scrape_comments(
        self,
        post_links: List[str],
        max_comments_per_post: Optional[int],
        include_replies: bool,
        comments_exporter: Optional[CommentsExporter] = None
    ) -> List[PostCommentsData]:
        """
        Scrape comments from multiple posts

        Args:
            post_links: List of post URLs
            max_comments_per_post: Max comments per post (None = all)
            include_replies: Include replies
            comments_exporter: Optional exporter for real-time export

        Returns:
            List of PostCommentsData objects
        """
        comments_data = []

        scraper = CommentScraper(self.config)
        session_data = scraper.load_session()
        scraper.setup_browser(session_data)

        try:
            for i, url in enumerate(post_links, 1):
                # Check for shutdown request
                if self.shutdown_requested:
                    self.logger.warning(f"Shutdown requested at comment scraping {i}/{len(post_links)}")
                    break

                self.logger.info(f"[{i}/{len(post_links)}] Scraping comments: {url}")

                try:
                    post_comments = scraper.scrape(
                        url,
                        target_count=max_comments_per_post,
                        include_replies=include_replies
                    )
                    comments_data.append(post_comments)

                    # Real-time export
                    if comments_exporter:
                        comments_exporter.add_post_comments(post_comments)

                    self.logger.info(
                        f"   {post_comments.total_comments_scraped} comments, "
                        f"{post_comments.total_replies_scraped} replies"
                    )

                except Exception as e:
                    self.logger.error(f"Failed to scrape comments from {url}: {e}")
                    # Add empty result
                    comments_data.append(PostCommentsData(
                        post_url=url,
                        post_id=scraper._extract_post_id(url),
                        total_comments_scraped=0,
                        total_replies_scraped=0,
                        comments=[]
                    ))

                # Delay between posts
                if i < len(post_links):
                    delay = random.uniform(
                        self.config.comment_post_delay_min,
                        self.config.comment_post_delay_max
                    )
                    time.sleep(delay)

        finally:
            scraper.close()

        return comments_data

    def scrape_comments_only(
        self,
        username: str,
        post_urls: Optional[List[str]] = None,
        max_comments_per_post: Optional[int] = None,
        include_replies: bool = True,
        save_excel: bool = True,
        export_json: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape only comments from posts (standalone method)

        Use this when you already have post URLs or want to scrape just comments

        Args:
            username: Instagram username (for file naming)
            post_urls: List of post URLs (if None, will collect from profile)
            max_comments_per_post: Max comments per post
            include_replies: Include replies
            save_excel: Save to Excel
            export_json: Export to JSON

        Returns:
            Dictionary with comments data
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"COMMENT SCRAPING: @{username}")
        self.logger.info(f"{'='*60}\n")

        # If no post URLs provided, collect them first
        if not post_urls:
            self.logger.info("Collecting post links first...")
            post_links = self._collect_post_links(username)
            post_urls = [link['url'] for link in post_links]
            self.logger.info(f"Collected {len(post_urls)} post URLs")

        # Initialize exporter
        comments_exporter = None
        if save_excel or export_json:
            comments_exporter = CommentsExporter(
                username=username,
                logger=self.logger,
                config=self.config,
                export_json=export_json,
                export_excel=save_excel
            )

        # Scrape comments
        comments_data = self._scrape_comments(
            post_links=post_urls,
            max_comments_per_post=max_comments_per_post,
            include_replies=include_replies,
            comments_exporter=comments_exporter
        )
        
        return comments_data

    def interact_with_post(
        self,
        url: str,
        like: bool = False,
        comment: Optional[str] = None
    ) -> bool:
        """
        Interact with a single post/reel (Like/Comment)
        """
        self.logger.info(f"❤️/💬 Interacting with: {url}")
        
        if self.shared_browser:
            scraper = self.shared_browser.post_data_scraper
            need_close = False
        else:
            scraper = PostDataScraper(self.config)
            session_data = scraper.load_session()
            scraper.setup_browser(session_data)
            need_close = True
        
        try:
            interaction = InteractionManager(scraper.page, self.logger, self.config)
            scraper.goto_url(url)
            time.sleep(3)
            
            success = True
            if like:
                if not interaction.like_post():
                    success = False
            
            if comment:
                if not interaction.comment_post(comment):
                    success = False
                    
            return success
        finally:
            if need_close:
                scraper.close()

    def run_reels_interaction_flow(
        self,
        duration_minutes: int = 10,
        like_probability: float = 0.5,
        comments: Optional[List[str]] = None
    ):
        """
        Watch Reels, scroll automatically, and randomly like/comment.
        """
        self.logger.info(f"🎬 Starting Reels Interaction Flow ({duration_minutes}m)...")
        
        scraper = ReelDataScraper(self.config)
        session_data = scraper.load_session()
        scraper.setup_browser(session_data)
        
        try:
            interaction = InteractionManager(scraper.page, self.logger, self.config)
            
            # Go to Reels feed
            scraper.goto_url("https://www.instagram.com/reels/")
            time.sleep(5)
            
            start_time = time.time()
            reels_cnt = 0
            
            while (time.time() - start_time) < (duration_minutes * 60):
                reels_cnt += 1
                self.logger.info(f"📺 Watching Reel #{reels_cnt}")
                
                # Watch for random duration
                watch_time = random.uniform(5, 15)
                time.sleep(watch_time)
                
                # Random Like
                if random.random() < like_probability:
                    interaction.like_reel()
                    
                # Random Comment (if enabled)
                if comments and random.random() < 0.1: # 10% chance if comments provided
                    text = random.choice(comments)
                    interaction.comment_reel(text)
                
                # Next Reel
                interaction.next_reel()
                
        finally:
            scraper.close()

        # Finalize exporter
        if comments_exporter:
            comments_exporter.finalize()

        # Build results
        results = {
            'username': username,
            'total_posts': len(post_urls),
            'total_comments': sum(c.total_comments_scraped for c in comments_data),
            'total_replies': sum(c.total_replies_scraped for c in comments_data),
            'comments_data': [c.to_dict() for c in comments_data]
        }

        self.logger.info(f"\n{'='*60}")
        self.logger.info("COMMENT SCRAPING COMPLETE!")
        self.logger.info(f"Posts processed: {len(post_urls)}")
        self.logger.info(f"Total comments: {results['total_comments']}")
        self.logger.info(f"Total replies: {results['total_replies']}")
        self.logger.info(f"{'='*60}\n")

        return results

    def _export_results(self, results: Dict[str, Any]) -> None:
        """Export results to JSON file"""
        import json

        json_filename = self.config.json_filename_pattern.format(username=results['username'])
        if self.config.base_output_dir:
            base_dir = Path(self.config.base_output_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
            output_file = base_dir / json_filename
        else:
            output_file = Path(json_filename)

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

    # ───────────────────────────────────────────────────────────
    # Story Scraping
    # ───────────────────────────────────────────────────────────

    def _scrape_stories(
        self,
        username: str,
        challenge_delay: int = 10
    ) -> StoryResult:
        """
        Internal: Scrape stories for a user.

        Uses JSON-first architecture for tag extraction.
        Returns StoryResult with per-slide tag mapping.
        """
        if self.shared_browser:
            return self.shared_browser.story_scraper.scrape(
                username,
                extract_tags=True,
                challenge_delay=challenge_delay
            )
        scraper = StoryScraper(self.config)
        return scraper.scrape(
            username,
            extract_tags=True,
            challenge_delay=challenge_delay
        )

    def scrape_stories_only(
        self,
        username: str,
        challenge_delay: int = 10,
        export_json: bool = True
    ) -> Dict[str, Any]:
        """
        Standalone story scraping with full tag extraction.

        Uses JSON-first architecture to extract ALL tagged accounts
        from ALL story slides in a single page load.

        Args:
            username: Instagram username
            challenge_delay: Seconds to wait for challenge solving (default: 10)
            export_json: Export results to JSON file

        Returns:
            Dictionary with story data including per-slide tag mapping

        Example:
            >>> orchestrator = InstagramOrchestrator(config)
            >>> result = orchestrator.scrape_stories_only('username')
            >>> print(result['all_tagged_accounts'])
            >>> for slide in result['slides']:
            ...     print(f"Slide {slide['slide_index']}: {slide['tagged_accounts']}")
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📸 STORY SCRAPING: @{username}")
        self.logger.info(f"{'='*60}\n")

        try:
            story_result = self._scrape_stories(
                username,
                challenge_delay=challenge_delay
            )
            results = story_result.to_dict()

            # Summary
            self.logger.info(f"\n{'='*60}")
            self.logger.info("STORY SCRAPING COMPLETE!")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Has stories: {story_result.has_stories}")
            self.logger.info(f"Story count: {story_result.story_count}")
            self.logger.info(f"Tagged accounts: {story_result.all_tagged_accounts}")

            if story_result.slides:
                tagged = [s for s in story_result.slides if s.has_tags]
                self.logger.info(f"Slides with tags: {len(tagged)}/{len(story_result.slides)}")
                for s in story_result.slides:
                    tag_str = ', '.join(s.tagged_accounts) if s.tagged_accounts else '(no tags)'
                    self.logger.info(
                        f"  Slide {s.slide_index + 1}: [{s.media_type}] "
                        f"{s.timestamp} → {tag_str}"
                    )

            self.logger.info(f"{'='*60}\n")

            # Export
            if export_json:
                import json
                filename = f"story_tags_{username}.json"
                if self.config.base_output_dir:
                    base_dir = Path(self.config.base_output_dir)
                    base_dir.mkdir(parents=True, exist_ok=True)
                    filepath = base_dir / filename
                else:
                    filepath = Path(filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                self.logger.info(f"📁 Results saved: {filepath}")

            return results

        except Exception as e:
            self.logger.error(f"Story scraping failed: {e}")
            return {'username': username, 'error': str(e), 'has_stories': False}

    def scrape_tagged_posts(
        self,
        username: str,
        max_posts: int = 50,
        scroll_pause: float = 2.0,
        max_scrolls: int = 20
    ) -> TaggedPostsResult:
        """
        Scrape posts where a user has been tagged by others.

        Uses JSON-First architecture + DOM extraction.
        Automatically scrolls to collect more posts.

        Args:
            username: Instagram username (without @)
            max_posts: Maximum posts to collect
            scroll_pause: Delay between scrolls
            max_scrolls: Maximum scroll attempts

        Returns:
            TaggedPostsResult with tagged posts and tagger info

        Example:
            >>> orch = InstagramOrchestrator()
            >>> result = orch.scrape_tagged_posts("mondayswimwear", max_posts=100)
            >>> for post in result.tagged_posts:
            ...     print(f"{post.owner.username} tagged you")
        """
        self.logger.info(f"🏷️ Starting tagged posts scrape for @{username}")

        try:
            scraper = TaggedPostsScraper(config=self.config)
            session_data = scraper.load_session()
            scraper.setup_browser(session_data)

            result = scraper.scrape(
                username,
                max_posts=max_posts,
                scroll_pause=scroll_pause,
                max_scrolls=max_scrolls
            )

            scraper.close()

            self.logger.info(
                f"✅ Tagged posts complete: {result.total_found} posts, "
                f"{len(result.unique_taggers)} unique taggers"
            )
            return result

        except Exception as e:
            self.logger.error(f"Tagged posts scraping failed: {e}")
            return TaggedPostsResult(username=username)

    def scrape_highlight(
        self,
        highlight_id: str,
        max_slides: int = 500,
        challenge_delay: int = 5
    ) -> HighlightResult:
        """
        Scrape all slides from an Instagram highlight.

        Args:
            highlight_id: Highlight ID or full URL
            max_slides: Maximum slides to collect
            challenge_delay: Seconds to wait after page load

        Returns:
            HighlightResult with all slides, stickers, music, etc.

        Example:
            >>> orch = InstagramOrchestrator()
            >>> result = orch.scrape_highlight("18092082532805201")
            >>> for slide in result.slides:
            ...     print(f"Slide {slide.slide_index}: {slide.mentions}")
        """
        self.logger.info(f"🌟 Starting highlight scrape: {highlight_id}")

        try:
            scraper = HighlightsScraper(config=self.config)
            session_data = scraper.load_session()
            scraper.setup_browser(session_data)

            result = scraper.scrape(
                highlight_id,
                max_slides=max_slides,
                challenge_delay=challenge_delay
            )

            scraper.close()

            self.logger.info(
                f"✅ Highlight complete: {result.slide_count} slides, "
                f"{len(result.all_mentions)} mentions"
            )
            return result

        except Exception as e:
            self.logger.error(f"Highlight scraping failed: {e}")
            return HighlightResult(highlight_id=highlight_id)

    def scrape_all_highlights(
        self,
        username: str,
        max_slides_per: int = 200,
        challenge_delay: int = 5,
        delay_between: float = 3.0
    ) -> HighlightsListResult:
        """
        List and scrape ALL highlights for a user.

        Args:
            username: Instagram username
            max_slides_per: Maximum slides per highlight
            challenge_delay: Seconds to wait after page load
            delay_between: Seconds between highlights

        Returns:
            HighlightsListResult with all highlights

        Example:
            >>> orch = InstagramOrchestrator()
            >>> result = orch.scrape_all_highlights("mondayswimwear")
            >>> print(f"{result.total_highlights} highlights, {result.total_slides} slides")
        """
        self.logger.info(f"🚀 Scraping all highlights for @{username}")

        try:
            scraper = HighlightsScraper(config=self.config)
            session_data = scraper.load_session()
            scraper.setup_browser(session_data)

            result = scraper.scrape_all(
                username,
                max_slides_per=max_slides_per,
                challenge_delay=challenge_delay,
                delay_between=delay_between
            )

            scraper.close()
            return result

        except Exception as e:
            self.logger.error(f"All highlights scraping failed: {e}")
            return HighlightsListResult(username=username)


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
