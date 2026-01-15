"""
Instagram Scraper - Configuration management
Centralized configuration for all hardcoded values
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


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
    viewport_width: int = 1280  # Browser window width (smaller for better fit)
    viewport_height: int = 720   # Browser window height (smaller for better fit)
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    browser_channel: str = 'chrome'  # Browser channel: 'chrome' (system) or 'chromium' (bundled)
    browser_args: List[str] = field(default_factory=lambda: ['--start-maximized'])  # Browser launch arguments
    
    # ==================== SECURITY & ANTI-BAN ====================
    proxies: List[str] = field(default_factory=list)  # List of proxy URLs
    rotate_user_agent: bool = True  # Enable User-Agent rotation
    user_agents: List[str] = field(default_factory=list)  # Custom User-Agents (overrides default)

    # ==================== INSTAGRAM URLS ====================
    instagram_base_url: str = 'https://www.instagram.com/'
    profile_url_pattern: str = 'https://www.instagram.com/{username}/'  # {username} will be replaced
    reels_url_pattern: str = 'https://www.instagram.com/{username}/reels/'  # {username} will be replaced

    # ==================== TIMEOUTS (milliseconds) ====================
    default_timeout: int = 60000
    navigation_timeout: int = 60000
    element_timeout: int = 10000
    session_activation_timeout: int = 30000  # Timeout for session activation
    click_timeout: int = 3000  # General click timeout
    visibility_timeout: int = 2000  # Element visibility timeout
    attribute_timeout: int = 1000  # Attribute retrieval timeout
    selector_test_timeout: int = 2000  # Selector testing timeout
    posts_count_timeout: int = 10000  # Posts count selector timeout
    link_scraper_timeout: int = 60000  # Link scraper navigation timeout

    # Specific operation timeouts
    follow_element_timeout: int = 2000  # Follow button element timeout
    follow_click_timeout: int = 3000  # Follow button click timeout
    followers_link_timeout: int = 3000  # Followers link click timeout
    followers_attr_timeout: int = 1000  # Followers attribute timeout
    message_button_timeout: int = 3000  # Message button timeout
    message_input_visibility_timeout: int = 2000  # Message input visibility timeout
    tag_button_click_timeout: int = 3000  # Tag button click timeout
    popup_close_timeout: int = 2000  # Popup close timeout
    post_tag_wait_timeout: int = 5000  # Post tag wait timeout
    reel_likes_timeout: int = 3000  # Reel likes timeout
    reel_element_timeout: int = 3000  # Reel element timeout

    # ==================== PAGE NAVIGATION DELAYS ====================
    page_load_delay: float = 2.0  # Wait after page loads
    page_stability_delay: float = 2.0  # Wait for page to stabilize after load
    profile_load_delay: float = 2.0  # Wait after loading profile page
    follow_profile_load_delay: float = 2.0  # Wait after loading profile for follow
    message_profile_load_delay: float = 2.0  # Wait after loading profile for messaging
    followers_profile_load_delay: float = 2.0  # Wait after loading profile for followers

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
    scroll_viewport_percentage: float = 0.8  # Scroll percentage for viewport
    scroll_wait_range: tuple = (1.5, 2.5)  # Random wait range for scrolling

    # ==================== SCROLL BEHAVIOR SETTINGS ====================
    # Container-based scrolling (for post/reel link collection)
    scroll_container_wait_timeout: float = 5.0  # Max seconds to wait for new containers to load
    scroll_container_check_interval: float = 0.5  # Check every 0.5s if containers loaded
    scroll_container_stability_wait: float = 0.5  # Wait after containers load for stability
    scroll_adaptive_offset_small: int = 2  # Offset for ≤10 containers (closer to end)
    scroll_adaptive_offset_large: int = 5  # Offset for >10 containers (further from end)
    scroll_adaptive_threshold: int = 10  # Container count threshold for offset switching
    scroll_fallback_pixels: int = 600  # Fallback scroll distance in pixels
    scroll_fallback_wait: float = 1.5  # Wait after fallback scroll
    scroll_max_no_new_attempts: int = 7  # Max attempts with no new links before stopping
    scroll_max_attempts_override: int = 150  # Override max_scroll_attempts for link collection
    followers_max_no_new_scrolls: int = 7  # Max no new followers scrolls (Updated by user request)

    # ==================== INPUT & TYPING DELAYS ====================
    input_focus_delay: float = 0.5  # Wait after clicking input field
    input_before_type_delay_min: float = 1.0  # Min delay before typing
    input_before_type_delay_max: float = 1.5  # Max delay before typing
    input_after_type_delay_min: float = 0.5  # Min delay after typing
    input_after_type_delay_max: float = 1.0  # Max delay after typing
    message_typing_delay_ms: int = 50  # Typing delay per character in milliseconds

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
    default_retry_initial_delay: float = 1.0  # Initial retry delay for error handler
    default_retry_backoff_factor: float = 2.0  # Exponential backoff multiplier

    # ==================== UI STABILITY DELAYS ====================
    ui_animation_delay: float = 1.5  # Wait for UI animations
    ui_stability_delay: float = 1.0  # Wait for UI to stabilize
    ui_micro_delay: float = 0.3  # Tiny delay for UI updates
    ui_mini_delay: float = 0.5  # Small delay for quick UI changes
    ui_element_load_delay: float = 0.1  # Very small delay for element loading

    # ==================== SCROLL SETTINGS ====================
    max_scroll_attempts: int = 1000

    # ==================== RETRY SETTINGS ====================
    max_retries: int = 3
    default_max_retries: int = 3  # Default max retries for error handler

    # ==================== THRESHOLDS ====================
    follow_max_button_search: int = 20  # Max buttons to search for follow operations
    worker_max_button_search: int = 20  # Max loop iterations for parallel worker
    memory_check_interval: int = 10  # Memory check interval
    memory_threshold_mb: float = 500.0  # Memory threshold in MB
    diagnostics_success_threshold_ok: int = 80  # Diagnostics success rate (OK)
    diagnostics_success_threshold_partial: int = 50  # Diagnostics success rate (PARTIAL)
    diagnostics_reel_success_threshold_ok: int = 70  # Reel diagnostics success rate (OK)
    diagnostics_reel_success_threshold_partial: int = 40  # Reel diagnostics success rate (PARTIAL)
    reel_max_span_check: int = 20  # Max span elements to check for reels

    # ==================== LOGGING ====================
    log_file: Optional[str] = 'instagram_scraper.log'
    log_level: str = 'INFO'
    log_to_console: bool = True
    log_format: str = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    log_date_format: str = '%Y-%m-%d %H:%M:%S'

    # ==================== OUTPUT FILES ====================
    links_file: str = 'post_links.txt'
    excel_filename_pattern: str = "instagram_data_{username}.xlsx"
    json_filename_pattern: str = "instagram_data_{username}.json"
    reel_links_filename_pattern: str = "reel_links_{username}.txt"

    # ==================== EXCEL SETTINGS ====================
    excel_max_column_width: int = 50  # Max column width in Excel
    excel_columns: List[str] = field(default_factory=lambda: [
        'Post URL', 'Type', 'Tagged Accounts', 'Likes', 'Timestamp'
    ])

    # ==================== TEXT VALUES ====================
    default_no_tags_text: str = 'No tags'  # Default text for no tags
    unfollow_text_search: str = 'unfollow'  # Text to search for unfollow
    follow_button_text: List[str] = field(default_factory=lambda: ["Follow", "Follow Back"])  # Follow button texts

    # ==================== DATETIME FORMATS ====================
    datetime_format: str = '%Y-%m-%d %H:%M:%S'  # Standard datetime format

    # ==================== ERROR MESSAGES ====================
    report_separator_width: int = 70  # Width of separator in error reports
    error_recent_limit: int = 5  # Number of recent errors to show

    # ==================== PAGE LOAD STRATEGIES ====================
    page_load_wait_until: str = 'domcontentloaded'  # Default page load strategy
    session_save_wait_until: str = 'networkidle'  # Wait strategy for session save

    # ==================== DETECTION STRINGS ====================
    login_detection_strings: List[str] = field(default_factory=lambda: ['loginForm', 'login'])
    profile_not_found_strings: List[str] = field(default_factory=lambda: [
        'Page Not Found', 'Sorry, this page'
    ])

    # ==================== SYSTEM FILTERS ====================
    instagram_system_paths: List[str] = field(default_factory=lambda: [
        'explore', 'direct', 'accounts', 'p', 'reel', 'tv', 'stories',
        'followers', 'following', 'reels', 'tagged'
    ])

    # ==================== CSS SELECTORS ====================
    # Profile selectors
    # Profile selectors
    selector_posts_count: str = 'span:has-text("posts")'
    selector_html_span: str = 'span.html-span'
    selector_followers_link: str = 'a[href*="/followers/"]'
    selector_following_link: str = 'a[href*="/following/"]'
    selector_post_reel_links: str = 'a[href*="/p/"], a[href*="/reel/"]'
    selector_verified_badge: str = 'svg[aria-label="Verified"]'  # Verified account badge
    selector_profile_category: str = 'div._ap3a._aaco._aacu._aacy._aad6._aade'  # Profile category (Actor, Model, etc.)
    
    # Bio Text & Links
    # Robust Structural Selectors:
    # Bio is usually in a section inside the header.
    # We select ALL spans with dir="auto" inside the header sections and rely on python filtering to pick the right one.
    # We avoid specific class names like .xqui205 as they are dynamic.
    selector_profile_bio_text: str = 'header section span[dir="auto"]'
    
    # Link container: Target the ICON, then traverse up in python.
    # We remove 'section' to be safer as the link might be in a div sibling to the section.
    # We also remove 'header' to be maximally robust (some mobile views or layouts might differ).
    selector_bio_link_container: str = 'svg[aria-label="Link icon"]'
    selector_examples_links: str = 'a[href*="threads"]' 
    selector_threads_badge: str = 'svg[aria-label="Threads"]'
    
    # Private Account Detection
    selector_private_text_indicators: List[str] = field(default_factory=lambda: [
        "This account is private",
        "Follow to see their photos and videos"
    ])
    selector_private_icon: str = 'svg[aria-label="Private"]'
    selector_private_title: str = 'h2'  # Sometimes h2 contains the text

    # Popup and dialog selectors
    selector_popup_dialog: str = 'div[role="dialog"]'
    selector_close_button: str = 'button:has(svg[aria-label="Close"])'

    # Tag selectors
    selector_tag_button: str = 'button:has(svg[aria-label="Tags"])'
    selector_post_tag_container: str = 'div._aa1y'
    selector_post_tag: str = 'div._aa1y'

    # Follower selectors
    selector_follower_container: str = 'div.x1dm5mii.x16mil14.xieb3on.x1e56ztr.x1lliihq.x193iq5w.xh8yej3'
    selector_follower_username_span: str = 'span.xjp7ctv'

    # Reel selectors
    selector_reel_container: str = 'div._ac7v.x1ty9z65.xzboxd6'
    selector_reel_likes: str = 'span.x1ypdohk.xt0psk2.x1xlr1w8.xzsf02u'
    selector_reel_timestamp: str = 'time.x1p4m5qa'

    # Grid/Feed Loop Selectors (for extracting metadata while scrolling)
    selector_grid_time: str = 'span.html-span'  # For stats like "13.5K"
    selector_grid_thumbnail_img: str = 'img'  # For PostPage.html
    selector_grid_thumbnail_bg: str = 'div[style*="background-image"]'  # For ReelsPage.html

    # Message button selectors (multiple options)
    selector_message_buttons: List[str] = field(default_factory=lambda: [
        'div[role="button"]:has-text("Message")',
        'button:has-text("Message")',
        'div._acan._acap._acas._aj1-._ap30:has-text("Message")',
        'div[role="button"] > div:has-text("Message")'
    ])

    # Message input selectors (multiple options)
    selector_message_inputs: List[str] = field(default_factory=lambda: [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][aria-label*="Message"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="Message"]',
        'div.xzsf02u.x1a2a7pz.x1n2onr6.x14wi4xw.x9f619.x1lliihq.x5yr21d.xh8yej3.xjpr12u'
    ])

    # Send button selectors (multiple options)
    selector_send_buttons: List[str] = field(default_factory=lambda: [
        'div[role="button"]:has-text("Send")',
        'button:has-text("Send")',
        'div._acan._acap._acar._acas._aj1-._ap30:has-text("Send")',
        'div[role="button"] svg[aria-label="Send"]',
        'button svg[aria-label="Send"]'
    ])

    # Following button selectors (multiple options for unfollow)
    selector_following_buttons: List[str] = field(default_factory=lambda: [
        'div._acan._acap._acat._aj1-._ap30:has-text("Following")',
        'button:has-text("Following")',
        'div[role="button"]:has-text("Following")'
    ])

    # Unfollow confirm button selectors (multiple options)
    selector_unfollow_confirm_buttons: List[str] = field(default_factory=lambda: [
        'button.x1ypdohk.xt0psk2.x78zum5.xdt5ytf.x6ikm8r.x10wlt62.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1hl2dhg.x16tdsg8.x1a2a7pz.xc9qbxq.x1ed109x.x1120s5i.x1247r65.x889kno.x1a8lsjc.x1sln4lm:has-text("Unfollow")',
        'button._a9--._ap36._a9_1:has-text("Unfollow")',
        'button:has-text("Unfollow")',
        'div[role="button"]:has-text("Unfollow")'
    ])

    # Popup container selectors (multiple options)
    selector_popup_containers: List[str] = field(default_factory=lambda: [
        'div[role="dialog"]',
        'div.x1cy8zhl.x9f619.x78zum5.xl56j7k.x2lwn1j.xeuugli.x47corl.x10l6tqk.x13vifvy.x1n327nk.x1ug75am.x1ja2u2z.x1xp8e9x.xexx8yu.x18d9i69.x1e558r4.x150jy0e.x1yrsyyn.x1fcty0u',
        'div._aa1y',
        'div[style*="overflow: hidden auto"]',
        'div[style*="overflow-y: auto"]',
        'div[style*="max-height"][style*="overflow-y: auto"]'
    ])

    # Likes selectors (multiple options for different layouts)
    selector_likes_options: List[str] = field(default_factory=lambda: [
        'span.html-span.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1hl2dhg.x16tdsg8.x1vvkbs',
        'section.x12nagc span.xdj266r',
        'span.html-span.xdj266r',
        'a[href*="/liked_by/"] span',
        'section[class*="x"] > div > span'
    ])

    # Timestamp selectors (multiple options)
    selector_timestamp_options: List[str] = field(default_factory=lambda: [
        'time.x1p4m5qa.x1r8a6vb.x1xlr1w8.x1ejq31n.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1hl2dhg.x16tdsg8.x1vvkbs',
        'time[datetime]',
        'time.x1p4m5qa',
        'time._aaqe'
    ])

    # Diagnostics selectors
    diagnostics_post_selectors: Dict[str, str] = field(default_factory=lambda: {
        'likes': 'span.html-span.xdj266r',
        'timestamp': 'time[datetime]',
        'tagged': 'button:has(svg[aria-label="Tags"])',
        'caption': 'h1._aacl._aaco._aacu._aacx._aad7._aade',
        'comments': 'section.x1ypdohk.x1pa1cj4 span.x1lliihq'
    })

    diagnostics_reel_selectors: Dict[str, str] = field(default_factory=lambda: {
        'likes': 'span.x1ypdohk.xt0psk2',
        'timestamp': 'time.x1p4m5qa',
        'tagged': 'button:has(svg[aria-label="Tags"])',
        'views': 'span.xrbpuxu',
        'audio': 'div._ac0k a'
    })

    # ==================== COMMENT SCRAPING SETTINGS ====================
    # Feature flags
    scrape_comments: bool = False  # Enable comment scraping
    scrape_comment_replies: bool = True  # Include replies in comment scraping
    scrape_collaborators: bool = True  # Extract post collaborators

    # Limits
    max_comments_per_post: Optional[int] = None  # None = all comments
    max_replies_per_comment: Optional[int] = None  # None = all replies
    comment_max_scroll_attempts: int = 100  # Max scroll attempts to load comments
    comment_max_no_new_scrolls: int = 5  # Stop after X scrolls with no new comments

    # Delays (in seconds)
    comment_scroll_delay_min: float = 1.0  # Min delay between comment scrolls
    comment_scroll_delay_max: float = 2.0  # Max delay between comment scrolls
    comment_reply_load_delay: float = 1.5  # Wait for replies to load
    comment_post_delay_min: float = 3.0  # Min delay between posts (comment scraping)
    comment_post_delay_max: float = 5.0  # Max delay between posts (comment scraping)

    # Comment CSS Selectors for DIRECT URL VIEW (https://www.instagram.com/p/POST_ID/)
    # NOTE: updated based on 2026 HTML structure analysis (Reels/Universal)
    # Using specific classes like x1iyjqo2 which represents a comment row
    selector_comment_thread: str = 'div.x1iyjqo2:has(a[href*="/c/"])'  # Robust thread finder
    selector_comment_main_body: str = 'div.x1iyjqo2'  # Fallback to the row itself if specific wrapper absent
    selector_comment_replies_wrapper: str = 'div.x5yr21d.xw2csxc'  # Container for nested replies (legacy/post specific)
    
    selector_comment_item: str = 'div.x1iyjqo2'  # Generic comment content row (used in main and replies)
    selector_comment_username_link: str = 'a.notranslate._a6hd'  # Username link
    selector_comment_username_text: str = 'span._ap3a._aaco._aacw._aacx._aad7._aade'  # Username text container
    selector_comment_text: str = 'span[dir="auto"]'  # Comment text span
    selector_comment_time: str = 'time[datetime]'  # Comment timestamp
    selector_comment_permalink: str = 'a[href*="/c/"]'  # Comment permalink (/p/POST_ID/c/COMMENT_ID/)
    selector_comment_likes_count: str = 'span.x193iq5w.x6ikm8r.x10wlt62'  # "X likes" text span
    selector_comment_reply_button: str = 'div[role="button"] span:has-text("Reply")'  # Reply button
    selector_comment_view_replies: str = 'span:has-text("View all")'  # Generic view replies text
    selector_comment_load_more: str = 'svg[aria-label="Load more comments"]'  # Load more (if exists, usually handled by scroll)
    
    # Scrollable container (Reels often show comments in a sidebar/modal)
    # x4h1yfo: User suggested specific container
    # x5yr21d: Common comment section wrapper
    selector_scrollable_container: str = 'div.x4h1yfo, div.x5yr21d, div[role="dialog"] > div > div > div'

    # Collaborator selectors (for post co-authors)
    selector_collaborator_container: str = 'header'  # Collaborator section in header
    selector_collaborator_link: str = 'a[href^="/"]'  # Collaborator profile link
    selector_collaborator_image: str = 'img[alt*="profile picture"]'  # Collaborator profile image
    selector_collaborator_others: str = 'span:has-text("and")'  # "and X others" text

    # Export settings
    comments_json_filename_pattern: str = "comments_{username}_{post_id}.json"
    comments_excel_filename_pattern: str = "comments_{username}.xlsx"

    # Excel columns for comments
    comments_excel_columns: List[str] = field(default_factory=lambda: [
        'Post URL',
        'Post ID',
        'Comment ID',
        'Author Username',
        'Author Verified',
        'Comment Text',
        'Likes Count',
        'Reply Count',
        'Timestamp',
        'Timestamp ISO',
        'Is Reply',
        'Parent Comment ID',
        'Comment URL',
        'Scraped At'
    ])

    # Excel columns for collaborators
    collaborators_excel_columns: List[str] = field(default_factory=lambda: [
        'Post URL',
        'Post ID',
        'Username',
        'Profile URL',
        'Is Verified',
        'Scraped At'
    ])

    # ==================== PRIVATE ACCOUNT DETECTORS ====================
    selector_private_icon: str = 'svg[aria-label="Private"]'
    selector_private_title: str = 'h2'  # Often inside h2
    selector_private_text_indicators: List[str] = field(default_factory=lambda: [
        'This Account is Private',
        'Follow to see their photos and videos'
    ])



    # ==================== LOCALIZATION & PARSING ====================
    number_suffixes: Dict[str, int] = field(default_factory=lambda: {
        'K': 1000, 'M': 1000000, 'B': 1000000000,
        'тыс.': 1000, 'млн.': 1000000,
        'ming': 1000, 'mln': 1000000,
        'k': 1000, 'm': 1000000
    })
    number_separators: List[str] = field(default_factory=lambda: [',', '.', ' '])
    return_empty_list_for_no_tags: bool = True
