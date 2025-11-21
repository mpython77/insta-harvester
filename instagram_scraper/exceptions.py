"""
Instagram Scraper - Professional grade scraping library
Custom exceptions for better error handling
"""


class InstagramScraperError(Exception):
    """Base exception for Instagram scraper"""
    pass


class SessionNotFoundError(InstagramScraperError):
    """Session file not found"""
    pass


class ProfileNotFoundError(InstagramScraperError):
    """Instagram profile not found"""
    pass


class HTMLStructureChangedError(InstagramScraperError):
    """Instagram HTML structure has changed"""

    def __init__(self, element_name: str, selector: str, message: str = None):
        self.element_name = element_name
        self.selector = selector
        self.message = message or f"HTML structure changed for '{element_name}'. Selector '{selector}' no longer works."
        super().__init__(self.message)


class PageLoadError(InstagramScraperError):
    """Page failed to load"""
    pass


class RateLimitError(InstagramScraperError):
    """Instagram rate limit reached"""
    pass


class LoginRequiredError(InstagramScraperError):
    """Login/session expired"""
    pass
