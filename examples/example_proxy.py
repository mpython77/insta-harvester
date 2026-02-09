"""
InstaHarvest - HTTP Proxy Support Examples
Shows how to configure and use HTTP/HTTPS proxies with Chrome.

IMPORTANT: Only HTTP/HTTPS proxies are supported.
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instaharvest import InstaHarvest, ScraperConfig, ProxyManager, SmartLogger


def example_hub_usage():
    """
    Example 1: InstaHarvest Hub (RECOMMENDED)
    Central access to all functionality via config
    """
    print("\n" + "=" * 60)
    print("Example 1: InstaHarvest Hub (Central Access)")
    print("=" * 60)
    
    # All settings in one place
    config = ScraperConfig(
        # Proxies from config
        proxies=[
            "http://apexqpredator:mbavBt9yDG@208.214.161.186:50101",
            "http://apexqpredator:mbavBt9yDG@161.77.55.99:50101",
            "http://apexqpredator:mbavBt9yDG@77.47.143.0:50101",
        ],
        proxy_rotation=True,
        proxy_rotation_interval=5,
        
        # Stealth
        enable_stealth=True,
        
        # Browser
        headless=False,
    )
    
    # Create hub - everything is connected
    hub = InstaHarvest(config)
    
    print(f"Hub: {hub}")
    print(f"Has proxies: {hub.has_proxies}")
    print(f"Healthy proxies: {hub.healthy_proxy_count}")


def example_proxy_check():
    """
    Example 2: Proxy Health Check with Config
    All proxies defined in config, not hardcoded
    """
    print("\n" + "=" * 60)
    print("Example 2: Proxy Health Check via Hub")
    print("=" * 60)
    
    config = ScraperConfig(
        proxies=[
            "http://apexqpredator:mbavBt9yDG@208.214.161.186:50101",
            "http://apexqpredator:mbavBt9yDG@161.77.55.99:50101",
            "http://apexqpredator:mbavBt9yDG@77.47.143.0:50101",
        ],
        log_level='WARNING',  # Reduce noise
    )
    
    hub = InstaHarvest(config)
    
    print(f"Testing {hub.healthy_proxy_count} proxies...\n")
    
    # Check all proxies - uses config settings
    results = hub.check_proxies(verbose=True)
    
    # Show stats
    print(f"\nHealthy: {hub.healthy_proxy_count}/{len(hub.proxy_manager._proxy_pool)}")


def example_smart_logging():
    """
    Example 3: Smart Logging
    Intelligent logging with context and timing
    """
    print("\n" + "=" * 60)
    print("Example 3: Smart Logging")
    print("=" * 60)
    
    # Create logger from config
    config = ScraperConfig(
        log_level='INFO',
        log_emoji_enabled=True,
    )
    
    logger = SmartLogger.from_config(config, name='MyScript')
    
    # Different log levels with emojis
    logger.success("Operation completed", items=10)
    logger.warning("Low disk space", available="500MB")
    logger.info("Processing started", target="cristiano")
    logger.proxy("Using proxy", server="208.214.161.186:50101")
    
    # Timed operation
    import time
    with logger.operation("Simulated scraping"):
        time.sleep(0.5)  # Simulate work
    
    print("\nLogging complete!")


def example_real_instagram():
    """
    Example 4: Real Instagram Scraping with Hub
    Uses InstaHarvest hub for everything
    """
    print("\n" + "=" * 60)
    print("Example 4: Real Instagram with Hub")
    print("=" * 60)
    
    from playwright.sync_api import sync_playwright
    import time
    
    # Config-driven approach
    config = ScraperConfig(
        proxies=[
            "http://apexqpredator:mbavBt9yDG@208.214.161.186:50101",
            "http://apexqpredator:mbavBt9yDG@161.77.55.99:50101",
        ],
        log_level='WARNING',
    )
    
    hub = InstaHarvest(config)
    
    # Get proxy from hub
    proxy_config = hub.get_proxy()
    print(f"Using proxy: {proxy_config['server']}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            proxy=proxy_config
        )
        
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent=config.user_agent  # From config!
        )
        page = context.new_page()
        
        try:
            target_user = "cristiano"
            print(f"\nLoading @{target_user}...")
            
            page.goto(f"https://www.instagram.com/{target_user}/", 
                     wait_until="domcontentloaded", 
                     timeout=30000)
            
            time.sleep(3)
            
            print("Profile loaded!")
            
            # Mark success in hub
            hub.proxy_manager.mark_success()
            
            # Show stats
            stats = hub.proxy_stats()
            print(f"Total requests: {stats['total_requests']}")
            
            print("\nBrowser will close in 3 seconds...")
            time.sleep(3)
            
        except Exception as e:
            print(f"Error: {e}")
            hub.proxy_manager.mark_failure(error=str(e))
            
        finally:
            browser.close()
            print("Done!")


def main():
    """Run all examples"""
    print("=" * 60)
    print("InstaHarvest - Centralized Architecture Examples")
    print("=" * 60)
    
    example_hub_usage()
    example_proxy_check()
    example_smart_logging()
    example_real_instagram()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
