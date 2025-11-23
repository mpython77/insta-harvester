"""
Example: Custom Configuration for InstaHarvest
Shows how to configure delays and headless mode
"""

from instaharvest import FollowManager, MessageManager, FollowersCollector
from instaharvest.config import ScraperConfig


def example_custom_delays():
    """Example: Using custom delays for slow internet connections"""

    # Create custom config with longer delays
    config = ScraperConfig(
        # Browser settings
        headless=True,  # Run Chrome in headless mode (default)
        # headless=False,  # Uncomment to see the browser window

        # Custom delays for slow internet
        page_load_delay=5.0,  # Wait after page loads: 5 seconds (default: 2.0)
        button_click_delay=5.0,  # Wait after button clicks: 5 seconds (default: 2.5)
        action_delay_min=3.0,  # Minimum delay before actions: 3 seconds (default: 2.0)
        action_delay_max=5.0,  # Maximum delay before actions: 5 seconds (default: 3.5)

        # Scroll delays
        scroll_delay_min=2.0,  # Minimum delay between scrolls (default: 1.5)
        scroll_delay_max=4.0,  # Maximum delay between scrolls (default: 2.5)
    )

    # Use the custom config
    manager = FollowManager(config=config)

    try:
        # Load session
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        # Now all actions will use your custom delays
        result = manager.unfollow("username")
        print(f"Result: {result}")

    finally:
        manager.close()


def example_fast_internet():
    """Example: Faster delays for good internet connection"""

    config = ScraperConfig(
        headless=True,
        page_load_delay=1.5,  # Faster page load wait
        button_click_delay=1.5,  # Faster button click wait
        action_delay_min=1.0,  # Faster minimum delay
        action_delay_max=2.0,  # Faster maximum delay
    )

    manager = MessageManager(config=config)

    try:
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        result = manager.send_message("username", "Hello!")
        print(f"Result: {result}")

    finally:
        manager.close()


def example_headless_mode():
    """Example: Running with visible browser (for debugging)"""

    # Show browser window (not headless)
    config = ScraperConfig(
        headless=False  # Show the browser window
    )

    collector = FollowersCollector(config=config)

    try:
        session_data = collector.load_session()
        collector.setup_browser(session_data)

        followers = collector.get_followers("instagram", limit=10)
        print(f"Collected {len(followers)} followers")

    finally:
        collector.close()


def example_default_config():
    """Example: Using default configuration"""

    # Create default config explicitly (best practice!)
    # Default config values:
    # - headless=True (browser runs in background)
    # - page_load_delay=2.0 seconds
    # - button_click_delay=2.5 seconds
    # - action_delay_min=2.0 seconds
    # - action_delay_max=3.5 seconds
    # - scroll_delay_min=1.5 seconds
    # - scroll_delay_max=2.5 seconds

    config = ScraperConfig()  # Create explicit config
    manager = FollowManager(config=config)  # Pass config to manager

    try:
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        result = manager.follow("instagram")
        print(f"Result: {result}")

    finally:
        manager.close()


if __name__ == '__main__':
    print("=" * 70)
    print("InstaHarvest - Custom Configuration Examples")
    print("=" * 70)
    print()
    print("These examples show how to customize delays and browser settings:")
    print("1. Custom delays for slow internet")
    print("2. Faster delays for good internet")
    print("3. Headless mode control")
    print("4. Default configuration")
    print()
    print("Uncomment the example you want to try:")
    print()

    # Uncomment one of these to try:
    # example_custom_delays()
    # example_fast_internet()
    # example_headless_mode()
    # example_default_config()

    print("✅ See the code above for examples!")
