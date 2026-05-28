"""Tests for ActionResult / ActionStatus models and ActionsConfig."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from instaharvest import ActionResult, ActionStatus, ActionsConfig


class TestActionStatus:
    def test_enum_values(self):
        # Document the wire-format names so callers can serialise
        # ActionResult to JSON without surprise.
        assert ActionStatus.OK.value == "ok"
        assert ActionStatus.ALREADY_DONE.value == "already_done"
        assert ActionStatus.NOT_APPLICABLE.value == "not_applicable"
        assert ActionStatus.DRY_RUN.value == "dry_run"
        assert ActionStatus.ERROR.value == "error"


class TestActionResult:
    def test_minimal(self):
        r = ActionResult(action="follow", target="alice", status=ActionStatus.OK)
        assert r.message == ""
        assert r.extra is None

    def test_succeeded_excludes_only_error(self):
        # Document the contract — anything-but-ERROR is "Instagram is
        # in the desired state". Callers that want strict OK should
        # check `status == ActionStatus.OK` directly.
        for s in (
            ActionStatus.OK,
            ActionStatus.ALREADY_DONE,
            ActionStatus.NOT_APPLICABLE,
            ActionStatus.DRY_RUN,
        ):
            assert ActionResult(
                action="x", target="y", status=s,
            ).succeeded is True
        assert ActionResult(
            action="x", target="y", status=ActionStatus.ERROR,
        ).succeeded is False

    def test_empty_action_rejected(self):
        with pytest.raises(ValidationError):
            ActionResult(action="", target="alice", status=ActionStatus.OK)

    def test_empty_target_rejected(self):
        with pytest.raises(ValidationError):
            ActionResult(action="follow", target="", status=ActionStatus.OK)

    def test_is_frozen(self):
        r = ActionResult(action="follow", target="alice", status=ActionStatus.OK)
        with pytest.raises(ValidationError):
            r.message = "tampered"  # type: ignore[misc]


class TestActionsConfig:
    def test_default_is_off_and_dry_run(self):
        c = ActionsConfig()
        assert c.enabled is False
        assert c.dry_run is True

    def test_negative_delay_rejected(self):
        with pytest.raises(ValueError):
            ActionsConfig(min_delay_seconds=-1)

    def test_max_below_min_rejected(self):
        with pytest.raises(ValueError):
            ActionsConfig(min_delay_seconds=10, max_delay_seconds=5)

    def test_zero_max_consecutive_errors_rejected(self):
        with pytest.raises(ValueError):
            ActionsConfig(max_consecutive_errors=0)
