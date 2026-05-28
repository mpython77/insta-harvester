"""
MessagingActions — direct messages.

Single public method: :meth:`send_message`. Posts to Instagram's
``direct_v2/threads/broadcast/text/`` endpoint. The legacy
``MessageManager`` clicked through the DM popup in the DOM, which is
both fragile and undetectable by Instagram's bot heuristics in roughly
equal measure; v3 uses the API path the official web client uses.

This is the most ban-prone action in the library. The conservative
defaults from :class:`ActionsConfig` (30..60s pacing, 5 consecutive
errors before pause) apply equally here, but you should also read
the threat-model section in ``SECURITY.md`` before using DMs in
production.
"""

from __future__ import annotations

import json
from typing import Optional

from instaharvest.actions._base import _ActionBase
from instaharvest.core.exceptions import NetworkError
from instaharvest.core.models import ActionResult


_BROADCAST_URL = (
    "https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/"
)
_PROFILE_API = (
    "https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
)


class MessagingActions(_ActionBase):
    """Send DMs via the official API endpoint."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._user_id_cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(self, username: str, text: str) -> ActionResult:
        """Send ``text`` to ``username``.

        Returns:
            :class:`ActionStatus.OK` on success,
            :class:`ActionStatus.DRY_RUN` if dry-run is on,
            :class:`ActionStatus.ERROR` otherwise.
        """
        username = _normalise_username(username)
        if not isinstance(text, str) or not text.strip():
            return self._error("send_message", username, "empty text")
        if len(text) > 1000:
            return self._error(
                "send_message", username,
                f"text too long ({len(text)} chars; Instagram caps at 1000)",
            )

        self._require_enabled("send_message")

        user_id = self._resolve_user_id(username)
        if user_id is None:
            return self._error(
                "send_message", username, "could not resolve user_id"
            )

        # Instagram's broadcast endpoint takes form-urlencoded data.
        # The ``recipient_users`` field is a JSON-encoded list of
        # lists: ``[[user_id]]``. The outer list represents threads;
        # one DM => one thread => one inner list with one recipient.
        body = {
            "recipient_users": json.dumps([[user_id]]),
            "action": "send_item",
            "text": text,
        }

        return self._perform(
            action="send_message",
            target=username,
            api_call=lambda: self._http.post(
                _BROADCAST_URL,
                data=body,
                headers=self._action_headers(),
            ),
            success_predicate=_broadcast_ok,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_user_id(self, username: str) -> Optional[str]:
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


def _broadcast_ok(payload) -> bool:
    """``broadcast/text/`` returns ``{"status": "ok", "action": "send_item"}``."""
    if not isinstance(payload, dict):
        return False
    return payload.get("status") == "ok"


__all__ = ["MessagingActions"]
