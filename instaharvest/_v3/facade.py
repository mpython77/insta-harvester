"""
InstaHarvest facade — the single user-facing entry point for v3.

Replaces legacy ``core.InstaHarvest``, which was documented as the
"central hub" but never actually used by any scraper. This one owns
the lifecycle of every infrastructure component and exposes scrapers
as cached properties so users do not construct them directly.

Usage::

    from instaharvest._v3 import InstaHarvest, Settings

    with InstaHarvest(Settings.default()) as ih:
        profile = ih.profile.scrape("instagram")
        print(profile.followers, profile.is_verified)

Design notes:
    * One ``InstaHarvest`` owns one browser session and one HTTP client.
      Scrapers share both, which is the point of the facade.
    * Lazy: nothing is started until a scraper is first accessed.
    * Idempotent ``close()``: safe to call multiple times.
"""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from instaharvest._v3.config.settings import Settings
from instaharvest._v3.actions import Actions
from instaharvest._v3.core.exceptions import SessionNotFoundError
from instaharvest._v3.core.protocols import (
    BrowserSession,
    HttpClient,
    Logger,
    SessionStore,
)
from instaharvest._v3.infrastructure.browser import PlaywrightBrowserSession
from instaharvest._v3.infrastructure.http import CurlHttpClient
from instaharvest._v3.infrastructure.logger import get_logger
from instaharvest._v3.infrastructure.session import FileSessionStore
from instaharvest._v3.evasion import EvasionManager
from instaharvest._v3.scrapers.comments import CommentScraper
from instaharvest._v3.scrapers.explore import ExploreScraper
from instaharvest._v3.scrapers.followers import FollowersScraper
from instaharvest._v3.scrapers.hashtag import HashtagScraper
from instaharvest._v3.scrapers.highlights import HighlightScraper
from instaharvest._v3.scrapers.location import LocationScraper
from instaharvest._v3.scrapers.media import MediaScraper
from instaharvest._v3.scrapers.notifications import NotificationsScraper
from instaharvest._v3.scrapers.profile import ProfileScraper
from instaharvest._v3.scrapers.search import SearchScraper
from instaharvest._v3.scrapers.stories import StoryScraper


class InstaHarvest:
    """Composition root for the v3 API.

    Hand it a :class:`Settings`; it builds and owns:
      * :class:`Logger`           — structured stderr logger
      * :class:`SessionStore`     — file-backed Instagram session
      * :class:`HttpClient`       — curl_cffi-based HTTP client
      * :class:`BrowserSession`   — Playwright browser, lazy-started
      * scrapers, exposed as properties

    Tests can substitute any of the four infrastructure dependencies
    by passing them to the constructor. In production you typically
    just write ``InstaHarvest(Settings.default())``.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        logger: Optional[Logger] = None,
        session_store: Optional[SessionStore] = None,
        http: Optional[HttpClient] = None,
        browser: Optional[BrowserSession] = None,
    ) -> None:
        self._settings = settings
        self._logger: Logger = logger or get_logger("facade")
        self._session_store: SessionStore = session_store or FileSessionStore(
            settings.output, self._logger
        )
        self._http: HttpClient = http or CurlHttpClient(settings.network, self._logger)
        # Browser is constructed eagerly but not *started*; that happens on
        # first scraper use. This keeps unit tests cheap and import-free.
        self._browser: BrowserSession = browser or PlaywrightBrowserSession(
            settings.browser, self._logger
        )
        self._browser_started: bool = browser is not None  # injected ones are pre-started
        self._closed: bool = False

        # Scraper cache — built on first access
        self._profile: Optional[ProfileScraper] = None
        self._media: Optional[MediaScraper] = None
        self._comments: Optional[CommentScraper] = None
        self._followers: Optional[FollowersScraper] = None
        self._actions: Optional[Actions] = None
        self._hashtag: Optional[HashtagScraper] = None
        self._location: Optional[LocationScraper] = None
        self._search: Optional[SearchScraper] = None
        self._explore: Optional[ExploreScraper] = None
        self._stories: Optional[StoryScraper] = None
        self._highlights: Optional[HighlightScraper] = None
        self._notifications: Optional[NotificationsScraper] = None
        self._evasion: Optional[EvasionManager] = None

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def session(self) -> SessionStore:
        """Session storage — load/save and ``temp_cookie_file()``."""
        return self._session_store

    @property
    def http(self) -> HttpClient:
        """HTTP client (curl_cffi) — non-browser HTTP."""
        return self._http

    @property
    def browser(self) -> BrowserSession:
        """Started browser session.

        First access triggers Playwright launch + Instagram session load.
        """
        if not self._browser_started:
            self._start_browser()
        return self._browser

    @property
    def profile(self) -> ProfileScraper:
        """ProfileScraper for ``ih.profile.scrape(username)``."""
        if self._profile is None:
            self._profile = ProfileScraper(
                browser=self.browser,
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
                selectors=self._settings.selectors.profile,
            )
        return self._profile

    @property
    def media(self) -> MediaScraper:
        """MediaScraper for ``ih.media.scrape(url_or_shortcode)``.

        Returns a :class:`Media` covering posts and reels (Instagram
        models them with the same JSON shape; v3 mirrors that).
        """
        if self._media is None:
            self._media = MediaScraper(
                browser=self.browser,
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
                selectors=self._settings.selectors.media,
            )
        return self._media

    @property
    def comments(self) -> CommentScraper:
        """CommentScraper for ``ih.comments.scrape(media_or_shortcode)``.

        API-only path; pagination is resolved internally and returned
        as a single :class:`CommentsPage`.
        """
        if self._comments is None:
            self._comments = CommentScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
                selectors=self._settings.selectors.comments,
            )
        return self._comments

    @property
    def followers(self) -> FollowersScraper:
        """FollowersScraper for ``ih.followers.list_followers(user_id)``.

        Read-only. Returns paginated :class:`FollowList`. Use
        :meth:`FollowersScraper.friendship_status` to check the
        viewer's relationship with another user.
        """
        if self._followers is None:
            self._followers = FollowersScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
            )
        return self._followers

    @property
    def actions(self) -> Actions:
        """Write-operation namespace.

        Off by default. See :mod:`instaharvest._v3.actions` package
        docstring for the two-step opt-in (``Settings.actions.enabled``
        and ``Settings.actions.dry_run``).
        """
        if self._actions is None:
            self._actions = Actions(
                http=self._http,
                logger=self._logger,
                config=self._settings.actions,
                followers=self.followers,
            )
        return self._actions

    @property
    def hashtag(self) -> HashtagScraper:
        """HashtagScraper for ``ih.hashtag.lookup(tag)`` and feed access."""
        if self._hashtag is None:
            self._hashtag = HashtagScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
            )
        return self._hashtag

    @property
    def location(self) -> LocationScraper:
        """LocationScraper for ``ih.location.lookup(pk)`` and feed access."""
        if self._location is None:
            self._location = LocationScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
            )
        return self._location

    @property
    def search(self) -> SearchScraper:
        """SearchScraper for ``ih.search.search(query)``."""
        if self._search is None:
            self._search = SearchScraper(
                http=self._http,
                logger=self._logger,
            )
        return self._search

    @property
    def explore(self) -> ExploreScraper:
        """ExploreScraper for the algorithmic ``/explore/`` feed."""
        if self._explore is None:
            self._explore = ExploreScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
            )
        return self._explore

    @property
    def stories(self) -> StoryScraper:
        """StoryScraper for ``ih.stories.get_stories(user_ids)``."""
        if self._stories is None:
            self._stories = StoryScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
            )
        return self._stories

    @property
    def highlights(self) -> HighlightScraper:
        """HighlightScraper for ``ih.highlights.list_highlights(user_id)``."""
        if self._highlights is None:
            self._highlights = HighlightScraper(
                http=self._http,
                logger=self._logger,
                rate_limit=self._settings.rate_limit,
            )
        return self._highlights

    @property
    def notifications(self) -> NotificationsScraper:
        """NotificationsScraper for ``ih.notifications.feed()``."""
        if self._notifications is None:
            self._notifications = NotificationsScraper(
                http=self._http,
                logger=self._logger,
            )
        return self._notifications

    @property
    def evasion(self) -> EvasionManager:
        """Opt-in evasion features (stealth, CAPTCHA, multi-session)."""
        if self._evasion is None:
            self._evasion = EvasionManager(
                config=self._settings.evasion,
                logger=self._logger,
            )
        return self._evasion

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __enter__(self) -> "InstaHarvest":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release every resource. Safe to call repeatedly."""
        if self._closed:
            return
        self._closed = True

        for closer, name in [
            (self._http.close, "http"),
            (self._browser.close, "browser"),
        ]:
            try:
                closer()
            except Exception as exc:
                self._logger.warning("close error", component=name, error=str(exc))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _start_browser(self) -> None:
        """Launch the browser and load the Instagram session if present.

        We don't fail when no session exists — anonymous browsing still
        works for many endpoints — but we log it so the operator knows
        why they're getting login walls.
        """
        if self._browser_started:
            return

        session_data = None
        if self._session_store.exists():
            try:
                session_data = self._session_store.load()
                self._logger.info("session loaded", path=getattr(self._session_store, "path", None))
            except SessionNotFoundError:
                # Race: file disappeared between exists() and load()
                self._logger.warning("session vanished after exists() check")
        else:
            self._logger.info("no session file found; browsing anonymously")

        # PlaywrightBrowserSession exposes start(); other implementations
        # are assumed to be already started when injected.
        start = getattr(self._browser, "start", None)
        if callable(start):
            start(session_data)

        # Wire cookies into the HTTP client so API calls share auth.
        try:
            cookies = self._browser.cookies()
            if cookies:
                self._http.import_cookies(cookies)
        except Exception as exc:
            self._logger.warning("could not sync browser cookies to http", error=str(exc))

        self._browser_started = True
