import random
from typing import List, Optional, Dict

class SecurityManager:
    """
    Manages security features like User-Agent rotation and Proxy selection
    to prevent detection and blocking.
    """
    
    # Modern User-Agents (Chrome, Firefox, Safari, Edge) on Windows/Mac
    # Updated: 2026
    USER_AGENTS = [
        # Chrome Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        
        # Firefox Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        
        # Edge Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        
        # Chrome Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        
        # Safari Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
    ]

    @staticmethod
    def get_random_user_agent(custom_list: Optional[List[str]] = None) -> str:
        """Returns a random User-Agent from built-in or custom list"""
        if custom_list:
            return random.choice(custom_list)
            
        # Use fake_useragent for real-world agents
        try:
            from fake_useragent import UserAgent
            ua = UserAgent()
            # Randomly pick between Chrome, Firefox, Safari to vary fingerprint
            browser_type = random.choice(['chrome', 'firefox', 'safari', 'edge'])
            return ua.getattr(browser_type)
        except Exception:
            # Fallback to hardcoded list if library fails
            return random.choice(SecurityManager.USER_AGENTS)

    @staticmethod
    def format_proxy(proxy_url: str) -> Dict[str, str]:
        """
        Formats proxy string into Playwright dictionary format.
        Input: protocol://user:pass@ip:port OR ip:port
        Output: {'server': 'protocol://ip:port', 'username': 'user', 'password': 'pass'}
        """
        if not proxy_url:
            return None
            
        # Handle "server" key if already formatted dict (for flexibility)
        if isinstance(proxy_url, dict):
            return proxy_url

        try:
            # Ensure protocol is present for parsing
            if '://' not in proxy_url:
                proxy_url = f'http://{proxy_url}'
            
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            
            server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            
            proxy_dict = {'server': server}
            
            if parsed.username and parsed.password:
                proxy_dict['username'] = parsed.username
                proxy_dict['password'] = parsed.password
                
            return proxy_dict
        except Exception:
            # Fallback if parsing completely fails
            return {'server': proxy_url}

    @staticmethod
    def get_random_proxy(proxy_list: List[str]) -> Optional[Dict[str, str]]:
        """Selects a random proxy from the list and formats it"""
        if not proxy_list:
            return None
        
        raw_proxy = random.choice(proxy_list)
        return SecurityManager.format_proxy(raw_proxy)
