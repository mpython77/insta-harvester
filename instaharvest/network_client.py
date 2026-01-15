from curl_cffi import requests
from typing import Dict, Optional, List, Any
import logging
from .security import SecurityManager

class NetworkClient:
    """
    Advanced HTTP Client using curl_cffi for TLS Fingerprint Impersonation.
    Designed to work in Hybrid Mode with Playwright.
    """
    
    def __init__(self, proxy: Optional[str] = None):
        self.logger = logging.getLogger("NetworkClient")
        self.session = requests.Session(impersonate="chrome120")
        self.proxy = proxy
        
        # Initial Setup
        self._setup_headers()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
            
    def _setup_headers(self):
        """Set common browser-like headers"""
        ua = SecurityManager.get_random_user_agent()
        self.session.headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }

    def set_cookies(self, cookies: List[Dict]):
        """
        Import cookies from Playwright
        Args:
            cookies: List of dicts from browser.context.cookies()
        """
        for cookie in cookies:
            self.session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie['domain'],
                path=cookie['path']
            )
        self.logger.info(f"🍪 Imported {len(cookies)} cookies from Browser.")

    def get(self, url: str, **kwargs) -> requests.Response:
        """Execute GET request with impersonation"""
        try:
            return self.session.get(url, **kwargs)
        except Exception as e:
            self.logger.error(f"GET Request failed: {e}")
            raise

    def post(self, url: str, data: Any = None, json: Any = None, **kwargs) -> requests.Response:
        """Execute POST request with impersonation"""
        try:
            return self.session.post(url, data=data, json=json, **kwargs)
        except Exception as e:
            self.logger.error(f"POST Request failed: {e}")
            raise

    def download_media(self, url: str, save_path: str):
        """High-speed media download"""
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.logger.info(f"💾 Downloaded: {save_path}")
            return True
        except Exception as e:
            self.logger.error(f"Download failed: {url} -> {e}")
            return False
