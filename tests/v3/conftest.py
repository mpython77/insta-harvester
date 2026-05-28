"""
In-memory fakes for v3 protocols.

These fakes implement the protocols from ``instaharvest._v3.core.protocols``
faithfully — they record calls, let tests pre-program responses, and
have observable side effects. They are not :class:`MagicMock`: a test
that uses them is exercising real code paths through the protocol
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


@dataclass
class FakeLogger:
    """Captures every log call so tests can assert on them."""

    records: List[tuple] = field(default_factory=list)

    def debug(self, message: str, **context: Any) -> None:
        self.records.append(("debug", message, context))

    def info(self, message: str, **context: Any) -> None:
        self.records.append(("info", message, context))

    def warning(self, message: str, **context: Any) -> None:
        self.records.append(("warning", message, context))

    def error(self, message: str, **context: Any) -> None:
        self.records.append(("error", message, context))

    def messages_at(self, level: str) -> List[str]:
        return [msg for lvl, msg, _ in self.records if lvl == level]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


class FakeHttpResponse:
    def __init__(self, *, status_code: int = 200, json_data: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_data
        self.text = text or ""
        self.content = self.text.encode()

    def json(self) -> Any:
        if self._json is None:
            raise ValueError("no json configured")
        return self._json


@dataclass
class FakeHttpClient:
    """Programmable HTTP client. Returns canned responses by URL prefix."""

    responses: Dict[str, FakeHttpResponse] = field(default_factory=dict)
    raise_for_url: Dict[str, Exception] = field(default_factory=dict)
    calls: List[Dict[str, Any]] = field(default_factory=list)
    imported_cookies: List[Mapping[str, Any]] = field(default_factory=list)
    closed: bool = False

    def _lookup(self, url: str) -> FakeHttpResponse:
        if url in self.raise_for_url:
            raise self.raise_for_url[url]
        for prefix, resp in self.responses.items():
            if url.startswith(prefix):
                return resp
        raise AssertionError(f"FakeHttpClient: no response programmed for {url!r}")

    def get(self, url: str, *, params=None, headers=None) -> FakeHttpResponse:
        self.calls.append({"method": "GET", "url": url, "headers": headers})
        return self._lookup(url)

    def post(self, url: str, *, data=None, json=None, headers=None) -> FakeHttpResponse:
        self.calls.append({"method": "POST", "url": url, "json": json, "headers": headers})
        return self._lookup(url)

    def stream_to_file(self, url: str, dest: str) -> None:
        self.calls.append({"method": "STREAM", "url": url, "dest": dest})
        with open(dest, "wb") as fh:
            fh.write(self._lookup(url).content)

    def import_cookies(self, cookies: Iterable[Mapping[str, Any]]) -> None:
        self.imported_cookies = list(cookies)

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------


@dataclass
class FakeBrowserSession:
    """Programmable browser. Tests set ``url``/``content``/``elements``.

    ``elements`` maps a CSS selector to a dict ``{"text": ..., "attrs": {...}}``.
    """

    url: str = "https://www.instagram.com/"
    content: str = ""
    elements: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cookies_data: List[Mapping[str, Any]] = field(default_factory=list)
    visited: List[str] = field(default_factory=list)
    closed: bool = False
    raise_on_goto: Optional[Exception] = None

    # Sequence of (url, content, elements) tuples to apply after each goto.
    # Used to simulate redirects / state changes.
    goto_sequence: List[Dict[str, Any]] = field(default_factory=list)

    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None:
        if self.raise_on_goto is not None:
            raise self.raise_on_goto
        self.visited.append(url)
        if self.goto_sequence:
            step = self.goto_sequence.pop(0)
            self.url = step.get("url", url)
            self.content = step.get("content", self.content)
            if "elements" in step:
                self.elements = step["elements"]
        else:
            self.url = url

    def page_url(self) -> str:
        return self.url

    def page_content(self) -> str:
        return self.content

    def query_text(self, selector: str) -> Optional[str]:
        elem = self.elements.get(selector)
        if elem is None:
            return None
        return elem.get("text")

    def query_attribute(self, selector: str, attribute: str) -> Optional[str]:
        elem = self.elements.get(selector)
        if elem is None:
            return None
        return (elem.get("attrs") or {}).get(attribute)

    def cookies(self) -> List[Mapping[str, Any]]:
        return list(self.cookies_data)

    def screenshot(self, dest: str) -> None:
        with open(dest, "wb") as fh:
            fh.write(b"png-stub")

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------


@dataclass
class FakeSessionStore:
    """In-memory session store. Tests set ``data`` directly."""

    data: Optional[Mapping[str, Any]] = None

    def exists(self) -> bool:
        return self.data is not None

    def load(self) -> Mapping[str, Any]:
        if self.data is None:
            from instaharvest._v3.core.exceptions import SessionNotFoundError
            raise SessionNotFoundError("(in-memory)")
        return self.data

    def save(self, data: Mapping[str, Any]) -> None:
        self.data = dict(data)

    def temp_cookie_file(self) -> Any:
        # Tests that need this should use the real FileSessionStore.
        raise NotImplementedError("use FileSessionStore for temp_cookie_file")
