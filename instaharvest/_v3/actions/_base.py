"""
Internal base class for action sub-namespaces.

Owns the cross-cutting concerns every action shares:

  * dry-run gating
  * pacing (random delay between calls)
  * consecutive-error tracking with hard stop
  * CSRF token extraction from imported cookies
  * uniform :class:`ActionResult` construction

Concrete action classes (:class:`SocialActions`,
:class:`MessagingActions`) only need to implement the actual API call
in their own methods; everything else is handled by ``_perform``.
"""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Optional

from instaharvest._v3.config.actions import ActionsConfig
from instaharvest._v3.core.exceptions import ConfigError, NetworkError
from instaharvest._v3.core.models import ActionResult, ActionStatus
from instaharvest._v3.core.protocols import HttpClient, Logger


# Header Instagram requires on private write endpoints. Public reads
# usually accept it too, so it costs nothing to send everywhere.
ACTION_HEADERS_BASE = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
    "Origin": "https://www.instagram.com",
    "Referer": "https://www.instagram.com/",
}


class _ActionBase:
    """Shared infrastructure for action sub-namespaces."""

    def __init__(
        self,
        *,
        http: HttpClient,
        logger: Logger,
        config: ActionsConfig,
    ) -> None:
        self._http = http
        self._logger = logger
        self._config = config
        self._consecutive_errors: int = 0
        self._last_action_at: float = 0.0

    # ------------------------------------------------------------------
    # Pre-flight checks
    # ------------------------------------------------------------------

    def _require_enabled(self, action: str) -> None:
        """Refuse the call if actions are disabled.

        Called by every action method as its first line. We *do not*
        want a half-executed dry-run path if the user forgot to
        flip ``enabled``.
        """
        if not self._config.enabled:
            raise ConfigError(
                f"action {action!r} is disabled. "
                "Set Settings.actions.enabled=True to allow write operations. "
                "See instaharvest._v3.actions package docstring for the "
                "two-step opt-in procedure."
            )
        if self._consecutive_errors >= self._config.max_consecutive_errors:
            raise ConfigError(
                f"actions paused after {self._consecutive_errors} consecutive "
                "errors; reset the InstaHarvest facade to retry. This usually "
                "means the account is rate-limited or the session has expired."
            )

    # ------------------------------------------------------------------
    # Result helpers
    # ------------------------------------------------------------------

    def _ok(self, action: str, target: str, message: str = "", **extra) -> ActionResult:
        self._consecutive_errors = 0
        return ActionResult(
            action=action,
            target=target,
            status=ActionStatus.OK,
            message=message,
            extra=extra or None,
        )

    def _already_done(self, action: str, target: str, message: str = "") -> ActionResult:
        self._consecutive_errors = 0
        return ActionResult(
            action=action,
            target=target,
            status=ActionStatus.ALREADY_DONE,
            message=message,
        )

    def _not_applicable(self, action: str, target: str, message: str = "") -> ActionResult:
        self._consecutive_errors = 0
        return ActionResult(
            action=action,
            target=target,
            status=ActionStatus.NOT_APPLICABLE,
            message=message,
        )

    def _dry_run(self, action: str, target: str, message: str = "") -> ActionResult:
        # Dry-run does NOT reset consecutive_errors — by design it
        # should never have caused them in the first place.
        return ActionResult(
            action=action,
            target=target,
            status=ActionStatus.DRY_RUN,
            message=message or f"dry-run: would {action} {target}",
        )

    def _error(self, action: str, target: str, message: str, **extra) -> ActionResult:
        self._consecutive_errors += 1
        # Embed the failure reason in the log message itself rather than
        # passing it as a ``message=`` kwarg — the structured logger
        # already takes ``message`` as its positional argument, and
        # passing it twice raises TypeError.
        self._logger.warning(
            f"action error: {message}",
            action=action,
            target=target,
            consecutive=self._consecutive_errors,
        )
        return ActionResult(
            action=action,
            target=target,
            status=ActionStatus.ERROR,
            message=message,
            extra=extra or None,
        )

    # ------------------------------------------------------------------
    # Pacing
    # ------------------------------------------------------------------

    def _respect_pacing(self) -> None:
        if self._config.max_delay_seconds <= 0:
            self._last_action_at = time.monotonic()
            return
        delay = random.uniform(
            self._config.min_delay_seconds,
            self._config.max_delay_seconds,
        )
        elapsed = time.monotonic() - self._last_action_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_action_at = time.monotonic()

    # ------------------------------------------------------------------
    # CSRF
    # ------------------------------------------------------------------

    def _csrf_token(self) -> Optional[str]:
        """Extract the ``csrftoken`` cookie from the underlying HTTP session.

        Instagram's write endpoints reject requests without a valid
        ``X-CSRFToken`` header. We pull it from whatever the
        :class:`HttpClient` has cached, but fail soft — if the token
        is unavailable the action method will surface a clear error
        instead of an opaque 403.
        """
        # Optional escape hatch: implementations that bind cookies
        # internally can expose ``csrf_token()``. The default
        # CurlHttpClient (production) currently does not, but tests
        # may inject a fake that does.
        getter = getattr(self._http, "csrf_token", None)
        if callable(getter):
            return getter()
        # Fallback: peek at the underlying session if it has one.
        session = getattr(self._http, "_session", None)
        cookies = getattr(session, "cookies", None) if session is not None else None
        if cookies is not None:
            try:
                return cookies.get("csrftoken")
            except Exception:
                return None
        return None

    def _action_headers(self) -> dict:
        headers = dict(ACTION_HEADERS_BASE)
        token = self._csrf_token()
        if token:
            headers["X-CSRFToken"] = token
        return headers

    # ------------------------------------------------------------------
    # Generic perform
    # ------------------------------------------------------------------

    def _perform(
        self,
        *,
        action: str,
        target: str,
        api_call: Callable[[], Any],
        success_predicate: Callable[[Any], bool] = lambda r: True,
    ) -> ActionResult:
        """Wrap a real API call with dry-run, pacing, error tracking.

        ``api_call`` is invoked only if dry-run is off. It must either
        return an HTTP response (whose ``.json()`` method we use for
        ``extra``), or raise — anything raised is converted to an
        :class:`ActionStatus.ERROR` with the cause attached.
        """
        if self._config.dry_run:
            return self._dry_run(action, target)

        self._respect_pacing()

        try:
            resp = api_call()
        except NetworkError as exc:
            return self._error(action, target, f"network: {exc}", url=exc.url)
        except Exception as exc:  # last-resort guard
            return self._error(action, target, f"unexpected: {exc}")

        status_code = getattr(resp, "status_code", None)
        if status_code is None or status_code >= 400:
            return self._error(
                action,
                target,
                f"http status {status_code}",
                status=status_code,
            )

        try:
            payload = resp.json()
        except Exception:
            payload = None

        if not success_predicate(payload):
            return self._error(
                action,
                target,
                "api returned non-success payload",
                payload=payload,
            )

        return self._ok(action, target, message=f"{action} ok", payload=payload)
