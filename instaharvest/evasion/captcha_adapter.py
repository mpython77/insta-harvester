"""Adapter for CAPTCHA detection and solving.

In 4.0 the legacy captcha_solver module was removed. Users must provide
a custom CAPTCHA provider implementation.
"""

from __future__ import annotations

from typing import Any

from instaharvest.core.exceptions import ConfigError
from instaharvest.core.protocols import Logger
from instaharvest.evasion.config import EvasionConfig


class CaptchaAdapter:
    """V3 adapter for CAPTCHA detection and solving.

    Raises :class:`ConfigError` if called while evasion is not
    enabled or no captcha_api_key is configured.
    """

    def __init__(self, *, config: EvasionConfig, logger: Logger) -> None:
        self._config = config
        self._logger = logger
        self._solver: Any = None

    def _guard(self) -> None:
        if not self._config.enabled or not self._config.captcha_api_key:
            raise ConfigError(
                "CaptchaAdapter: evasion.enabled must be True and "
                "evasion.captcha_api_key must be set to use CAPTCHA features."
            )

    def _get_solver(self) -> Any:
        raise ConfigError(
            "Legacy captcha_solver module was removed in 4.0. "
            "CaptchaAdapter requires a custom CAPTCHA provider implementation."
        )

    def detect(self, page: Any) -> bool:
        """Detect whether a CAPTCHA is present on the page."""
        self._guard()
        self._logger.debug("detecting captcha")
        solver = self._get_solver()
        return solver.detect_captcha(page)

    def solve(self, page: Any) -> bool:
        """Attempt to solve a CAPTCHA on the page."""
        self._guard()
        self._logger.debug("solving captcha")
        solver = self._get_solver()
        return solver.solve(page)


__all__ = ["CaptchaAdapter"]
