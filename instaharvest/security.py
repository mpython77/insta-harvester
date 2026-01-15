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
        agents = custom_list if custom_list else SecurityManager.USER_AGENTS
        return random.choice(agents)

    @staticmethod
    def format_proxy(proxy_url: str) -> Dict[str, str]:
        """
        Formats proxy string into Playwright dictionary format.
        Input: http://user:pass@ip:port OR ip:port
        Output: {'server': 'http://ip:port', 'username': 'user', 'password': 'pass'}
        """
        if not proxy_url:
            return None
            
        # Handle "server" key if already formatted dict (for flexibility)
        if isinstance(proxy_url, dict):
            return proxy_url

        # Basic parsing logic
        # 1. Check for authentication
        if '@' in proxy_url:
            # Format: protocol://user:pass@host:port
            try:
                # Remove protocol if present
                clean_url = proxy_url.replace('http://', '').replace('https://', '')
                auth, server = clean_url.split('@')
                username, password = auth.split(':')
                
                return {
                    'server': f'http://{server}',
                    'username': username,
                    'password': password
                }
            except:
                # Fallback if parsing fails
                return {'server': proxy_url}
        else:
            # Format: protocol://host:port or host:port
            server = proxy_url if '://' in proxy_url else f'http://{proxy_url}'
            return {'server': server}

    @staticmethod
    def get_random_proxy(proxy_list: List[str]) -> Optional[Dict[str, str]]:
        """Selects a random proxy from the list and formats it"""
        if not proxy_list:
            return None
        
        raw_proxy = random.choice(proxy_list)
        return SecurityManager.format_proxy(raw_proxy)
