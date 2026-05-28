"""Adapter for multi-account session rotation.

In 4.0 the legacy session_manager module was removed. Users must provide
a custom session rotation implementation.
"""

from __future__ import annotations

from typing import Any, List, Mapping

from instaharvest.core.exceptions import ConfigError
from instaharvest.core.protocols import Logger
from instaharvest.evasion.config import EvasionConfig


class MultiSessionAdapter:
    """V3 adapter for multi-account session rotation.

    Raises :class:`ConfigError` if called while evasion or
    multi_session is not enabled.
    """

    def __init__(self, *, config: EvasionConfig, logger: Logger) -> None:
        self._config = config
        self._logger = logger
        self._manager: Any = None

    def _guard(self) -> None:
        if not self._config.enabled or not self._config.multi_session_enabled:
            raise ConfigError(
                "MultiSessionAdapter: evasion.enabled and "
                "evasion.multi_session_enabled must both be True "
                "to use multi-session features."
            )

    def _get_manager(self) -> Any:
        raise ConfigError(
            "Legacy session_manager module was removed in 4.0. "
            "MultiSessionAdapter requires a custom session rotation implementation."
        )

    def add_session(self, path: str) -> None:
        """Add a session file to the rotation pool."""
        self._guard()
        self._logger.debug("adding session", path=path)
        manager = self._get_manager()
        manager.add_session(path)

    def get_session(self) -> Mapping[str, Any]:
        """Get the next healthy session data."""
        self._guard()
        self._logger.debug("getting session")
        manager = self._get_manager()
        result = manager.get_session()
        if result is None:
            return {}
        return result

    def rotate(self) -> Mapping[str, Any]:
        """Rotate to the next session and return its data."""
        self._guard()
        self._logger.debug("rotating session")
        manager = self._get_manager()
        result = manager.get_session()
        if result is None:
            return {}
        return result

    def health_report(self) -> List[dict]:
        """Get health status for all sessions in the pool."""
        self._guard()
        self._logger.debug("generating health report")
        manager = self._get_manager()
        try:
            return manager.get_stats()
        except AttributeError:
            return []


__all__ = ["MultiSessionAdapter"]
