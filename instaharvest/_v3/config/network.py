"""Network configuration.

Owned by: ``infrastructure.http.CurlHttpClient``.

Covers proxy, timeouts, retries. Browser-side networking goes
through Playwright with its own settings (see ``BrowserConfig``);
this config governs the *non-browser* HTTP path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class NetworkConfig:
    """Configuration for the HTTP client."""

    # Proxy
    proxy_url: Optional[str] = None  # "http://user:pass@host:port"
    proxy_pool: tuple = ()  # rotated round-robin if non-empty
    proxy_max_failures: int = 3  # remove proxy after N consecutive errors

    # Timeouts (seconds)
    connect_timeout: float = 10.0
    read_timeout: float = 30.0

    # Retries
    max_retries: int = 3
    retry_backoff_base: float = 1.0  # exponential: base * 2^attempt
    retry_backoff_cap: float = 30.0

    # TLS impersonation profile (passed to curl_cffi)
    impersonate: str = "chrome120"

    def __post_init__(self) -> None:
        if self.connect_timeout <= 0 or self.read_timeout <= 0:
            raise ValueError("timeouts must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry_backoff_base <= 0 or self.retry_backoff_cap <= 0:
            raise ValueError("backoff values must be positive")
