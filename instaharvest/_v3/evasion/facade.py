"""
:class:`EvasionManager` -- thin facade for the evasion subsystem.

Holds cached adapter instances and exposes them as lazy properties,
following the same pattern as :class:`instaharvest._v3.actions.facade.Actions`.
"""

from __future__ import annotations

from typing import Optional

from instaharvest._v3.core.protocols import Logger
from instaharvest._v3.evasion.captcha_adapter import CaptchaAdapter
from instaharvest._v3.evasion.config import EvasionConfig
from instaharvest._v3.evasion.multi_session import MultiSessionAdapter
from instaharvest._v3.evasion.stealth_adapter import StealthAdapter


class EvasionManager:
    """User-facing entry point for evasion features.

    The facade itself is cheap to construct; the work happens inside
    the individual adapters. Accessing adapters while
    ``config.enabled`` is False is allowed (for introspection), but
    calling methods on them raises :class:`ConfigError`.
    """

    def __init__(self, *, config: EvasionConfig, logger: Logger) -> None:
        self._config = config
        self._logger = logger

        self._stealth: Optional[StealthAdapter] = None
        self._captcha: Optional[CaptchaAdapter] = None
        self._multi_session: Optional[MultiSessionAdapter] = None

    # ------------------------------------------------------------------
    # Sub-namespaces (lazy init)
    # ------------------------------------------------------------------

    @property
    def stealth(self) -> StealthAdapter:
        if self._stealth is None:
            self._stealth = StealthAdapter(
                config=self._config, logger=self._logger
            )
        return self._stealth

    @property
    def captcha(self) -> CaptchaAdapter:
        if self._captcha is None:
            self._captcha = CaptchaAdapter(
                config=self._config, logger=self._logger
            )
        return self._captcha

    @property
    def multi_session(self) -> MultiSessionAdapter:
        if self._multi_session is None:
            self._multi_session = MultiSessionAdapter(
                config=self._config, logger=self._logger
            )
        return self._multi_session

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._config.enabled


__all__ = ["EvasionManager"]
