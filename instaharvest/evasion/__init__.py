"""
Evasion -- opt-in stealth, CAPTCHA, and multi-session management.

This package is **opt-in**. Default: disabled. Enable via Settings:

    from dataclasses import replace
    from instaharvest.evasion.config import EvasionConfig

    settings = replace(settings, evasion=EvasionConfig(
        enabled=True,
        stealth_enabled=True,
    ))

All adapters raise ConfigError if called while disabled.
"""

from instaharvest.evasion.facade import EvasionManager
from instaharvest.evasion.stealth_adapter import StealthAdapter
from instaharvest.evasion.captcha_adapter import CaptchaAdapter
from instaharvest.evasion.multi_session import MultiSessionAdapter

__all__ = ["EvasionManager", "StealthAdapter", "CaptchaAdapter", "MultiSessionAdapter"]
