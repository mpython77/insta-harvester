"""
SocialActions — follow and unfollow.

The core of the action namespace. Both methods follow the same shape:

  1. Resolve ``username`` to a ``user_id`` via the profile API
     (cached per :class:`SocialActions` instance).
  2. Optionally short-circuit on the current friendship status — a
     ``follow`` on someone we already follow returns
     :attr:`ActionStatus.ALREADY_DONE` without hitting the
     mutation endpoint.
  3. POST ``/api/v1/friendships/create/{user_id}/`` (or
     ``destroy/``).

The ``check_status`` parameter is on by default because the
short-circuit costs one read but saves one write — and Instagram's
write quota is the scarce resource here.
"""

from __future__ import annotations

import json
from typing import Optional

from instaharvest.actions._base import _ActionBase
from instaharvest.core.exceptions import NetworkError, ParseError
from instaharvest.core.models import ActionResult, ActionStatus
from instaharvest.scrapers.followers import FollowersScraper


_FOLLOW_URL = "https://www.instagram.com/api/v1/friendships/create/{user_id}/"
_UNFOLLOW_URL = "https://www.instagram.com/api/v1/friendships/destroy/{user_id}/"

_PROFILE_API = (
    "https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
)


class SocialActions(_ActionBase):
    """Follow / unfollow as :class:`ActionResult`-returning methods.

    Construct via :attr:`Actions.social`; direct instantiation is
    supported for tests and infrastructure injection.
    """

    def __init__(
        self,
        *,
        followers: FollowersScraper,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._followers = followers
        self._user_id_cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def follow(
        self,
        username: str,
        *,
        check_status: bool = True,
    ) -> ActionResult:
        """Follow ``username``.

        Returns:
            :class:`ActionStatus.OK` on success,
            :class:`ActionStatus.ALREADY_DONE` if we already follow,
            :class:`ActionStatus.DRY_RUN` if dry-run is on,
            :class:`ActionStatus.ERROR` otherwise.
        """
        username = _normalise_username(username)
        self._require_enabled("follow")

        user_id = self._resolve_user_id(username)
        if user_id is None:
            return self._error("follow", username, "could not resolve user_id")

        if check_status:
            try:
                status = self._followers.friendship_status(user_id)
            except (NetworkError, ParseError) as exc:
                self._logger.debug(
                    "friendship status pre-check failed; proceeding",
                    error=str(exc),
                )
            else:
                if status.is_following:
                    return self._already_done(
                        "follow", username, "already following"
                    )

        return self._perform(
            action="follow",
            target=username,
            api_call=lambda: self._http.post(
                _FOLLOW_URL.format(user_id=user_id),
                headers=self._action_headers(),
            ),
            success_predicate=_friendship_create_ok,
        )

    def unfollow(
        self,
        username: str,
        *,
        check_status: bool = True,
    ) -> ActionResult:
        """Unfollow ``username``.

        Returns:
            :class:`ActionStatus.OK` on success,
            :class:`ActionStatus.NOT_APPLICABLE` if we were not
            following to begin with,
            :class:`ActionStatus.DRY_RUN` if dry-run is on,
            :class:`ActionStatus.ERROR` otherwise.
        """
        username = _normalise_username(username)
        self._require_enabled("unfollow")

        user_id = self._resolve_user_id(username)
        if user_id is None:
            return self._error("unfollow", username, "could not resolve user_id")

        if check_status:
            try:
                status = self._followers.friendship_status(user_id)
            except (NetworkError, ParseError) as exc:
                self._logger.debug(
                    "friendship status pre-check failed; proceeding",
                    error=str(exc),
                )
            else:
                if not status.is_following:
                    return self._not_applicable(
                        "unfollow", username, "not following"
                    )

        return self._perform(
            action="unfollow",
            target=username,
            api_call=lambda: self._http.post(
                _UNFOLLOW_URL.format(user_id=user_id),
                headers=self._action_headers(),
            ),
            success_predicate=_friendship_destroy_ok,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_user_id(self, username: str) -> Optional[str]:
        """Resolve ``username`` to its numeric user id.

        Cached on this instance so a follow loop does not re-fetch
        the profile API for each call. Cache invalidation is the
        caller's job (rebuild the :class:`InstaHarvest` facade if
        Instagram renames an account mid-run).
        """
        cached = self._user_id_cache.get(username)
        if cached is not None:
            return cached

        url = _PROFILE_API.format(username=username)
        try:
            resp = self._http.get(url, headers=self._action_headers())
        except NetworkError:
            return None
        if resp.status_code >= 400:
            return None
        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError):
            return None

        user = (
            payload.get("data", {}).get("user")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(user, dict):
            return None
        user_id = user.get("id") or user.get("pk")
        if user_id is None:
            return None
        user_id = str(user_id)
        self._user_id_cache[username] = user_id
        return user_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


import re

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{1,30}$")


def _normalise_username(raw: str) -> str:
    cleaned = raw.strip().lstrip("@")
    if not _USERNAME_RE.match(cleaned):
        raise ValueError(f"invalid Instagram username: {raw!r}")
    return cleaned


def _friendship_create_ok(payload) -> bool:
    """Instagram returns ``{"status": "ok", "friendship_status": {...}}``.

    A few historical variants return only ``status: ok`` with no
    nested object; treat both as success.
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("status") != "ok":
        return False
    fs = payload.get("friendship_status")
    if fs is None:
        return True
    if not isinstance(fs, dict):
        return False
    # ``following`` flips True after a successful create. If the API
    # returned us a status that contradicts the action, surface it as
    # an error so callers do not silently trust a no-op.
    return bool(fs.get("following", True))


def _friendship_destroy_ok(payload) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("status") != "ok":
        return False
    fs = payload.get("friendship_status")
    if fs is None:
        return True
    if not isinstance(fs, dict):
        return False
    return not bool(fs.get("following", False))


__all__ = ["SocialActions"]
