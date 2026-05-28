"""Adapter for browser-level stealth patches.

In 4.0 the legacy stealth module was removed. Users must provide
a custom stealth implementation.
"""

from __future__ import annotations

from typing import Any

from instaharvest.core.exceptions import ConfigError
from instaharvest.core.protocols import Logger
from instaharvest.evasion.config import EvasionConfig


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
        raise ConfigError(
            "Legacy stealth module was removed in 4.0. "
            "StealthAdapter requires a custom stealth implementation."
        )

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
