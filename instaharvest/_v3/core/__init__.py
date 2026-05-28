"""
Core domain — pure logic, no I/O.

This layer defines:
  * exceptions  — the typed error hierarchy used across the package
  * models      — immutable Pydantic data classes returned to users
  * protocols   — interfaces that infrastructure must implement

``core`` does not import from ``infrastructure``, ``scrapers``, or
``facade``. Its only dependency inside the package is ``config``.
"""

from instaharvest._v3.core.exceptions import (
    ConfigError,
    HtmlStructureChangedError,
    InstaHarvestError,
    NetworkError,
    ParseError,
    ProfileNotFoundError,
    RateLimitedError,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
)
from instaharvest._v3.core.models import BioLink, BusinessInfo, Profile
from instaharvest._v3.core.protocols import (
    BrowserSession,
    HttpClient,
    HttpResponse,
    Logger,
    SessionStore,
)

__all__ = [
    # Exceptions
    "InstaHarvestError",
    "ConfigError",
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "NetworkError",
    "RateLimitedError",
    "ProfileNotFoundError",
    "HtmlStructureChangedError",
    "ParseError",
    # Models
    "Profile",
    "BioLink",
    "BusinessInfo",
    # Protocols
    "HttpClient",
    "HttpResponse",
    "BrowserSession",
    "SessionStore",
    "Logger",
]
