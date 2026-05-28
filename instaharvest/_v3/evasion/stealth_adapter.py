"""Adapter wrapping the legacy :mod:`instaharvest.stealth` module.

Provides a clean v3 interface while delegating to the existing
``StealthManager`` implementation under the hood.
"""

from __future__ import annotations

from typing import Any

from instaharvest._v3.core.exceptions import ConfigError
from instaharvest._v3.core.protocols import Logger
from instaharvest._v3.evasion.config import EvasionConfig


class StealthAdapter:
    """V3 adapter for browser-level stealth patches.

    Raises :class:`ConfigError` if called while evasion or stealth
    is not enabled.
    """

    def __init__(self, *, config: EvasionConfig, logger: Logger) -> None:
        self._config = config
        self._logger = logger
        self._manager: Any = None

    def _guard(self) -> None:
        if not self._config.enabled or not self._config.stealth_enabled:
            raise ConfigError(
                "StealthAdapter: evasion.enabled and evasion.stealth_enabled "
                "must both be True to use stealth features."
            )

    def _get_manager(self) -> Any:
        """Lazily instantiate and cache the legacy StealthManager."""
        if self._manager is None:
            from instaharvest.stealth import StealthManager  # noqa: WPS433
            from instaharvest.config import ScraperConfig  # noqa: WPS433

            # The legacy StealthManager requires a ScraperConfig instance.
            # We pass a default one since v3 stealth configuration is
            # managed via EvasionConfig; the legacy config controls
            # browser-level defaults that are acceptable as-is.
            self._manager = StealthManager(
                config=ScraperConfig(),
                logger=None,
            )
        return self._manager

    def apply_to_context(self, context: Any) -> None:
        """Apply stealth patches to a browser context."""
        self._guard()
        self._logger.debug("applying stealth to context")
        manager = self._get_manager()
        manager.apply_context_stealth(context)

    def apply_to_page(self, page: Any) -> None:
        """Apply stealth patches to a browser page."""
        self._guard()
        self._logger.debug("applying stealth to page")
        manager = self._get_manager()
        manager.apply_page_stealth(page)


__all__ = ["StealthAdapter"]
