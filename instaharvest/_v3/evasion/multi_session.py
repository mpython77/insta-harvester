"""Adapter wrapping the legacy :mod:`instaharvest.session_manager` module.

Provides a clean v3 interface while delegating to the existing
``SessionManager`` implementation under the hood.
"""

from __future__ import annotations

from typing import Any, List, Mapping

from instaharvest._v3.core.exceptions import ConfigError
from instaharvest._v3.core.protocols import Logger
from instaharvest._v3.evasion.config import EvasionConfig


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
        """Lazily instantiate the legacy SessionManager."""
        if self._manager is None:
            from instaharvest.session_manager import (  # noqa: WPS433
                SessionManager,
                SessionRotationStrategy,
            )

            strategy = SessionRotationStrategy(self._config.session_rotation)
            self._manager = SessionManager(rotation=strategy)
        return self._manager

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
        """Rotate to the next session and return its data.

        Note: In the legacy SessionManager, rotation is implicit in
        get_session() (it advances the internal pointer based on the
        configured rotation strategy). This method is a semantic alias
        provided for API clarity.
        """
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
