"""
Abstract base for v3 scrapers.

Owns the cross-cutting concerns that every scraper needs:

    * navigation with login detection and rate-limit detection
    * pacing between requests (configurable jitter)
    * cooldown-and-retry on rate-limit signals
    * uniform structured logging

A concrete scraper implements ``scrape(...)`` and uses
:meth:`navigate` instead of touching the browser session directly.
That keeps detection logic in *one* place and unit-testable in
isolation: feed the scraper a fake ``BrowserSession`` and verify
that it raises the right exception, retries the right number of
times, etc.

Sync only for now. Async will share this same module by
parameterising on the protocols (``AsyncHttpClient`` /
``AsyncBrowserSession``); no copy-paste is planned.
"""

from __future__ import annotations

import random
import time
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.config.selectors import ProfileSelectors
from instaharvest.core.exceptions import (
    NetworkError,
    RateLimitedError,
    SessionExpiredError,
)
from instaharvest.core.protocols import BrowserSession, Logger


class NavigationOutcome(Enum):
    """High-level result of a navigation attempt."""

    OK = "ok"
    LOGIN_REQUIRED = "login_required"
    RATE_LIMITED = "rate_limited"


@dataclass(frozen=True)
class _NavResult:
    outcome: NavigationOutcome
    url: str


class AbstractScraper(ABC):
    """Common scraper functionality.

    Subclasses receive infrastructure through the constructor and
    use it via the protocols defined in ``core.protocols``. They
    do **not** create or own the browser/session/HTTP client.
    """

    def __init__(
        self,
        *,
        browser: BrowserSession,
        logger: Logger,
        rate_limit: RateLimitConfig,
        selectors: ProfileSelectors,
    ) -> None:
        self._browser = browser
        self._logger = logger
        self._rate_limit = rate_limit
        self._selectors = selectors

        # Pacing state
        self._last_request_at: float = 0.0

    # ----- public helpers for subclasses ----------------------------------

    def navigate(self, url: str) -> _NavResult:
        """Go to ``url``, classifying the resulting page.

        Raises:
            RateLimitedError: cooldown_max_retries exhausted.
            SessionExpiredError: Instagram redirected to login and we
                cannot recover by visiting the home page.
            NetworkError: underlying browser navigation kept failing.

        Returns:
            ``_NavResult(NavigationOutcome.OK, final_url)`` on success.
        """
        rate_limit_attempts = 0

        while True:
            self._respect_pacing()

            try:
                self._browser.goto(url)
            except Exception as exc:
                raise NetworkError(f"navigation to {url!r} failed", url=url) from exc

            current_url = self._browser.page_url()
            content = self._safe_page_content()

            if self._is_rate_limited(current_url, content):
                rate_limit_attempts += 1
                self._logger.warning(
                    "rate-limit detected",
                    url=current_url,
                    attempt=rate_limit_attempts,
                    max_attempts=self._rate_limit.cooldown_max_retries,
                )
                if rate_limit_attempts > self._rate_limit.cooldown_max_retries:
                    raise RateLimitedError(
                        "Instagram rate-limit cooldown exhausted",
                        cooldown_seconds=self._rate_limit.cooldown_seconds,
                    )
                time.sleep(self._rate_limit.cooldown_seconds)
                continue

            if self._is_login_page(current_url, content):
                self._logger.warning("login page detected", url=current_url)
                raise SessionExpiredError(
                    f"redirected to login page from {url!r}; "
                    "session is invalid or expired"
                )

            return _NavResult(NavigationOutcome.OK, current_url)

    # ----- internals ------------------------------------------------------

    def _respect_pacing(self) -> None:
        """Sleep just enough to honour the configured request jitter."""
        if self._rate_limit.request_delay_max <= 0:
            self._last_request_at = time.monotonic()
            return

        delay = random.uniform(
            self._rate_limit.request_delay_min,
            self._rate_limit.request_delay_max,
        )
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_at = time.monotonic()

    def _safe_page_content(self) -> str:
        try:
            return self._browser.page_content()
        except Exception as exc:
            # Content read can fail mid-navigation; treat as empty so the
            # outcome classifiers fall back to URL-based detection.
            self._logger.debug("page_content unavailable", error=str(exc))
            return ""

    def _is_rate_limited(self, url: str, content: str) -> bool:
        for indicator in self._selectors.rate_limit_indicators:
            if indicator in url or indicator in content:
                return True
        return False

    def _is_login_page(self, url: str, content: str) -> bool:
        for indicator in self._selectors.login_required_indicators:
            if indicator in url:
                return True
        # Heuristic: bare login forms contain a password field.
        # The browser adapter's ``page_content`` returns the rendered HTML.
        return 'type="password"' in content
