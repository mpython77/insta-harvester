"""
Backward-compatible exception re-exports.

In 4.0 all exceptions live in instaharvest.core.exceptions.
This module provides aliases for code that imports from here.
"""
from instaharvest.core.exceptions import (
    InstaHarvestError,
    ConfigError,
    SessionError,
    SessionNotFoundError,
    SessionExpiredError,
    NetworkError,
    RateLimitedError,
    ProfileNotFoundError,
    HtmlStructureChangedError,
    ParseError,
)

# Legacy aliases for code that used the old exception names
InstagramScraperError = InstaHarvestError
PageLoadError = NetworkError
RateLimitError = RateLimitedError
LoginRequiredError = SessionExpiredError
HTMLStructureChangedError = HtmlStructureChangedError


class WebAPIError(NetworkError):
    """Legacy alias kept for backward compatibility."""
    pass
