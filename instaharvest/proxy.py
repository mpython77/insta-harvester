"""
Instagram Scraper - Professional HTTP Proxy Management
Enterprise-grade proxy support with rotation, health checking, and failure tracking.

Features:
- Single proxy or pool support
- Automatic rotation (round-robin, random, sticky)
- Proxy health checking with latency & location
- Failure tracking and auto-removal
- Playwright and curl_cffi format support
- HTTP/HTTPS proxies only (Chrome compatible)
"""

import random
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse
from enum import Enum


class RotationStrategy(Enum):
    """Proxy rotation strategies"""
    ROUND_ROBIN = "round_robin"  # Cycle through proxies in order
    RANDOM = "random"  # Random selection each time
    STICKY = "sticky"  # Stay with one proxy until it fails


@dataclass
class ProxyStats:
    """Statistics for a single proxy"""
    url: str
    requests: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    last_used: float = 0.0
    last_failure: float = 0.0
    is_healthy: bool = True
    
    # Health check results
    latency_ms: Optional[float] = None
    ip_address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    country_code: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        if self.requests == 0:
            return 1.0
        return self.successes / self.requests
    
    @property
    def location(self) -> str:
        """Human-readable location string"""
        if self.city and self.country:
            return f"{self.city}, {self.country}"
        elif self.country:
            return self.country
        return "Unknown"


@dataclass
class ProxyConfig:
    """Parsed proxy configuration - HTTP/HTTPS only"""
    server: str  # http://host:port
    username: Optional[str] = None
    password: Optional[str] = None
    host: str = ""
    port: int = 0
    original_url: str = ""
    
    @property
    def has_auth(self) -> bool:
        return bool(self.username and self.password)
    
    def to_playwright(self) -> Dict[str, str]:
        """Convert to Playwright proxy format"""
        result = {'server': self.server}
        if self.has_auth:
            result['username'] = self.username
            result['password'] = self.password
        return result
    
    def to_curl(self) -> str:
        """Convert to curl_cffi/requests format"""
        if self.has_auth:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return self.server


class ProxyManager:
    """
    Professional HTTP proxy management for Instagram scraping.
    
    Features:
    - Single proxy or pool support
    - Automatic rotation with multiple strategies
    - Health checking with latency and location
    - Failure tracking with auto-removal
    - Chrome/Chromium compatible (HTTP only)
    
    Usage:
        # Single proxy
        manager = ProxyManager(proxy_url="http://user:pass@proxy.com:8080")
        
        # Proxy pool with rotation
        manager = ProxyManager(proxies=[
            "http://user:pass@proxy1.com:8080",
            "http://user:pass@proxy2.com:8080",
        ])
        
        # Get proxy for Playwright browser launch
        playwright_proxy = manager.get_for_playwright()
        
        # Get proxy for curl_cffi/requests
        curl_proxy = manager.get_for_curl()
    """
    
    # Test URL for health checking (returns IP and location)
    TEST_URL = "http://ip-api.com/json"
    TEST_TIMEOUT = 15
    
    def __init__(
        self,
        proxy_url: Optional[str] = None,
        proxies: Optional[List[str]] = None,
        rotation_strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        rotation_interval: int = 10,
        max_failures: int = 3,
        check_on_start: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize ProxyManager.
        
        Args:
            proxy_url: Single proxy URL (simple usage)
            proxies: List of proxy URLs (pool)
            rotation_strategy: How to rotate proxies (round_robin, random, sticky)
            rotation_interval: Rotate every N requests (for round-robin)
            max_failures: Disable proxy after N consecutive failures
            check_on_start: Validate proxies on initialization
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.rotation_strategy = rotation_strategy
        self.rotation_interval = rotation_interval
        self.max_failures = max_failures
        
        # Proxy pool
        self._proxy_pool: List[ProxyConfig] = []
        self._proxy_stats: Dict[str, ProxyStats] = {}
        self._current_index = 0
        self._request_count = 0
        
        # Initialize pool
        if proxy_url:
            self._add_proxy(proxy_url)
        
        if proxies:
            for p in proxies:
                self._add_proxy(p)
        
        # Health check if requested
        if check_on_start and self._proxy_pool:
            self.check_all_proxies(verbose=False)
        
        # Log initialization
        if self._proxy_pool:
            self.logger.info(f"ProxyManager initialized with {len(self._proxy_pool)} proxy(ies)")
            if len(self._proxy_pool) > 1:
                self.logger.info(f"  Strategy: {rotation_strategy.value}, Interval: {rotation_interval}")
    
    def _parse_proxy(self, proxy_url: str) -> ProxyConfig:
        """
        Parse proxy URL into ProxyConfig.
        
        Supports formats:
        - http://ip:port
        - http://user:pass@ip:port
        - ip:port (assumes http)
        - user:pass@ip:port (assumes http)
        """
        if not proxy_url:
            raise ValueError("Proxy URL cannot be empty")
        
        # Add http:// if missing
        if '://' not in proxy_url:
            proxy_url = f'http://{proxy_url}'
        
        try:
            parsed = urlparse(proxy_url)
            
            host = parsed.hostname or ''
            port = parsed.port or 8080
            server = f"http://{host}:{port}"
            
            return ProxyConfig(
                server=server,
                username=parsed.username,
                password=parsed.password,
                host=host,
                port=port,
                original_url=proxy_url
            )
        except Exception as e:
            self.logger.error(f"Failed to parse proxy URL: {proxy_url} - {e}")
            raise ValueError(f"Invalid proxy URL: {proxy_url}")
    
    def _add_proxy(self, proxy_url: str) -> None:
        """Add a proxy to the pool"""
        try:
            config = self._parse_proxy(proxy_url)
            self._proxy_pool.append(config)
            self._proxy_stats[config.server] = ProxyStats(url=config.server)
            self.logger.debug(f"Added proxy: {config.server}")
        except Exception as e:
            self.logger.warning(f"Failed to add proxy: {e}")
    
    # ==================== Properties ====================
    
    @property
    def has_proxies(self) -> bool:
        """Check if any proxies are available"""
        return len(self._proxy_pool) > 0
    
    @property
    def healthy_count(self) -> int:
        """Count of healthy proxies"""
        return sum(1 for p in self._proxy_pool if self._proxy_stats[p.server].is_healthy)
    
    @property
    def current_proxy(self) -> Optional[ProxyConfig]:
        """Get current proxy without rotation"""
        if not self._proxy_pool:
            return None
        
        # Filter to healthy proxies
        healthy = [p for p in self._proxy_pool if self._proxy_stats[p.server].is_healthy]
        if not healthy:
            # All failed, reset and try again
            self.logger.warning("All proxies unhealthy, resetting...")
            for stats in self._proxy_stats.values():
                stats.is_healthy = True
                stats.consecutive_failures = 0
            healthy = self._proxy_pool
        
        if self._current_index >= len(healthy):
            self._current_index = 0
        
        return healthy[self._current_index]
    
    # ==================== Get Proxy Methods ====================
    
    def get_proxy(self) -> Optional[ProxyConfig]:
        """
        Get proxy with rotation logic.
        
        Returns:
            ProxyConfig or None if no proxies configured
        """
        if not self._proxy_pool:
            return None
        
        self._request_count += 1
        
        # Apply rotation
        if len(self._proxy_pool) > 1:
            if self.rotation_strategy == RotationStrategy.ROUND_ROBIN:
                if self._request_count % self.rotation_interval == 0:
                    self._rotate_to_next()
            elif self.rotation_strategy == RotationStrategy.RANDOM:
                healthy_indices = [i for i, p in enumerate(self._proxy_pool) 
                                  if self._proxy_stats[p.server].is_healthy]
                if healthy_indices:
                    self._current_index = random.choice(healthy_indices)
        
        proxy = self.current_proxy
        if proxy:
            stats = self._proxy_stats[proxy.server]
            stats.requests += 1
            stats.last_used = time.time()
        
        return proxy
    
    def get_for_playwright(self) -> Optional[Dict[str, str]]:
        """
        Get proxy formatted for Playwright browser.launch(proxy={...})
        
        Returns:
            Dict with 'server', 'username', 'password' keys or None
            
        Example:
            browser = playwright.chromium.launch(
                proxy=manager.get_for_playwright()
            )
        """
        proxy = self.get_proxy()
        if not proxy:
            return None
        return proxy.to_playwright()
    
    def get_for_curl(self) -> Optional[str]:
        """
        Get proxy formatted for curl_cffi/requests.
        
        Returns:
            Proxy URL string like "http://user:pass@host:port" or None
        """
        proxy = self.get_proxy()
        if not proxy:
            return None
        return proxy.to_curl()
    
    def get_for_requests(self) -> Optional[Dict[str, str]]:
        """
        Get proxy formatted for requests library.
        
        Returns:
            Dict like {"http": "...", "https": "..."} or None
        """
        curl_proxy = self.get_for_curl()
        if not curl_proxy:
            return None
        return {"http": curl_proxy, "https": curl_proxy}
    
    # ==================== Tracking Methods ====================
    
    def mark_success(self, proxy_server: Optional[str] = None) -> None:
        """Record successful request"""
        if not proxy_server and self.current_proxy:
            proxy_server = self.current_proxy.server
        
        if proxy_server and proxy_server in self._proxy_stats:
            stats = self._proxy_stats[proxy_server]
            stats.successes += 1
            stats.consecutive_failures = 0
            stats.is_healthy = True
    
    def mark_failure(self, proxy_server: Optional[str] = None, error: Optional[str] = None) -> None:
        """Record failed request. May disable proxy if too many failures."""
        if not proxy_server and self.current_proxy:
            proxy_server = self.current_proxy.server
        
        if proxy_server and proxy_server in self._proxy_stats:
            stats = self._proxy_stats[proxy_server]
            stats.failures += 1
            stats.consecutive_failures += 1
            stats.last_failure = time.time()
            
            if error:
                self.logger.warning(f"Proxy failure ({proxy_server}): {error}")
            
            if stats.consecutive_failures >= self.max_failures:
                stats.is_healthy = False
                self.logger.warning(f"Proxy disabled after {stats.consecutive_failures} failures: {proxy_server}")
                
                # Rotate to next healthy proxy
                if len(self._proxy_pool) > 1:
                    self._rotate_to_next()
    
    def _rotate_to_next(self) -> None:
        """Rotate to next healthy proxy"""
        for i in range(len(self._proxy_pool)):
            next_index = (self._current_index + 1 + i) % len(self._proxy_pool)
            proxy = self._proxy_pool[next_index]
            if self._proxy_stats[proxy.server].is_healthy:
                self._current_index = next_index
                self.logger.debug(f"Rotated to proxy: {proxy.server}")
                return
    
    # ==================== Health Check ====================
    
    def check_proxy(self, proxy: ProxyConfig, timeout: int = None) -> Dict[str, Any]:
        """
        Test if a proxy is working and measure performance.
        
        Returns:
            Dict with: is_healthy, latency_ms, ip, country, city, error
        """
        result = {
            'is_healthy': False,
            'latency_ms': None,
            'ip': None,
            'country': None,
            'city': None,
            'country_code': None,
            'error': None
        }
        
        try:
            import requests
            
            timeout = timeout or self.TEST_TIMEOUT
            proxies = {
                "http": proxy.to_curl(),
                "https": proxy.to_curl()
            }
            
            start_time = time.time()
            response = requests.get(self.TEST_URL, proxies=proxies, timeout=timeout)
            latency_ms = (time.time() - start_time) * 1000
            result['latency_ms'] = round(latency_ms, 2)
            
            if response.status_code == 200:
                result['is_healthy'] = True
                
                try:
                    data = response.json()
                    result['ip'] = data.get('query', 'Unknown')
                    result['country'] = data.get('country', 'Unknown')
                    result['city'] = data.get('city', '')
                    result['country_code'] = data.get('countryCode', '')
                except Exception:
                    pass
                
                # Update stats
                stats = self._proxy_stats.get(proxy.server)
                if stats:
                    stats.latency_ms = result['latency_ms']
                    stats.ip_address = result['ip']
                    stats.country = result['country']
                    stats.city = result['city']
                    stats.country_code = result['country_code']
                    stats.is_healthy = True
                    stats.consecutive_failures = 0
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.debug(f"Proxy check failed ({proxy.server}): {e}")
        
        return result
    
    def check_all_proxies(self, verbose: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Validate all proxies in pool.
        
        Args:
            verbose: Print detailed table of results
            
        Returns:
            Dict mapping proxy server to check results
        """
        self.logger.info(f"Checking {len(self._proxy_pool)} proxies...")
        results = {}
        
        for proxy in self._proxy_pool:
            check_result = self.check_proxy(proxy)
            self._proxy_stats[proxy.server].is_healthy = check_result['is_healthy']
            results[proxy.server] = check_result
        
        healthy = sum(1 for r in results.values() if r['is_healthy'])
        self.logger.info(f"  {healthy}/{len(results)} proxies healthy")
        
        if verbose:
            print("\n" + "=" * 75)
            print(f"{'STATUS':<8} {'PROXY':<30} {'LATENCY':<10} {'IP':<16} {'LOCATION'}")
            print("=" * 75)
            for server, data in results.items():
                status = "[OK]" if data['is_healthy'] else "[FAIL]"
                latency = f"{data['latency_ms']:.0f}ms" if data['latency_ms'] else "N/A"
                ip = data['ip'] or "N/A"
                location = f"{data['city']}, {data['country']}" if data['city'] else (data['country'] or "N/A")
                server_display = server[:28] + ".." if len(server) > 30 else server
                print(f"{status:<8} {server_display:<30} {latency:<10} {ip:<16} {location}")
            print("=" * 75)
        
        return results
    
    # ==================== Stats ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy usage statistics"""
        return {
            'total_proxies': len(self._proxy_pool),
            'healthy_proxies': self.healthy_count,
            'total_requests': self._request_count,
            'rotation_strategy': self.rotation_strategy.value,
            'proxies': {
                server: {
                    'requests': stats.requests,
                    'successes': stats.successes,
                    'failures': stats.failures,
                    'success_rate': f"{stats.success_rate:.1%}",
                    'is_healthy': stats.is_healthy,
                    'latency_ms': stats.latency_ms,
                    'ip': stats.ip_address,
                    'location': stats.location
                }
                for server, stats in self._proxy_stats.items()
            }
        }
    
    @classmethod
    def from_config(cls, config: 'ScraperConfig', logger=None) -> 'ProxyManager':
        """
        Create ProxyManager from ScraperConfig.
        
        Args:
            config: ScraperConfig instance
            logger: Optional logger (creates default if None)
            
        Returns:
            Configured ProxyManager
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        
        strategy = RotationStrategy.ROUND_ROBIN if getattr(config, 'proxy_rotation', True) else RotationStrategy.STICKY
        
        return cls(
            proxy_url=getattr(config, 'proxy_url', None),
            proxies=getattr(config, 'proxies', []),
            rotation_strategy=strategy,
            rotation_interval=getattr(config, 'proxy_rotation_interval', 10),
            max_failures=getattr(config, 'proxy_max_failures', 3),
            check_on_start=getattr(config, 'proxy_check_on_start', False),
            logger=logger
        )
    
    def load_from_file(self, filepath: str) -> int:
        """
        Load proxies from a text/JSON/CSV file.

        Supported formats:
        - .txt: One proxy per line (http://user:pass@host:port)
        - .json: Array of proxy URLs or objects with 'url' key
        - .csv: One proxy per line

        Args:
            filepath: Path to proxy file

        Returns:
            Number of proxies added
        """
        from pathlib import Path
        path = Path(filepath)

        if not path.exists():
            self.logger.error(f"Proxy file not found: {filepath}")
            return 0

        count = 0
        try:
            content = path.read_text(encoding='utf-8').strip()

            if path.suffix == '.json':
                data = __import__('json').loads(content)
                if isinstance(data, list):
                    for item in data:
                        url = item.get('url', item) if isinstance(item, dict) else str(item)
                        if url and url.strip():
                            self._add_proxy(url.strip())
                            count += 1
            else:
                # txt/csv — one proxy per line
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Handle CSV (take first column)
                        if ',' in line and '://' not in line.split(',')[0]:
                            parts = line.split(',')
                            line = parts[0].strip()
                        if line:
                            self._add_proxy(line)
                            count += 1

            self.logger.info(f"Loaded {count} proxies from {path.name}")

        except Exception as e:
            self.logger.error(f"Failed to load proxies from {filepath}: {e}")

        return count

    def load_from_url(self, url: str, timeout: int = 15) -> int:
        """
        Load proxies from an online proxy list URL.

        Args:
            url: URL to fetch proxy list from
            timeout: Request timeout in seconds

        Returns:
            Number of proxies added
        """
        count = 0
        try:
            import requests
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                for line in resp.text.strip().splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self._add_proxy(line)
                        count += 1
                self.logger.info(f"Loaded {count} proxies from URL")
            else:
                self.logger.error(f"Failed to fetch proxies: HTTP {resp.status_code}")

        except ImportError:
            self.logger.error("requests library required for load_from_url")
        except Exception as e:
            self.logger.error(f"Failed to load proxies from URL: {e}")

        return count

    def auto_remove_dead(self) -> int:
        """
        Remove all unhealthy (dead) proxies from the pool.

        Returns:
            Number of proxies removed
        """
        dead = [
            p for p in self._proxy_pool
            if not self._proxy_stats[p.server].is_healthy
        ]

        for proxy in dead:
            self._proxy_pool.remove(proxy)
            del self._proxy_stats[proxy.server]
            self.logger.info(f"Removed dead proxy: {proxy.server}")

        if dead:
            self._current_index = 0
            self.logger.info(
                f"Removed {len(dead)} dead proxies, "
                f"{len(self._proxy_pool)} remaining"
            )

        return len(dead)

    def get_stats_summary(self) -> str:
        """Get formatted stats summary string"""
        lines = [
            f"\n{'='*70}",
            f"  Proxy Pool: {len(self._proxy_pool)} total, "
            f"{self.healthy_count} healthy",
            f"  Strategy: {self.rotation_strategy.value}",
            f"{'='*70}",
        ]

        for proxy in self._proxy_pool:
            stats = self._proxy_stats[proxy.server]
            icon = '✅' if stats.is_healthy else '❌'
            lines.append(
                f"  {icon} {proxy.server:35s} | "
                f"req={stats.requests:3d} ok={stats.successes:3d} "
                f"fail={stats.failures:3d} | "
                f"{stats.success_rate:.0%} | "
                f"{stats.location}"
            )

        summary = '\n'.join(lines)
        return summary

    def __repr__(self) -> str:
        if not self._proxy_pool:
            return "ProxyManager(no proxies)"
        return f"ProxyManager({len(self._proxy_pool)} proxies, {self.healthy_count} healthy)"


# ============================================
# Convenience Functions
# ============================================

def create_proxy_manager_from_config(config: 'ScraperConfig', logger: logging.Logger) -> ProxyManager:
    """
    Create ProxyManager from ScraperConfig.
    
    Args:
        config: ScraperConfig instance
        logger: Logger instance
        
    Returns:
        Configured ProxyManager
    """
    strategy = RotationStrategy.ROUND_ROBIN if getattr(config, 'proxy_rotation', True) else RotationStrategy.STICKY
    
    return ProxyManager(
        proxy_url=getattr(config, 'proxy_url', None),
        proxies=getattr(config, 'proxies', []),
        rotation_strategy=strategy,
        rotation_interval=getattr(config, 'proxy_rotation_interval', 10),
        max_failures=getattr(config, 'proxy_max_failures', 3),
        check_on_start=getattr(config, 'proxy_check_on_start', False),
        logger=logger
    )
