"""Configuration for write/mutation operations (follow, unfollow, DM).

Owned by: ``instaharvest.actions``.

Design:
    * Default is **off**. Users must explicitly opt in.
    * Default is **dry-run** even when on. Users must explicitly opt
      out of dry-run to make real Instagram API calls.

This two-step opt-in is intentional. The legacy library exposed
``manager.follow(username)`` as a one-line call with no warning, and
plenty of users discovered the cost (account bans, ToS strikes) the
hard way. v3 makes you write::

    from dataclasses import replace

    settings = replace(
        settings,
        actions=replace(settings.actions, enabled=True, dry_run=False),
    )

before any state-mutating call will actually hit Instagram.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionsConfig:
    """Opt-in switches for the ``actions`` namespace.

    ``enabled``
        When ``False`` (default), every method on ``ih.actions`` raises
        :class:`ConfigError` on first call. The user has to consciously
        flip this to use any write operation.

    ``dry_run``
        When ``True`` (default), action methods log what they *would*
        do and return :attr:`ActionStatus.DRY_RUN`, without actually
        calling Instagram. Useful for testing pipelines, debugging
        rate-limit logic, and demonstrating to a reviewer what an
        action script would touch.

    ``min_delay_seconds`` / ``max_delay_seconds``
        Random pacing between actions, in seconds. Defaults are
        deliberately conservative: 30s..60s. Users who lower these
        are responsible for the rate-limit consequences.

    ``max_consecutive_errors``
        Hard ceiling on consecutive ``ERROR`` statuses before the
        action namespace stops accepting calls. Prevents a hot loop
        on a permanently-broken endpoint or an account that has been
        rate-limited.
    """

    enabled: bool = False
    dry_run: bool = True

    min_delay_seconds: float = 30.0
    max_delay_seconds: float = 60.0

    max_consecutive_errors: int = 5

    def __post_init__(self) -> None:
        if self.min_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("delay seconds must be >= 0")
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError("max_delay_seconds must be >= min_delay_seconds")
        if self.max_consecutive_errors < 1:
            raise ValueError("max_consecutive_errors must be >= 1")
