"""Tests for the v3 ``actions`` namespace.

Focus areas:

  * Two-step opt-in (enabled / dry_run) is enforced.
  * Username validation runs *before* any I/O.
  * Dry-run never makes mutation requests.
  * Pre-checks short-circuit ``follow`` / ``unfollow`` correctly.
  * The success predicate distinguishes "API returned ok and the
    state really changed" from "API returned ok but the side effect
    did not happen".
  * Consecutive errors track and eventually pause the namespace.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional

import pytest

from instaharvest._v3 import (
    ActionResult,
    ActionStatus,
    ActionsConfig,
    Settings,
)
from instaharvest._v3.actions import Actions
from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.exceptions import ConfigError, NetworkError
from instaharvest._v3.scrapers.followers import FollowersScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _config(*, enabled: bool, dry_run: bool, **overrides) -> ActionsConfig:
    base = dict(
        enabled=enabled,
        dry_run=dry_run,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
    )
    base.update(overrides)
    return ActionsConfig(**base)


def _make_actions(
    http: FakeHttpClient,
    *,
    enabled: bool = True,
    dry_run: bool = False,
    config_overrides: Optional[dict] = None,
) -> Actions:
    config = _config(enabled=enabled, dry_run=dry_run, **(config_overrides or {}))
    followers = FollowersScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0, request_delay_max=0.0,
            cooldown_seconds=0.0, cooldown_max_retries=0,
        ),
    )
    return Actions(
        http=http,
        logger=FakeLogger(),
        config=config,
        followers=followers,
    )


_PROFILE_API = "https://i.instagram.com/api/v1/users/web_profile_info/"
_FOLLOW_URL = "https://www.instagram.com/api/v1/friendships/create/"
_UNFOLLOW_URL = "https://www.instagram.com/api/v1/friendships/destroy/"
_FRIENDSHIP_URL = "https://i.instagram.com/api/v1/friendships/show/"
_BROADCAST_URL = "https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/"


def _profile_response(user_id: str) -> FakeHttpResponse:
    return FakeHttpResponse(
        status_code=200,
        json_data={"data": {"user": {"id": user_id, "username": "alice"}}},
    )


# ---------------------------------------------------------------------------
# Disabled / dry-run gating
# ---------------------------------------------------------------------------


class TestEnabledGate:
    def test_disabled_follow_raises(self):
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=False)
        with pytest.raises(ConfigError) as exc:
            actions.follow("alice")
        assert "disabled" in str(exc.value).lower()
        # No HTTP traffic should have happened.
        assert http.calls == []

    def test_disabled_unfollow_raises(self):
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=False)
        with pytest.raises(ConfigError):
            actions.unfollow("alice")

    def test_disabled_send_message_raises(self):
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=False)
        with pytest.raises(ConfigError):
            actions.send_message("alice", "hi")

    def test_introspection_works_when_disabled(self):
        # Accessing the namespace shouldn't itself fail — only calls do.
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=False, dry_run=True)
        assert actions.enabled is False
        assert actions.dry_run is True
        assert actions.social is not None
        assert actions.messaging is not None


class TestDryRun:
    def test_follow_dry_run_returns_dry_run_status(self):
        http = FakeHttpClient()
        # Profile lookup still happens (we need user_id for logging).
        http.responses[_PROFILE_API] = _profile_response("99")
        # Friendship status pre-check also happens — give it a 404
        # shape so the pre-check fails-soft and we proceed to the
        # mutation path which is then short-circuited by dry-run.
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={},
        )

        actions = _make_actions(http, enabled=True, dry_run=True)
        result = actions.follow("alice")

        assert result.status == ActionStatus.DRY_RUN
        assert result.action == "follow"
        # Mutation endpoint must NOT have been called.
        assert not any(
            c["url"].startswith(_FOLLOW_URL) for c in http.calls
        )

    def test_send_message_dry_run(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        actions = _make_actions(http, enabled=True, dry_run=True)
        result = actions.send_message("alice", "hello")
        assert result.status == ActionStatus.DRY_RUN
        assert not any(
            c["url"].startswith(_BROADCAST_URL) for c in http.calls
        )


# ---------------------------------------------------------------------------
# Input validation (runs before I/O)
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_invalid_username_rejected_before_io(self):
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=True, dry_run=False)
        with pytest.raises(ValueError):
            actions.follow("not a username!")
        assert http.calls == []

    def test_send_message_empty_text_returns_error(self):
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=True, dry_run=False)
        # Username validation happens first. With a valid username
        # but empty text, we get an ERROR result — no exception.
        result = actions.send_message("alice", "  ")
        assert result.status == ActionStatus.ERROR
        assert "empty" in result.message.lower()
        assert http.calls == []

    def test_send_message_too_long_rejected(self):
        http = FakeHttpClient()
        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.send_message("alice", "x" * 1001)
        assert result.status == ActionStatus.ERROR
        assert "too long" in result.message.lower()


# ---------------------------------------------------------------------------
# Follow / unfollow
# ---------------------------------------------------------------------------


class TestFollowSuccess:
    def test_follow_ok_when_not_following(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": False},
        )
        http.responses[_FOLLOW_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"status": "ok", "friendship_status": {"following": True}},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.follow("alice")
        assert result.status == ActionStatus.OK
        assert result.action == "follow"
        assert result.target == "alice"

    def test_follow_short_circuits_on_already_following(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": True},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.follow("alice")
        assert result.status == ActionStatus.ALREADY_DONE
        # Mutation endpoint must NOT have been hit.
        assert not any(c["url"].startswith(_FOLLOW_URL) for c in http.calls)

    def test_follow_check_status_false_skips_pre_check(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FOLLOW_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"status": "ok", "friendship_status": {"following": True}},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.follow("alice", check_status=False)
        assert result.status == ActionStatus.OK
        # Friendship pre-check must NOT have been called.
        assert not any(c["url"].startswith(_FRIENDSHIP_URL) for c in http.calls)


class TestFollowFailure:
    def test_user_id_resolution_failure_returns_error(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = FakeHttpResponse(status_code=404)

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.follow("alice")
        assert result.status == ActionStatus.ERROR
        assert "user_id" in result.message

    def test_api_returns_ok_status_but_following_false_is_error(self):
        """Defends against silent no-ops on the server side.

        Instagram has historically returned ``status: ok`` while quietly
        refusing the friendship change (rate-limit shadow ban, account
        review, etc.). The success predicate must catch this.
        """
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": False},
        )
        http.responses[_FOLLOW_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"status": "ok", "friendship_status": {"following": False}},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.follow("alice")
        assert result.status == ActionStatus.ERROR
        assert "non-success" in result.message

    def test_network_error_caught_and_reported(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": False},
        )
        http.raise_for_url[_FOLLOW_URL] = NetworkError("boom", url=_FOLLOW_URL)

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.follow("alice")
        assert result.status == ActionStatus.ERROR
        assert "network" in result.message.lower()


class TestUnfollow:
    def test_short_circuits_on_not_following(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": False},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.unfollow("alice")
        assert result.status == ActionStatus.NOT_APPLICABLE
        assert not any(c["url"].startswith(_UNFOLLOW_URL) for c in http.calls)

    def test_destroy_ok(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": True},
        )
        http.responses[_UNFOLLOW_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"status": "ok", "friendship_status": {"following": False}},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.unfollow("alice")
        assert result.status == ActionStatus.OK


# ---------------------------------------------------------------------------
# Send message
# ---------------------------------------------------------------------------


class TestSendMessage:
    def test_ok(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_BROADCAST_URL] = FakeHttpResponse(
            status_code=200, json_data={"status": "ok", "action": "send_item"},
        )

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.send_message("alice", "hello")
        assert result.status == ActionStatus.OK

    def test_user_id_resolution_failure(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = FakeHttpResponse(status_code=404)

        actions = _make_actions(http, enabled=True, dry_run=False)
        result = actions.send_message("alice", "hi")
        assert result.status == ActionStatus.ERROR


# ---------------------------------------------------------------------------
# Consecutive-error pause
# ---------------------------------------------------------------------------


class TestConsecutiveErrorPause:
    def test_paused_after_n_errors(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": False},
        )
        http.responses[_FOLLOW_URL] = FakeHttpResponse(status_code=503)

        actions = _make_actions(
            http,
            enabled=True,
            dry_run=False,
            config_overrides={"max_consecutive_errors": 2},
        )

        # Two errors are allowed.
        r1 = actions.follow("alice")
        assert r1.status == ActionStatus.ERROR
        r2 = actions.follow("alice")
        assert r2.status == ActionStatus.ERROR

        # Third call must raise — the namespace is paused.
        with pytest.raises(ConfigError) as exc:
            actions.follow("alice")
        assert "consecutive" in str(exc.value).lower()

    def test_success_resets_consecutive_counter(self):
        http = FakeHttpClient()
        http.responses[_PROFILE_API] = _profile_response("99")
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={"following": False},
        )

        # First call: follow returns success.
        http.responses[_FOLLOW_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"status": "ok", "friendship_status": {"following": True}},
        )

        actions = _make_actions(
            http,
            enabled=True,
            dry_run=False,
            config_overrides={"max_consecutive_errors": 2},
        )

        r1 = actions.follow("alice")
        assert r1.status == ActionStatus.OK
        # Now flip the response to error twice — counter should reset
        # after r1, so we get to do two errors before pause.
        http.responses[_FOLLOW_URL] = FakeHttpResponse(status_code=503)
        # Friendship needs to keep saying "not following" for the
        # mutation path to be reached.
        r2 = actions.follow("bob")
        r3 = actions.follow("carol")
        assert r2.status == ActionStatus.ERROR
        assert r3.status == ActionStatus.ERROR
        with pytest.raises(ConfigError):
            actions.follow("dave")
