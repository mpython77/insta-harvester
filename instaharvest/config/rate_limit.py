"""Rate-limit configuration.

Owned by: ``scrapers`` (each scraper enforces its own pacing).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for client-side request pacing.

    Two layers:
      * Per-request jitter (``request_delay_*``): a uniform random
        delay between consecutive requests.
      * Cooldown on detection (``cooldown_*``): if Instagram returns
        a rate-limit signal, the scraper sleeps for ``cooldown_seconds``
        and retries up to ``cooldown_max_retries`` times.
    """

    request_delay_min: float = 1.0
    request_delay_max: float = 3.0

    cooldown_seconds: float = 300.0
    cooldown_max_retries: int = 2

    def __post_init__(self) -> None:
        if self.request_delay_min < 0 or self.request_delay_max < 0:
            raise ValueError("request delays must be >= 0")
        if self.request_delay_max < self.request_delay_min:
            raise ValueError("request_delay_max must be >= request_delay_min")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        if self.cooldown_max_retries < 0:
            raise ValueError("cooldown_max_retries must be >= 0")
