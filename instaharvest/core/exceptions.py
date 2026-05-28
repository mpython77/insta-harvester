"""
Typed exception hierarchy for v3.

Every error raised out of v3 is a subclass of ``InstaHarvestError``.
Callers can catch the base type once and dispatch on the subclass,
or catch a specific subclass for fine-grained handling.

Design rules:
    * Each exception carries enough structured context (attributes)
      to be useful in logs and retries; do not stuff context only
      into the message string.
    * No exception is raised with ``except Exception: raise X(str(e))``
      — preserve the cause via ``raise X(...) from e``.
"""

from __future__ import annotations

from typing import Optional


class InstaHarvestError(Exception):
    """Base for every error v3 raises."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigError(InstaHarvestError):
    """User-supplied configuration is invalid."""


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionError(InstaHarvestError):
    """Base for session-related errors."""


class SessionNotFoundError(SessionError):
    """No session file was found at the expected location."""

    def __init__(self, path: str):
        super().__init__(f"Session file not found: {path}")
        self.path = path


class SessionExpiredError(SessionError):
    """The loaded session is no longer valid (Instagram redirected to login)."""


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------


class NetworkError(InstaHarvestError):
    """Generic transport-level failure (timeout, DNS, TLS)."""

    def __init__(self, message: str, *, url: Optional[str] = None):
        super().__init__(message)
        self.url = url


class RateLimitedError(InstaHarvestError):
    """Instagram returned a rate-limit signal.

    ``cooldown_seconds`` is the suggested back-off before retrying.
    """

    def __init__(self, message: str, *, cooldown_seconds: float):
        super().__init__(message)
        self.cooldown_seconds = cooldown_seconds


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class ProfileNotFoundError(InstaHarvestError):
    """The requested Instagram profile does not exist."""

    def __init__(self, username: str):
        super().__init__(f"Profile not found: @{username}")
        self.username = username


class HtmlStructureChangedError(InstaHarvestError):
    """An expected element is missing — Instagram likely changed their DOM.

    Carries enough context to file a useful bug report.
    """

    def __init__(
        self,
        *,
        element: str,
        selector: str,
        url: Optional[str] = None,
        snapshot_path: Optional[str] = None,
    ):
        msg = (
            f"HTML structure changed: element {element!r} "
            f"not found via selector {selector!r}"
        )
        super().__init__(msg)
        self.element = element
        self.selector = selector
        self.url = url
        self.snapshot_path = snapshot_path


class ParseError(InstaHarvestError):
    """Response was reachable but its content could not be parsed."""

    def __init__(self, message: str, *, source: Optional[str] = None):
        super().__init__(message)
        self.source = source
