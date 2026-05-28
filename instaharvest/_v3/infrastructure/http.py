"""
Single HTTP stack for v3 — curl_cffi-based.

Replaces the four-stack situation in legacy (Playwright +
curl_cffi + requests + yt-dlp internal). Exposes the
``HttpClient`` protocol from ``core.protocols``.

Concerns owned here:
    * proxy rotation (round-robin over the configured pool)
    * timeouts and exponential back-off retries
    * TLS impersonation profile
    * cookie import from a Playwright session
    * streaming download with bounded memory

Concerns deliberately NOT owned here:
    * session storage (see ``FileSessionStore``)
    * page rendering (see ``PlaywrightBrowserSession``)
    * domain logic (see scrapers)
"""

from __future__ import annotations

import time
from typing import Any, Iterable, List, Mapping, Optional

from curl_cffi import requests as curl_requests

from instaharvest._v3.config.network import NetworkConfig
from instaharvest._v3.core.exceptions import NetworkError
from instaharvest._v3.core.protocols import HttpResponse, Logger


_DEFAULT_HEADERS: dict = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


class _CurlResponse:
    """Adapter satisfying ``HttpResponse`` for ``curl_cffi.requests.Response``."""

    __slots__ = ("_inner",)

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def status_code(self) -> int:
        return int(self._inner.status_code)

    @property
    def text(self) -> str:
        return self._inner.text  # type: ignore[no-any-return]

    @property
    def content(self) -> bytes:
        return self._inner.content  # type: ignore[no-any-return]

    def json(self) -> Any:
        return self._inner.json()


class CurlHttpClient:
    """Concrete ``HttpClient`` — curl_cffi with proxy rotation and retries."""

    def __init__(self, config: NetworkConfig, logger: Logger) -> None:
        self._config = config
        self._logger = logger
        self._session = curl_requests.Session(impersonate=config.impersonate)
        self._session.headers.update(_DEFAULT_HEADERS)

        # Proxy state
        self._proxy_pool: List[str] = list(config.proxy_pool)
        if config.proxy_url:
            self._proxy_pool.insert(0, config.proxy_url)
        self._proxy_index: int = 0
        self._proxy_failures: dict[str, int] = {}

    # ----- proxy ----------------------------------------------------------

    def _current_proxy(self) -> Optional[str]:
        if not self._proxy_pool:
            return None
        return self._proxy_pool[self._proxy_index % len(self._proxy_pool)]

    def _rotate_proxy(self) -> None:
        if not self._proxy_pool:
            return
        self._proxy_index = (self._proxy_index + 1) % len(self._proxy_pool)

    def _record_proxy_failure(self, proxy: str) -> None:
        count = self._proxy_failures.get(proxy, 0) + 1
        self._proxy_failures[proxy] = count
        if count >= self._config.proxy_max_failures and proxy in self._proxy_pool:
            self._proxy_pool.remove(proxy)
            self._logger.warning("proxy removed from pool", proxy=proxy, failures=count)

    def _apply_proxy(self) -> None:
        proxy = self._current_proxy()
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        else:
            self._session.proxies = {}

    # ----- request --------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        data: Any = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        stream: bool = False,
    ) -> Any:
        last_exc: Optional[BaseException] = None
        for attempt in range(self._config.max_retries + 1):
            self._apply_proxy()
            current_proxy = self._current_proxy()
            try:
                return self._session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=dict(headers) if headers else None,
                    timeout=(self._config.connect_timeout, self._config.read_timeout),
                    stream=stream,
                )
            except Exception as exc:  # narrow to transport errors only
                last_exc = exc
                self._logger.warning(
                    "http attempt failed",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if current_proxy:
                    self._record_proxy_failure(current_proxy)
                self._rotate_proxy()
                if attempt < self._config.max_retries:
                    backoff = min(
                        self._config.retry_backoff_base * (2 ** attempt),
                        self._config.retry_backoff_cap,
                    )
                    time.sleep(backoff)
        raise NetworkError(
            f"{method} {url} failed after {self._config.max_retries + 1} attempts",
            url=url,
        ) from last_exc

    # ----- HttpClient protocol -------------------------------------------

    def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> HttpResponse:
        resp = self._request("GET", url, params=params, headers=headers)
        return _CurlResponse(resp)

    def post(
        self,
        url: str,
        *,
        data: Any = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> HttpResponse:
        resp = self._request("POST", url, data=data, json=json, headers=headers)
        return _CurlResponse(resp)

    def stream_to_file(self, url: str, dest: str) -> None:
        resp = self._request("GET", url, stream=True)
        try:
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        finally:
            close = getattr(resp, "close", None)
            if callable(close):
                close()

    def import_cookies(self, cookies: Iterable[Mapping[str, Any]]) -> None:
        for cookie in cookies:
            try:
                self._session.cookies.set(
                    name=cookie["name"],
                    value=cookie["value"],
                    domain=cookie.get("domain", ".instagram.com"),
                    path=cookie.get("path", "/"),
                )
            except KeyError as exc:
                self._logger.warning("skipped malformed cookie", missing_key=str(exc))

    def close(self) -> None:
        try:
            self._session.close()
        except Exception as exc:
            self._logger.warning("http session close failed", error=str(exc))
