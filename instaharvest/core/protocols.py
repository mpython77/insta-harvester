"""
Protocol abstractions.

Scrapers depend on these — never on Playwright or curl_cffi directly.
Tests inject in-memory fakes that implement the same shape; production
code wires up the concrete implementations from ``infrastructure``.

This is the boundary that lets us:
    * test scrapers without spinning up a real browser
    * swap the HTTP stack (today: curl_cffi) without touching scrapers
    * share logic between sync and async by parameterising on protocol
"""

from __future__ import annotations

from typing import (
    Any,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    runtime_checkable,
)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


@runtime_checkable
class HttpResponse(Protocol):
    """The minimum shape v3 scrapers need from an HTTP response."""

    status_code: int
    text: str
    content: bytes

    def json(self) -> Any: ...


@runtime_checkable
class HttpClient(Protocol):
    """Single HTTP stack used outside the browser.

    Implementations (production: curl_cffi) handle proxy rotation,
    timeouts, retries, and TLS impersonation. Scrapers see only this.
    """

    def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> HttpResponse: ...

    def post(
        self,
        url: str,
        *,
        data: Any = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> HttpResponse: ...

    def stream_to_file(self, url: str, dest: str) -> None: ...

    def import_cookies(self, cookies: Iterable[Mapping[str, Any]]) -> None: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------


@runtime_checkable
class BrowserSession(Protocol):
    """Logged-in Playwright browser surface.

    Owns the playwright/browser/context/page lifecycle. Scrapers never
    call ``sync_playwright()`` themselves — they receive a started
    ``BrowserSession`` from ``InstaHarvest`` and use only the methods
    declared here.
    """

    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None: ...

    def page_url(self) -> str: ...

    def page_content(self) -> str: ...

    def query_text(self, selector: str) -> Optional[str]:
        """Return ``inner_text`` of the first match, or ``None`` if no match."""

    def query_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Return one attribute of the first matching element."""

    def cookies(self) -> List[Mapping[str, Any]]: ...

    def screenshot(self, dest: str) -> None: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@runtime_checkable
class SessionStore(Protocol):
    """Owns Instagram session data on disk.

    Single point of responsibility for:
        * locating session files
        * atomic writes
        * optional encryption
        * cleaning up any temp files we create (e.g. yt-dlp cookies)

    The legacy ``downloader._create_cookie_file_from_session`` leak
    where ``/tmp/ig_cookies_*.txt`` files were left behind is fixed
    here by funnelling all such writes through ``SessionStore`` and
    requiring callers to use ``temp_cookie_file`` as a context manager.
    """

    def exists(self) -> bool: ...

    def load(self) -> Mapping[str, Any]: ...

    def save(self, data: Mapping[str, Any]) -> None: ...

    def temp_cookie_file(self) -> "TempCookieFile":
        """Context manager yielding a Netscape-format cookie file path.

        File is deleted on exit, no exceptions.
        """


@runtime_checkable
class TempCookieFile(Protocol):
    """Result of :meth:`SessionStore.temp_cookie_file`."""

    path: str

    def __enter__(self) -> "TempCookieFile": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


@runtime_checkable
class Logger(Protocol):
    """Minimal structured logger used by v3.

    All keyword arguments are appended as ``key=value`` to the log line,
    which makes them grep-friendly and easy to ship to a log aggregator.
    """

    def debug(self, message: str, **context: Any) -> None: ...
    def info(self, message: str, **context: Any) -> None: ...
    def warning(self, message: str, **context: Any) -> None: ...
    def error(self, message: str, **context: Any) -> None: ...
