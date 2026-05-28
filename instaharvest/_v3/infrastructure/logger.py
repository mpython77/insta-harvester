"""
Structured logger.

Implements the ``Logger`` protocol from ``core.protocols``.
Every log line is a single string of the form::

    LEVEL name: message key1=value1 key2=value2

No emoji, no decorative whitespace, no multi-line banners. The log
output is grep-friendly and can be ingested by standard tooling
(jq-after-cut, Loki, CloudWatch, etc.) without fighting the format.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional


def _format_context(context: dict) -> str:
    """Render kwargs as ``key=value`` pairs, quoting values with spaces."""
    if not context:
        return ""
    parts = []
    for key, value in context.items():
        rendered = repr(value) if isinstance(value, str) and " " in value else str(value)
        parts.append(f"{key}={rendered}")
    return " " + " ".join(parts)


class StructuredLogger:
    """``logging.Logger`` adapter that supports kwargs-as-context.

    Construct via :func:`get_logger`. Direct instantiation is supported
    but discouraged outside tests.
    """

    def __init__(self, name: str, level: str = "INFO") -> None:
        self._impl = logging.getLogger(f"instaharvest.v3.{name}")
        if not self._impl.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s: %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                )
            )
            self._impl.addHandler(handler)
            self._impl.propagate = False
        self._impl.setLevel(level)

    # Logger protocol -------------------------------------------------------

    def debug(self, message: str, **context: Any) -> None:
        self._impl.debug(message + _format_context(context))

    def info(self, message: str, **context: Any) -> None:
        self._impl.info(message + _format_context(context))

    def warning(self, message: str, **context: Any) -> None:
        self._impl.warning(message + _format_context(context))

    def error(self, message: str, **context: Any) -> None:
        self._impl.error(message + _format_context(context))


def get_logger(name: str, level: Optional[str] = None) -> StructuredLogger:
    """Create or fetch a configured ``StructuredLogger``."""
    return StructuredLogger(name, level or "INFO")
