"""Tests for StructuredLogger output format.

The logger sets ``propagate=False`` so log lines do not bubble up to
pytest's ``caplog`` fixture (which would double-record output in
applications that already have their own root handler). We verify
behaviour by capturing stderr directly with ``capfd``.
"""

from __future__ import annotations

import pytest

from instaharvest.infrastructure.logger import StructuredLogger, get_logger


class TestStructuredLogger:
    def test_message_with_no_context(self, capfd):
        logger = StructuredLogger("test_no_ctx", level="DEBUG")
        logger.info("hello world")
        err = capfd.readouterr().err
        assert "hello world" in err
        assert "INFO" in err

    def test_kwargs_render_as_key_value(self, capfd):
        logger = StructuredLogger("test_kv", level="DEBUG")
        logger.info("ok", username="alice", count=42)
        err = capfd.readouterr().err
        assert "username=alice" in err
        assert "count=42" in err

    def test_string_with_space_is_quoted(self, capfd):
        logger = StructuredLogger("test_space", level="DEBUG")
        logger.info("ok", reason="needs more time")
        err = capfd.readouterr().err
        # The repr-quoted form keeps the value parseable.
        assert "reason='needs more time'" in err

    def test_no_emoji_in_output(self, capfd):
        logger = StructuredLogger("test_noemoji", level="DEBUG")
        logger.info("done", phase="a")
        err = capfd.readouterr().err
        # No emoji escape codes anywhere in the rendered line.
        for ch in ("🛡", "✅", "🍪", "⚡", "🎬", "💾"):
            assert ch not in err

    def test_levels_route_correctly(self, capfd):
        logger = StructuredLogger("test_levels", level="DEBUG")
        logger.debug("dmsg")
        logger.info("imsg")
        logger.warning("wmsg")
        logger.error("emsg")
        err = capfd.readouterr().err
        assert "DEBUG" in err and "dmsg" in err
        assert "INFO" in err and "imsg" in err
        assert "WARNING" in err and "wmsg" in err
        assert "ERROR" in err and "emsg" in err


class TestGetLogger:
    def test_returns_structured_logger(self):
        logger = get_logger("factory_test")
        assert isinstance(logger, StructuredLogger)

    def test_handlers_not_duplicated_on_repeated_calls(self):
        # Calling get_logger twice with the same name must not stack handlers
        # (otherwise we'd double-log every message).
        logger1 = get_logger("dup_test")
        logger2 = get_logger("dup_test")
        # Both wrap the same underlying ``logging.Logger`` (Python's logger
        # registry returns the same instance per name) and that logger
        # should have exactly one handler.
        assert len(logger1._impl.handlers) == 1
        assert logger1._impl is logger2._impl
