"""Adapter wrapping the legacy :mod:`instaharvest.captcha_solver` module.

Provides a clean v3 interface while delegating to the existing
``CaptchaSolver`` implementation under the hood.
"""

from __future__ import annotations

from typing import Any

from instaharvest._v3.core.exceptions import ConfigError
from instaharvest._v3.core.protocols import Logger
from instaharvest._v3.evasion.config import EvasionConfig


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
        """Lazily instantiate the legacy CaptchaSolver."""
        if self._solver is None:
            from instaharvest.captcha_solver import CaptchaSolver  # noqa: WPS433

            self._solver = CaptchaSolver(
                api_key=self._config.captcha_api_key,
                provider=self._config.captcha_provider,
            )
        return self._solver

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
