"""
Instagram Scraper - Configuration management
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    """
    Configuration for Instagram scraper

    All timing values are in seconds and can be customized based on:
    - Internet connection speed (slower = increase delays)
    - Instagram rate limiting (increase delays to avoid blocks)
    - System performance

    Example:
        >>> from instaharvest.config import ScraperConfig
        >>> # For slow internet
        >>> config = ScraperConfig(
        ...     page_load_delay=5.0,
        ...     button_click_delay=3.0,
        ...     popup_animation_delay=4.0
        ... )
        >>> # For fast internet
        >>> config = ScraperConfig(
        ...     page_load_delay=1.0,
        ...     button_click_delay=1.5,
        ...     popup_animation_delay=2.0
        ... )
    """

    # ==================== SESSION ====================
    session_file: str = 'instagram_session.json'

    # ==================== BROWSER SETTINGS ====================
    headless: bool = True  # Run Chrome in headless mode (no visible window)
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    # ==================== TIMEOUTS (milliseconds) ====================
    default_timeout: int = 60000
    navigation_timeout: int = 60000
    element_timeout: int = 10000

    # ==================== PAGE NAVIGATION DELAYS ====================
    page_load_delay: float = 2.0  # Wait after page loads
    page_stability_delay: float = 2.0  # Wait for page to stabilize after load
    profile_load_delay: float = 2.0  # Wait after loading profile page

    # ==================== BUTTON & CLICK DELAYS ====================
    button_click_delay: float = 2.5  # Wait after clicking any button
    action_delay_min: float = 2.0  # Min random delay before button clicks
    action_delay_max: float = 3.5  # Max random delay before button clicks

    # ==================== POPUP & DIALOG DELAYS ====================
    popup_open_delay: float = 2.5  # Wait for popup/dialog to open
    popup_animation_delay: float = 1.5  # Wait for popup animation to complete
    popup_content_load_delay: float = 0.5  # Wait for popup content to load
    popup_close_delay: float = 0.5  # Wait for popup to close

    # ==================== SCROLL DELAYS ====================
    scroll_delay_min: float = 1.5  # Min delay between scrolls
    scroll_delay_max: float = 2.5  # Max delay between scrolls
    scroll_post_delay: float = 0.5  # Wait after individual scroll
    scroll_content_load_delay: float = 0.8  # Wait for content after scroll
    scroll_lazy_load_delay: float = 1.5  # Wait for lazy-loaded content

    # ==================== INPUT & TYPING DELAYS ====================
    input_focus_delay: float = 0.5  # Wait after clicking input field
    input_before_type_delay_min: float = 1.0  # Min delay before typing
    input_before_type_delay_max: float = 1.5  # Max delay before typing
    input_after_type_delay_min: float = 0.5  # Min delay after typing
    input_after_type_delay_max: float = 1.0  # Max delay after typing

    # ==================== POST/REEL SCRAPING DELAYS ====================
    post_open_delay: float = 3.0  # Wait after opening post
    post_scrape_delay_min: float = 2.0  # Min delay when scraping post data
    post_scrape_delay_max: float = 4.0  # Max delay when scraping post data
    post_navigation_delay: float = 1.5  # Wait when navigating between posts

    reel_open_delay: float = 3.0  # Wait after opening reel
    reel_scrape_delay_min: float = 2.0  # Min delay when scraping reel data
    reel_scrape_delay_max: float = 4.0  # Max delay when scraping reel data

    # ==================== RATE LIMITING DELAYS ====================
    # These delays help avoid Instagram rate limiting and blocks
    follow_delay_min: float = 2.0  # Min delay after follow/unfollow
    follow_delay_max: float = 4.0  # Max delay after follow/unfollow
    message_delay_min: float = 3.0  # Min delay after sending message
    message_delay_max: float = 5.0  # Max delay after sending message
    batch_operation_delay_min: float = 2.0  # Min delay between batch operations
    batch_operation_delay_max: float = 4.0  # Max delay between batch operations

    # ==================== RETRY DELAYS ====================
    retry_delay: float = 2.0  # Delay before retry on failure
    error_recovery_delay_min: float = 1.0  # Min delay for error recovery
    error_recovery_delay_max: float = 2.0  # Max delay for error recovery

    # ==================== UI STABILITY DELAYS ====================
    ui_animation_delay: float = 1.5  # Wait for UI animations
    ui_stability_delay: float = 1.0  # Wait for UI to stabilize
    ui_micro_delay: float = 0.3  # Tiny delay for UI updates
    ui_mini_delay: float = 0.5  # Small delay for quick UI changes
    ui_element_load_delay: float = 0.1  # Very small delay for element loading

    # ==================== SCROLL SETTINGS ====================
    max_scroll_attempts: int = 1000
    no_new_content_threshold: int = 3

    # ==================== RETRY SETTINGS ====================
    max_retries: int = 3

    # ==================== LOGGING ====================
    log_file: Optional[str] = 'instagram_scraper.log'
    log_level: str = 'INFO'
    log_to_console: bool = True

    # ==================== OUTPUT ====================
    links_file: str = 'post_links.txt'

    # ==================== DEPRECATED (kept for backwards compatibility) ====================
    # Use specific delays above instead
    sleep_time: float = 2.5  # Deprecated: use button_click_delay instead
