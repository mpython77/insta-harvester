"""Composed top-level Settings.

This is the only object users hand to ``InstaHarvest``. It owns
every subsystem config and nothing else. Sub-configs are immutable
(frozen dataclasses), so code that wants different settings must
build a new ``Settings`` rather than reaching in to mutate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from instaharvest.config.actions import ActionsConfig
from instaharvest.config.browser import BrowserConfig
from instaharvest.config.network import NetworkConfig
from instaharvest.config.stealth import StealthConfig
from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.config.output import OutputConfig
from instaharvest.config.selectors import SelectorConfig
from instaharvest.evasion.config import EvasionConfig


@dataclass(frozen=True)
class Settings:
    """Composed configuration for InstaHarvest.

    Construct with ``Settings.default()`` for a sensible starting
    point, then build a customised copy with ``dataclasses.replace``::

        from dataclasses import replace
        from instaharvest import Settings

        s = Settings.default()
        s = replace(s, browser=replace(s.browser, headless=False))
    """

    browser: BrowserConfig = field(default_factory=BrowserConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    stealth: StealthConfig = field(default_factory=StealthConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    selectors: SelectorConfig = field(default_factory=SelectorConfig)
    actions: ActionsConfig = field(default_factory=ActionsConfig)
    evasion: EvasionConfig = field(default_factory=EvasionConfig)

    @classmethod
    def default(cls) -> "Settings":
        """Sensible defaults for production use.

        Headless browser, no proxy, no stealth, conservative pacing.
        """
        return cls()
