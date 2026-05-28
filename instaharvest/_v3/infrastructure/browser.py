"""
Playwright browser session adapter.

Implements the ``BrowserSession`` protocol from ``core.protocols``.

Lifecycle is owned here, not in scrapers:
    * ``start(session_data)`` launches Playwright, builds context with
      cookies pre-loaded, opens a page.
    * The adapter is also a context manager — ``with PlaywrightBrowserSession(...)``
      starts and stops automatically.
    * Scrapers receive a *started* session; they cannot call
      ``sync_playwright()`` themselves.

This is the single place where Playwright is imported in v3 outside
of the legacy tree.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from instaharvest._v3.config.browser import BrowserConfig
from instaharvest._v3.core.protocols import Logger


class PlaywrightBrowserSession:
    """Concrete ``BrowserSession`` backed by ``playwright.sync_api``."""

    def __init__(self, config: BrowserConfig, logger: Logger) -> None:
        self._config = config
        self._logger = logger
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    # Lifecycle -----------------------------------------------------------

    def start(self, session_data: Optional[Mapping[str, Any]] = None) -> None:
        from playwright.sync_api import sync_playwright

        self._logger.info(
            "browser starting",
            channel=self._config.channel,
            headless=self._config.headless,
        )
        self._playwright = sync_playwright().start()

        launch_kwargs: dict = {
            "headless": self._config.headless,
            "channel": self._config.channel,
            "args": list(self._config.extra_launch_args),
        }
        if self._config.executable_path:
            launch_kwargs["executable_path"] = self._config.executable_path

        self._browser = self._playwright.chromium.launch(**launch_kwargs)

        context_kwargs: dict = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            "locale": self._config.locale,
            "accept_downloads": self._config.accept_downloads,
        }
        if self._config.user_agent:
            context_kwargs["user_agent"] = self._config.user_agent
        if session_data:
            context_kwargs["storage_state"] = dict(session_data)

        self._context = self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(self._config.default_timeout_ms)
        self._context.set_default_navigation_timeout(self._config.navigation_timeout_ms)

        if self._config.block_resources:
            blocked = set(self._config.block_resources)

            def _route(route: Any) -> None:
                if route.request.resource_type in blocked:
                    route.abort()
                else:
                    route.continue_()

            self._context.route("**/*", _route)

        self._page = self._context.new_page()

    def __enter__(self) -> "PlaywrightBrowserSession":
        if self._page is None:
            self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # BrowserSession protocol --------------------------------------------

    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None:
        self._require_started()
        self._page.goto(url, wait_until=wait_until)

    def page_url(self) -> str:
        self._require_started()
        return self._page.url

    def page_content(self) -> str:
        self._require_started()
        return self._page.content()

    def query_text(self, selector: str) -> Optional[str]:
        self._require_started()
        loc = self._page.locator(selector).first
        if loc.count() == 0:
            return None
        try:
            return loc.inner_text()
        except Exception as exc:
            self._logger.debug("query_text failed", selector=selector, error=str(exc))
            return None

    def query_attribute(self, selector: str, attribute: str) -> Optional[str]:
        self._require_started()
        loc = self._page.locator(selector).first
        if loc.count() == 0:
            return None
        try:
            return loc.get_attribute(attribute)
        except Exception as exc:
            self._logger.debug(
                "query_attribute failed",
                selector=selector,
                attribute=attribute,
                error=str(exc),
            )
            return None

    def cookies(self) -> List[Mapping[str, Any]]:
        self._require_started()
        return list(self._context.cookies())

    def screenshot(self, dest: str) -> None:
        self._require_started()
        self._page.screenshot(path=dest, full_page=True)

    def close(self) -> None:
        for closer, name in [
            (lambda: self._page and self._page.close(), "page"),
            (lambda: self._context and self._context.close(), "context"),
            (lambda: self._browser and self._browser.close(), "browser"),
            (lambda: self._playwright and self._playwright.stop(), "playwright"),
        ]:
            try:
                closer()
            except Exception as exc:
                self._logger.warning("browser close error", component=name, error=str(exc))
        self._page = self._context = self._browser = self._playwright = None

    # ----------------------------------------------------------------

    def _require_started(self) -> None:
        if self._page is None:
            raise RuntimeError(
                "PlaywrightBrowserSession is not started; call start() or use as a context manager"
            )
