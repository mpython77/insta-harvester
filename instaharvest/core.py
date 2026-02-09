"""
InstaHarvest - Central Hub
Main entry point that connects all modules together.

Usage:
    from instaharvest import InstaHarvest, ScraperConfig
    
    config = ScraperConfig(
        proxies=["http://user:pass@proxy.com:8080"],
        enable_stealth=True,
        headless=False
    )
    
    hub = InstaHarvest(config)
    hub.check_proxies()
    proxy = hub.get_proxy()
"""

from typing import Optional, Dict, List, Any

from .config import ScraperConfig
from .logging_config import SmartLogger
from .proxy import ProxyManager


class InstaHarvest:
    """
    Central hub for InstaHarvest library.
    
    Connects all modules (proxy, stealth, browser) and provides
    unified access to functionality.
    
    Attributes:
        config: ScraperConfig instance
        logger: SmartLogger instance
        proxy_manager: ProxyManager for HTTP proxies
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize InstaHarvest hub.
        
        Args:
            config: ScraperConfig instance (creates default if None)
        """
        self.config = config or ScraperConfig()
        
        # Initialize SmartLogger
        self.logger = SmartLogger.from_config(self.config, name='InstaHarvest')
        
        # Initialize ProxyManager
        self.proxy_manager = ProxyManager.from_config(self.config, self.logger)
        
        self.logger.info("InstaHarvest initialized", 
                        proxies=len(self.proxy_manager._proxy_pool) if self.proxy_manager else 0,
                        stealth=self.config.enable_stealth)
    
    # ==================== Proxy Methods ====================
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get proxy for Playwright browser.
        
        Returns:
            Dict with 'server', 'username', 'password' or None
        """
        return self.proxy_manager.get_for_playwright()
    
    def get_curl_proxy(self) -> Optional[str]:
        """
        Get proxy for curl_cffi/requests.
        
        Returns:
            Proxy URL string like "http://user:pass@ip:port" or None
        """
        return self.proxy_manager.get_for_curl()
    
    def check_proxies(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Test all proxies and show results.
        
        Args:
            verbose: Print formatted table with latency and location
            
        Returns:
            Dict of proxy check results
        """
        return self.proxy_manager.check_all_proxies(verbose=verbose)
    
    def proxy_stats(self) -> Dict[str, Any]:
        """Get proxy usage statistics"""
        return self.proxy_manager.get_stats()
    
    # ==================== Config Access ====================
    
    def update_config(self, **kwargs) -> None:
        """
        Update config values dynamically.
        
        Args:
            **kwargs: Config attributes to update
            
        Example:
            hub.update_config(headless=True, enable_stealth=False)
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.debug(f"Config updated", key=key, value=value)
            else:
                self.logger.warning(f"Unknown config key", key=key)
    
    # ==================== Properties ====================
    
    @property
    def has_proxies(self) -> bool:
        """Check if proxies are configured"""
        return self.proxy_manager.has_proxies
    
    @property
    def healthy_proxy_count(self) -> int:
        """Count of healthy proxies"""
        return self.proxy_manager.healthy_count
    
    # ==================== String Representation ====================
    
    def __repr__(self) -> str:
        return f"InstaHarvest(proxies={self.healthy_proxy_count}, stealth={self.config.enable_stealth})"
