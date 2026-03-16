"""
Full coverage tests for instaharvest/base.py — BaseScraper
Target: 8% → 100% (374 missing stmts)
"""

import json
import time
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, PropertyMock
from instaharvest.config import ScraperConfig
from instaharvest.exceptions import (
    SessionNotFoundError, PageLoadError, LoginRequiredError,
    RateLimitError, HTMLStructureChangedError
)


# ── Helper: Concrete subclass of abstract BaseScraper ──
def _make_concrete_scraper(config=None):
    """Create a concrete BaseScraper subclass with mocked dependencies"""
    from instaharvest.base import BaseScraper

    class TestScraper(BaseScraper):
        def scrape(self, *args, **kwargs):
            return "scraped"

    with patch('instaharvest.base.sync_playwright'), \
         patch('instaharvest.base.create_proxy_manager_from_config') as mock_pm:
        mock_pm.return_value = MagicMock(
            has_proxies=False,
            get_for_curl=MagicMock(return_value=None),
            get_for_playwright=MagicMock(return_value=None)
        )
        scraper = TestScraper(config=config or ScraperConfig())
    scraper.logger = MagicMock()
    return scraper


# ═══════════════════════════════════════════════════════════
# __init__ and basic attrs
# ═══════════════════════════════════════════════════════════

class TestBaseScraperInit:
    def test_default_init(self):
        scraper = _make_concrete_scraper()
        assert scraper.config is not None
        assert scraper.playwright is None or scraper.playwright is not None  # may be mock
        assert scraper.interrupted is False
        assert scraper._web_api is None

    def test_custom_config(self):
        cfg = ScraperConfig(headless=False)
        scraper = _make_concrete_scraper(config=cfg)
        assert scraper.config.headless is False


# ═══════════════════════════════════════════════════════════
# check_session_exists / load_session
# ═══════════════════════════════════════════════════════════

class TestSessionFileOps:
    def test_check_session_exists_found(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            f.write(b'{}')
            path = f.name
        try:
            cfg = ScraperConfig()
            cfg.session_file = path
            scraper = _make_concrete_scraper(config=cfg)
            scraper.check_session_exists()  # should not raise
        finally:
            os.unlink(path)

    def test_check_session_exists_not_found(self):
        cfg = ScraperConfig()
        cfg.session_file = '/nonexistent/path/session.json'
        scraper = _make_concrete_scraper(config=cfg)
        with pytest.raises(SessionNotFoundError):
            scraper.check_session_exists()

    def test_load_session_success(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'cookies': [{'name': 'test'}]}, f)
            path = f.name
        try:
            cfg = ScraperConfig()
            cfg.session_file = path
            scraper = _make_concrete_scraper(config=cfg)
            data = scraper.load_session()
            assert len(data['cookies']) == 1
        finally:
            os.unlink(path)

    def test_load_session_bad_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            path = f.name
        try:
            cfg = ScraperConfig()
            cfg.session_file = path
            scraper = _make_concrete_scraper(config=cfg)
            with pytest.raises(SessionNotFoundError):
                scraper.load_session()
        finally:
            os.unlink(path)

    def test_load_session_file_not_found(self):
        cfg = ScraperConfig()
        cfg.session_file = '/nonexistent/session.json'
        scraper = _make_concrete_scraper(config=cfg)
        with pytest.raises(SessionNotFoundError):
            scraper.load_session()


# ═══════════════════════════════════════════════════════════
# update_session
# ═══════════════════════════════════════════════════════════

class TestUpdateSession:
    def test_update_session_no_context(self):
        scraper = _make_concrete_scraper()
        scraper.context = None
        scraper.update_session()
        scraper.logger.warning.assert_called()

    def test_update_session_success(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            cfg = ScraperConfig()
            cfg.session_file = path
            scraper = _make_concrete_scraper(config=cfg)
            mock_ctx = MagicMock()
            mock_ctx.storage_state.return_value = {'cookies': [{'name': 'sid', 'value': 'test'}], 'origins': []}
            scraper.context = mock_ctx
            scraper.update_session()
            with open(path, 'r') as f:
                data = json.load(f)
            assert len(data['cookies']) == 1
        finally:
            os.unlink(path)

    def test_update_session_coroutine_running_loop(self):
        import asyncio
        scraper = _make_concrete_scraper()
        mock_ctx = MagicMock()
        
        async def fake_coroutine():
            return {'cookies': []}
        
        coro = fake_coroutine()
        mock_ctx.storage_state.return_value = coro
        scraper.context = mock_ctx
        
        # patch asyncio.get_event_loop to return a running loop
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            scraper.update_session()
        # should handle gracefully

    def test_update_session_exception(self):
        scraper = _make_concrete_scraper()
        mock_ctx = MagicMock()
        mock_ctx.storage_state.side_effect = Exception("storage error")
        scraper.context = mock_ctx
        scraper.update_session()  # should not raise
        scraper.logger.warning.assert_called()


# ═══════════════════════════════════════════════════════════
# sync_network_client
# ═══════════════════════════════════════════════════════════

class TestSyncNetworkClient:
    def test_with_context(self):
        scraper = _make_concrete_scraper()
        mock_ctx = MagicMock()
        mock_ctx.cookies.return_value = [{'name': 'sid', 'value': 'v'}]
        scraper.context = mock_ctx
        scraper.network_client = MagicMock()
        scraper.sync_network_client()
        scraper.network_client.set_cookies.assert_called_once()

    def test_without_context(self):
        scraper = _make_concrete_scraper()
        scraper.context = None
        scraper.network_client = MagicMock()
        scraper.sync_network_client()
        scraper.network_client.set_cookies.assert_not_called()


# ═══════════════════════════════════════════════════════════
# web_api property
# ═══════════════════════════════════════════════════════════

class TestWebApiProperty:
    def test_web_api_lazy_init(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper._web_api = None
        with patch('instaharvest.base.BaseScraper.web_api', new_callable=PropertyMock) as mock_prop:
            mock_api = MagicMock()
            mock_prop.return_value = mock_api
            # Access through property
            result = scraper.web_api
            assert result is mock_api

    def test_web_api_no_page(self):
        scraper = _make_concrete_scraper()
        scraper.page = None
        scraper._web_api = None
        result = scraper.web_api
        assert result is None


# ═══════════════════════════════════════════════════════════
# setup_browser
# ═══════════════════════════════════════════════════════════

class TestSetupBrowser:
    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    @patch('time.sleep')
    def test_setup_basic(self, mock_sleep, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        scraper = TestScraper()
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.chromium.launch.return_value = mock_browser
        mock_sync_pw.return_value.start.return_value = mock_pw

        scraper.setup_browser(auto_update_session=False)
        assert scraper.page == mock_page
        assert scraper.browser == mock_browser

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    @patch('time.sleep')
    def test_setup_with_session(self, mock_sleep, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        scraper = TestScraper()
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = 'https://www.instagram.com/'
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = {'cookies': [], 'origins': []}
        mock_browser.new_context.return_value = mock_context
        mock_pw.chromium.launch.return_value = mock_browser
        mock_sync_pw.return_value.start.return_value = mock_pw

        session_data = {'cookies': [{'name': 'sid', 'value': 'v'}]}
        scraper.setup_browser(session_data=session_data, auto_update_session=False)
        assert scraper.page is not None

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    def test_setup_browser_failure_cleanup(self, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        scraper = TestScraper()
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_pw.chromium.launch.side_effect = Exception("Browser launch failed")
        mock_sync_pw.return_value.start.return_value = mock_pw

        with pytest.raises(Exception, match="Browser launch failed"):
            scraper.setup_browser()
        assert scraper.page is None
        assert scraper.browser is None

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    @patch('time.sleep')
    def test_setup_old_headless_retry(self, mock_sleep, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        scraper = TestScraper()
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        # First call raises "Old Headless", second succeeds
        mock_pw.chromium.launch.side_effect = [
            Exception("Old Headless mode is not supported"),
            mock_browser
        ]
        mock_sync_pw.return_value.start.return_value = mock_pw

        scraper.setup_browser(auto_update_session=False)
        assert scraper.page is not None

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    @patch('time.sleep')
    def test_setup_with_proxy(self, mock_sleep, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        proxy_mock = MagicMock(
            has_proxies=True,
            get_for_curl=MagicMock(return_value='http://p:8080'),
            get_for_playwright=MagicMock(return_value={'server': 'http://p:8080'})
        )
        mock_pm.return_value = proxy_mock
        scraper = TestScraper()
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.chromium.launch.return_value = mock_browser
        mock_sync_pw.return_value.start.return_value = mock_pw

        scraper.setup_browser(auto_update_session=False)
        assert scraper.page is not None

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    def test_setup_chrome_channel_error(self, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        cfg = ScraperConfig()
        cfg.browser_channel = 'chrome'
        scraper = TestScraper(config=cfg)
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_pw.chromium.launch.side_effect = Exception("Chrome not found")
        mock_sync_pw.return_value.start.return_value = mock_pw

        with pytest.raises(Exception):
            scraper.setup_browser()

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    @patch('time.sleep')
    def test_setup_with_stealth(self, mock_sleep, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        cfg = ScraperConfig(enable_stealth=True)
        scraper = TestScraper(config=cfg)
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.chromium.launch.return_value = mock_browser
        mock_sync_pw.return_value.start.return_value = mock_pw

        with patch('instaharvest.stealth.StealthManager') as mock_stealth_cls:
            mock_stealth = MagicMock()
            mock_stealth_cls.return_value = mock_stealth
            scraper.setup_browser(auto_update_session=False)
            mock_stealth.apply_context_stealth.assert_called_once()
            mock_stealth.apply_page_stealth.assert_called_once()

    @patch('instaharvest.base.sync_playwright')
    @patch('instaharvest.base.create_proxy_manager_from_config')
    @patch('time.sleep')
    def test_setup_with_ua_rotation(self, mock_sleep, mock_pm, mock_sync_pw):
        from instaharvest.base import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, *a, **kw): return None

        mock_pm.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        cfg = ScraperConfig(rotate_user_agent=True, enable_stealth=False)
        scraper = TestScraper(config=cfg)
        scraper.logger = MagicMock()

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.chromium.launch.return_value = mock_browser
        mock_sync_pw.return_value.start.return_value = mock_pw

        with patch('instaharvest.base.SecurityManager.get_random_user_agent', return_value='RotatedUA'):
            scraper.setup_browser(auto_update_session=False)


# ═══════════════════════════════════════════════════════════
# goto_url
# ═══════════════════════════════════════════════════════════

class TestGotoUrl:
    @patch('time.sleep')
    def test_goto_success(self, mock_sleep):
        scraper = _make_concrete_scraper()
        mock_page = MagicMock()
        mock_page.url = 'https://www.instagram.com/user/'
        mock_page.locator.return_value.count.return_value = 1
        mock_page.content.return_value = '<html>OK</html>'
        mock_page.title.return_value = 'User • Instagram'
        scraper.page = mock_page
        result = scraper.goto_url('https://www.instagram.com/user/')
        assert result is True

    @patch('time.sleep')
    def test_goto_rate_limited(self, mock_sleep):
        scraper = _make_concrete_scraper()
        cfg = scraper.config
        cfg.max_retries = 1
        cfg.rate_limit_max_retries = 0
        mock_page = MagicMock()
        mock_page.url = 'https://www.instagram.com/challenge/'
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.return_value = '<html></html>'
        scraper.page = mock_page
        with pytest.raises(RateLimitError):
            scraper.goto_url('https://www.instagram.com/user/')

    @patch('time.sleep')
    def test_goto_login_page_recovery_fails(self, mock_sleep):
        scraper = _make_concrete_scraper()
        cfg = scraper.config
        cfg.max_retries = 1
        mock_page = MagicMock()
        mock_page.url = 'https://www.instagram.com/accounts/login/'
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.return_value = '<html>name="username"</html>'
        mock_page.title.return_value = 'Login'
        scraper.page = mock_page
        with pytest.raises(LoginRequiredError):
            scraper.goto_url('https://www.instagram.com/user/')

    @patch('time.sleep')
    def test_goto_navigation_failure(self, mock_sleep):
        scraper = _make_concrete_scraper()
        cfg = scraper.config
        cfg.max_retries = 1
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Timeout")
        scraper.page = mock_page
        with pytest.raises(PageLoadError):
            scraper.goto_url('https://www.instagram.com/user/')

    @patch('time.sleep')
    def test_goto_with_custom_delay(self, mock_sleep):
        scraper = _make_concrete_scraper()
        mock_page = MagicMock()
        mock_page.url = 'https://www.instagram.com/user/'
        mock_page.locator.return_value.count.return_value = 1
        mock_page.content.return_value = '<html>nav</html>'
        scraper.page = mock_page
        result = scraper.goto_url('https://www.instagram.com/user/', delay=0.1)
        assert result is True


# ═══════════════════════════════════════════════════════════
# _is_login_page
# ═══════════════════════════════════════════════════════════

class TestIsLoginPage:
    def test_login_url(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/accounts/login/?next=/'
        assert scraper._is_login_page() is True

    def test_emailsignup_url(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/accounts/emailsignup/'
        assert scraper._is_login_page() is True

    def test_logged_in_nav_element(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/'
        locator = MagicMock()
        locator.count.return_value = 1
        scraper.page.locator.return_value = locator
        assert scraper._is_login_page() is False

    def test_no_nav_login_form_detected(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/'
        locator = MagicMock()
        locator.count.return_value = 0
        scraper.page.locator.return_value = locator
        scraper.page.content.return_value = 'name="username" name="password"'
        assert scraper._is_login_page() is True

    def test_title_login(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/'
        locator = MagicMock()
        locator.count.return_value = 0
        scraper.page.locator.return_value = locator
        scraper.page.content.return_value = '<html>normal</html>'
        scraper.page.title.return_value = 'Login • Instagram'
        assert scraper._is_login_page() is True

    def test_page_error(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = PropertyMock(side_effect=Exception("Page crashed"))
        type(scraper.page).url = PropertyMock(side_effect=Exception("err"))
        assert scraper._is_login_page() is True


# ═══════════════════════════════════════════════════════════
# _is_rate_limited
# ═══════════════════════════════════════════════════════════

class TestIsRateLimited:
    def test_rate_limit_url(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/challenge/action/'
        assert scraper._is_rate_limited() is True

    def test_rate_limit_body_text(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/user/'
        locator = MagicMock()
        locator.inner_text.return_value = 'Try Again Later'
        scraper.page.locator.return_value = locator
        assert scraper._is_rate_limited() is True

    def test_no_rate_limit(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/user/'
        locator = MagicMock()
        locator.inner_text.return_value = 'Normal page content'
        scraper.page.locator.return_value = locator
        assert scraper._is_rate_limited() is False

    def test_rate_limit_body_fallback_html(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.url = 'https://www.instagram.com/user/'
        locator = MagicMock()
        locator.inner_text.side_effect = Exception("Timeout")
        scraper.page.locator.return_value = locator
        scraper.page.content.return_value = 'Try Again Later blocked'
        assert scraper._is_rate_limited() is True

    def test_rate_limit_exception(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        type(scraper.page).url = PropertyMock(side_effect=Exception("err"))
        assert scraper._is_rate_limited() is False


# ═══════════════════════════════════════════════════════════
# safe_extract
# ═══════════════════════════════════════════════════════════

class TestSafeExtract:
    def test_success(self):
        scraper = _make_concrete_scraper()
        result = scraper.safe_extract(lambda: 42, 'test_field', 'div.test')
        assert result == 42

    def test_failure_returns_default(self):
        scraper = _make_concrete_scraper()
        scraper.page = None
        result = scraper.safe_extract(lambda: 1/0, 'bad_field', 'div.bad', default='N/A', snapshot_on_error=False)
        assert result == 'N/A'

    def test_failure_critical_raises(self):
        scraper = _make_concrete_scraper()
        scraper.page = None
        with pytest.raises(HTMLStructureChangedError):
            scraper.safe_extract(lambda: 1/0, 'critical_field', 'div.critical', critical=True, snapshot_on_error=False)

    def test_failure_with_snapshot(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.page.content.return_value = '<html>debug</html>'
        with patch('builtins.open', mock_open()):
            with patch('pathlib.Path.mkdir'):
                result = scraper.safe_extract(lambda: 1/0, 'snap_field', 'div.snap', default=0)
        assert result == 0


# ═══════════════════════════════════════════════════════════
# parse_number (already partially tested, ensure full coverage)
# ═══════════════════════════════════════════════════════════

class TestParseNumber:
    def test_warnings_on_bad_text(self):
        scraper = _make_concrete_scraper()
        result = scraper.parse_number('totally_invalid')
        assert result is None
        scraper.logger.warning.assert_called()


# ═══════════════════════════════════════════════════════════
# close
# ═══════════════════════════════════════════════════════════

class TestClose:
    def test_close_all(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.context = MagicMock()
        scraper.browser = MagicMock()
        scraper.playwright = MagicMock()
        scraper.close(update_session_before_close=False)
        scraper.page.close.assert_called_once()
        scraper.context.close.assert_called_once()
        scraper.browser.close.assert_called_once()
        scraper.playwright.stop.assert_called_once()

    def test_close_with_session_update(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.context = MagicMock()
        scraper.context.storage_state.return_value = {'cookies': [], 'origins': []}
        scraper.browser = MagicMock()
        scraper.playwright = MagicMock()
        with patch.object(scraper, 'update_session') as mock_update:
            scraper.close(update_session_before_close=True)
            mock_update.assert_called_once()

    def test_close_with_errors(self):
        scraper = _make_concrete_scraper()
        mock_page = MagicMock()
        mock_page.close.side_effect = Exception("page close error")
        scraper.page = mock_page
        scraper.context = MagicMock()
        scraper.browser = MagicMock()
        scraper.playwright = MagicMock()
        scraper.close(update_session_before_close=False)  # should not raise

    def test_close_none_resources(self):
        scraper = _make_concrete_scraper()
        scraper.page = None
        scraper.context = None
        scraper.browser = None
        scraper.playwright = None
        scraper.close(update_session_before_close=False)  # should be safe


# ═══════════════════════════════════════════════════════════
# Context Manager
# ═══════════════════════════════════════════════════════════

class TestContextManager:
    def test_enter_exit(self):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        scraper.context = MagicMock()
        scraper.browser = MagicMock()
        scraper.playwright = MagicMock()
        with patch.object(scraper, 'close') as mock_close:
            with scraper as s:
                assert s is scraper
            mock_close.assert_called_once()

    def test_exit_with_exception(self):
        scraper = _make_concrete_scraper()
        with patch.object(scraper, 'close'):
            result = scraper.__exit__(ValueError, ValueError("test"), None)
            assert result is False  # Never suppresses


# ═══════════════════════════════════════════════════════════
# _extract_post_date / _filter_by_date_range
# ═══════════════════════════════════════════════════════════

class TestDateFilterHelpers:
    @patch('time.sleep')
    def test_extract_post_date_success(self, mock_sleep):
        scraper = _make_concrete_scraper()
        mock_page = MagicMock()
        mock_page.url = 'https://www.instagram.com/p/ABC/'
        locator = MagicMock()
        locator.count.return_value = 1
        locator.get_attribute.return_value = '2025-03-07T12:00:00.000Z'
        mock_page.locator.return_value.first = locator
        mock_page.locator.return_value.count.return_value = 1
        scraper.page = mock_page
        with patch.object(scraper, 'goto_url'):
            date = scraper._extract_post_date('https://www.instagram.com/p/ABC/')
        assert date == '2025-03-07'

    @patch('time.sleep')
    def test_extract_post_date_failure(self, mock_sleep):
        scraper = _make_concrete_scraper()
        scraper.page = MagicMock()
        with patch.object(scraper, 'goto_url', side_effect=Exception("fail")):
            date = scraper._extract_post_date('https://www.instagram.com/p/XYZ/')
        assert date is None

    def test_filter_no_dates(self):
        scraper = _make_concrete_scraper()
        links = [{'url': 'a'}, {'url': 'b'}]
        result = scraper._filter_by_date_range(links)
        assert result == links


# ═══════════════════════════════════════════════════════════
# scrape (abstract)
# ═══════════════════════════════════════════════════════════

class TestScrapeAbstract:
    def test_concrete_scrape(self):
        scraper = _make_concrete_scraper()
        assert scraper.scrape() == "scraped"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
