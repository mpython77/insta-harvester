"""
Legacy ``InstaHarvest`` central-hub stub.

.. deprecated:: 2.18

    The original ``core.InstaHarvest`` was documented as the central
    hub but was never wired into any scraper — it only constructed a
    ``ProxyManager`` and a ``SmartLogger``. The real composition root
    now lives in :mod:`instaharvest._v3.facade` (re-exported as
    ``instaharvest._v3.InstaHarvest``).

    This module is kept only so that ``from instaharvest import
    InstaHarvest`` continues to import. Each instantiation emits a
    :class:`DeprecationWarning`. The class will be removed in 3.0.0.

Migration::

    # Old (still works, deprecated)
    from instaharvest import InstaHarvest, ScraperConfig
    hub = InstaHarvest(ScraperConfig(...))
    proxy = hub.get_proxy()

    # New
    from instaharvest._v3 import InstaHarvest, Settings
    with InstaHarvest(Settings.default()) as ih:
        profile = ih.profile.scrape("instagram")
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Optional

from .config import ScraperConfig
from .logging_config import SmartLogger
from .proxy import ProxyManager


_DEPRECATION_MSG = (
    "instaharvest.core.InstaHarvest is deprecated and will be removed in "
    "3.0.0. Use instaharvest._v3.InstaHarvest with instaharvest._v3.Settings "
    "instead. See ARCHITECTURE.md for the migration guide."
)


class InstaHarvest:
    """Deprecated legacy hub. See module docstring."""

    def __init__(self, config: Optional[ScraperConfig] = None) -> None:
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)

        self.config = config or ScraperConfig()
        self.logger = SmartLogger.from_config(self.config, name="InstaHarvest")
        self.proxy_manager = ProxyManager.from_config(self.config, self.logger)

        self.logger.info(
            "InstaHarvest initialized (legacy)",
            proxies=len(self.proxy_manager._proxy_pool) if self.proxy_manager else 0,
            stealth=self.config.enable_stealth,
        )

    # ----- Proxy passthroughs ---------------------------------------------

    def get_proxy(self) -> Optional[Dict[str, str]]:
        return self.proxy_manager.get_for_playwright()

    def get_curl_proxy(self) -> Optional[str]:
        return self.proxy_manager.get_for_curl()

    def check_proxies(self, verbose: bool = True) -> Dict[str, Any]:
        return self.proxy_manager.check_all_proxies(verbose=verbose)

    def proxy_stats(self) -> Dict[str, Any]:
        return self.proxy_manager.get_stats()

    # ----- Config passthroughs --------------------------------------------

    def update_config(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.debug("Config updated", key=key, value=value)
            else:
                self.logger.warning("Unknown config key", key=key)

    # ----- Properties -----------------------------------------------------

    @property
    def has_proxies(self) -> bool:
        return self.proxy_manager.has_proxies

    @property
    def healthy_proxy_count(self) -> int:
        return self.proxy_manager.healthy_count

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"InstaHarvest(legacy, proxies={self.healthy_proxy_count}, "
            f"stealth={self.config.enable_stealth})"
        )
