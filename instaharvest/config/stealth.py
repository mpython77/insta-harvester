"""Stealth / anti-detection configuration.

Owned by: ``infrastructure.browser`` (when stealth is enabled).

NOTE: Stealth in v3 is opt-in and disabled by default. The legal
and ethical posture of using fingerprint-masking and CAPTCHA
bypass is the operator's responsibility. See SECURITY.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StealthConfig:
    """Configuration for browser-level anti-detection patches.

    Default: everything off. The legacy ``stealth.py`` module
    still implements the actual patches; v3 uses it as a leaf
    dependency until phase 5 of the migration.
    """

    enabled: bool = False
    mask_webgl: bool = False
    mask_canvas: bool = False
    mask_audio: bool = False

    # Human-behaviour simulation
    humanize_mouse: bool = False
    humanize_typing: bool = False
    humanize_scroll: bool = False

    def __post_init__(self) -> None:
        # If stealth is disabled, no submasks should be on; warn loudly.
        if not self.enabled:
            any_on = (
                self.mask_webgl
                or self.mask_canvas
                or self.mask_audio
                or self.humanize_mouse
                or self.humanize_typing
                or self.humanize_scroll
            )
            if any_on:
                raise ValueError(
                    "StealthConfig: submasks set but enabled=False. "
                    "Set enabled=True or unset the submasks."
                )
