"""
:class:`Actions` — the thin facade users see at ``ih.actions``.

Holds two cached sub-namespaces (:class:`SocialActions`,
:class:`MessagingActions`) and exposes pass-through convenience
methods for the most common operations so users do not have to write
``ih.actions.social.follow(x)`` when ``ih.actions.follow(x)`` reads
just as well.
"""

from __future__ import annotations

from typing import Optional

from instaharvest._v3.actions.messaging import MessagingActions
from instaharvest._v3.actions.social import SocialActions
from instaharvest._v3.config.actions import ActionsConfig
from instaharvest._v3.core.exceptions import ConfigError
from instaharvest._v3.core.models import ActionResult
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers.followers import FollowersScraper


class Actions:
    """User-facing entry point for write operations.

    The facade itself is cheap to construct; the work happens inside
    :class:`SocialActions` / :class:`MessagingActions`. Accessing
    those sub-namespaces while ``settings.actions.enabled`` is False
    is allowed (so users can introspect the API surface), but any
    actual call on them raises :class:`ConfigError`.
    """

    def __init__(
        self,
        *,
        http: HttpClient,
        logger: Logger,
        config: ActionsConfig,
        followers: FollowersScraper,
    ) -> None:
        self._http = http
        self._logger = logger
        self._config = config
        self._followers = followers

        self._social: Optional[SocialActions] = None
        self._messaging: Optional[MessagingActions] = None

    # ------------------------------------------------------------------
    # Sub-namespaces
    # ------------------------------------------------------------------

    @property
    def social(self) -> SocialActions:
        if self._social is None:
            self._social = SocialActions(
                http=self._http,
                logger=self._logger,
                config=self._config,
                followers=self._followers,
            )
        return self._social

    @property
    def messaging(self) -> MessagingActions:
        if self._messaging is None:
            self._messaging = MessagingActions(
                http=self._http,
                logger=self._logger,
                config=self._config,
            )
        return self._messaging

    # ------------------------------------------------------------------
    # Convenience pass-throughs
    # ------------------------------------------------------------------

    def follow(self, username: str, *, check_status: bool = True) -> ActionResult:
        return self.social.follow(username, check_status=check_status)

    def unfollow(self, username: str, *, check_status: bool = True) -> ActionResult:
        return self.social.unfollow(username, check_status=check_status)

    def send_message(self, username: str, text: str) -> ActionResult:
        return self.messaging.send_message(username, text)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def dry_run(self) -> bool:
        return self._config.dry_run


__all__ = ["Actions"]
