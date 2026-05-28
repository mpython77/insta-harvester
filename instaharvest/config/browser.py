"""Browser configuration.

Owned by: ``infrastructure.browser.PlaywrightBrowserSession``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class BrowserConfig:
    """Configuration for the Playwright browser session.

    Frozen so that scrapers cannot mutate browser settings at runtime.
    Build a new ``Settings`` if you need different browser behaviour.
    """

    # Launch
    headless: bool = True
    channel: str = "chrome"  # 'chrome' (system) or 'chromium' (bundled)
    executable_path: Optional[str] = None
    extra_launch_args: List[str] = field(default_factory=list)

    # Context
    viewport_width: int = 1280
    viewport_height: int = 720
    locale: str = "en-US"
    user_agent: Optional[str] = None  # None => use Playwright default

    # Timeouts (milliseconds)
    default_timeout_ms: int = 30_000
    navigation_timeout_ms: int = 60_000

    # Behaviour
    block_resources: tuple = ("font", "media")  # speeds up scraping
    accept_downloads: bool = False

    def __post_init__(self) -> None:
        if self.viewport_width <= 0 or self.viewport_height <= 0:
            raise ValueError("viewport dimensions must be positive")
        if self.default_timeout_ms <= 0 or self.navigation_timeout_ms <= 0:
            raise ValueError("timeouts must be positive")
        if self.channel not in {"chrome", "chromium", "msedge"}:
            raise ValueError(
                f"unsupported channel {self.channel!r}; "
                "expected one of 'chrome', 'chromium', 'msedge'"
            )
