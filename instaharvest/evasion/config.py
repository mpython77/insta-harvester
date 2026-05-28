"""Evasion configuration.

Opt-in and disabled by default. Sub-features (stealth, CAPTCHA,
multi-session) can only be enabled when the top-level ``enabled``
flag is True -- same validation pattern as :class:`StealthConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvasionConfig:
    """Configuration for the evasion subsystem.

    Default: everything off. Enable the top-level flag first,
    then turn on individual sub-features as needed.
    """

    enabled: bool = False
    stealth_enabled: bool = False
    captcha_api_key: Optional[str] = None
    captcha_provider: str = "2captcha"
    multi_session_enabled: bool = False
    session_rotation: str = "round_robin"

    def __post_init__(self) -> None:
        if not self.enabled:
            any_on = (
                self.stealth_enabled
                or self.captcha_api_key is not None
                or self.multi_session_enabled
            )
            if any_on:
                raise ValueError(
                    "EvasionConfig: sub-features set but enabled=False. "
                    "Set enabled=True or unset the sub-features."
                )


__all__ = ["EvasionConfig"]
