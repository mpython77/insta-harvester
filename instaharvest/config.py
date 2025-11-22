"""
Instagram Scraper - Configuration management
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    """Configuration for Instagram scraper"""

    # Session
    session_file: str = 'instagram_session.json'

    # Browser settings
    headless: bool = True  # Chrome runs in headless mode by default
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    # Timeouts (milliseconds)
    default_timeout: int = 60000
    navigation_timeout: int = 60000
    element_timeout: int = 10000

    # Delays (seconds)
    page_load_delay: float = 2.0
    scroll_delay_min: float = 1.5
    scroll_delay_max: float = 2.5
    post_scrape_delay_min: float = 2.0
    post_scrape_delay_max: float = 4.0

    # Action delays - used for button clicks, popups, and interactive elements
    # This ensures Instagram has time to load, especially on slow connections
    sleep_time: float = 2.5  # Base sleep time in seconds
    action_delay_min: float = 2.0  # Minimum random delay before actions
    action_delay_max: float = 3.5  # Maximum random delay before actions

    # Scroll settings
    max_scroll_attempts: int = 1000
    no_new_content_threshold: int = 3

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0

    # Logging
    log_file: Optional[str] = 'instagram_scraper.log'
    log_level: str = 'INFO'
    log_to_console: bool = True

    # Output
    links_file: str = 'post_links.txt'
