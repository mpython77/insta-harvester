"""
Shared pytest fixtures for instaharvest test suite.
Provides mock objects for Playwright, NetworkClient, Config, and BaseScraper factory.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from instaharvest.config import ScraperConfig


# ═══════════════════════════════════════════════════════════
# Core Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_config():
    """Default ScraperConfig for testing"""
    return ScraperConfig()


@pytest.fixture
def mock_logger():
    """MagicMock logger"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    return logger


# ═══════════════════════════════════════════════════════════
# Playwright Mock Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_locator():
    """Mock Playwright Locator"""
    locator = MagicMock()
    locator.count.return_value = 0
    locator.first = locator
    locator.inner_text.return_value = ''
    locator.get_attribute.return_value = None
    locator.is_visible.return_value = True
    locator.text_content.return_value = ''
    locator.all_inner_texts.return_value = []
    locator.all_text_contents.return_value = []
    locator.nth.return_value = locator
    return locator


@pytest.fixture
def mock_page(mock_locator):
    """Mock Playwright Page"""
    page = MagicMock()
    page.url = 'https://www.instagram.com/testuser/'
    page.title.return_value = 'testuser • Instagram'
    page.content.return_value = '<html><body>Test</body></html>'
    page.locator.return_value = mock_locator
    page.query_selector.return_value = None
    page.query_selector_all.return_value = []
    page.goto.return_value = None
    page.evaluate.return_value = None
    page.wait_for_selector.return_value = mock_locator
    page.wait_for_timeout.return_value = None
    page.set_default_timeout.return_value = None
    page.keyboard = MagicMock()
    page.mouse = MagicMock()
    page.close.return_value = None
    page.screenshot.return_value = b'fake_screenshot'
    return page


@pytest.fixture
def mock_context(mock_page):
    """Mock Playwright BrowserContext"""
    context = MagicMock()
    context.new_page.return_value = mock_page
    context.cookies.return_value = [
        {'name': 'sessionid', 'value': 'test123', 'domain': '.instagram.com', 'path': '/'}
    ]
    context.storage_state.return_value = {
        'cookies': [{'name': 'sessionid', 'value': 'test123'}],
        'origins': []
    }
    context.close.return_value = None
    context.add_init_script.return_value = None
    return context


@pytest.fixture
def mock_browser(mock_context):
    """Mock Playwright Browser"""
    browser = MagicMock()
    browser.new_context.return_value = mock_context
    browser.close.return_value = None
    return browser


@pytest.fixture
def mock_playwright(mock_browser):
    """Mock Playwright instance"""
    pw = MagicMock()
    pw.chromium.launch.return_value = mock_browser
    pw.stop.return_value = None
    return pw


# ═══════════════════════════════════════════════════════════
# BaseScraper Factory
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def make_scraper(mock_page, mock_context, mock_browser, mock_playwright, mock_logger, mock_config):
    """
    Factory fixture: creates any BaseScraper subclass with mocked browser stack.
    
    Usage:
        scraper = make_scraper(ProfileScraper)
        # or with custom config:
        scraper = make_scraper(ProfileScraper, config=my_config)
    """
    def _factory(scraper_class, config=None):
        cfg = config or mock_config
        with patch('instaharvest.base.sync_playwright'), \
             patch('instaharvest.base.create_proxy_manager_from_config') as mock_proxy_mgr:
            mock_proxy_mgr.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
            scraper = scraper_class(config=cfg)
        scraper.playwright = mock_playwright
        scraper.browser = mock_browser
        scraper.context = mock_context
        scraper.page = mock_page
        scraper.logger = mock_logger
        scraper._web_api = None
        return scraper
    return _factory


# ═══════════════════════════════════════════════════════════
# Network Mock
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_network_client():
    """Mock NetworkClient"""
    client = MagicMock()
    client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={}), text='{}')
    client.post.return_value = MagicMock(status_code=200, json=MagicMock(return_value={}))
    client.download_media.return_value = True
    client.set_cookies.return_value = None
    return client


# ═══════════════════════════════════════════════════════════
# Session Data Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def sample_session_data():
    """Sample session data dict"""
    return {
        'cookies': [
            {'name': 'sessionid', 'value': 'test_session_123', 'domain': '.instagram.com', 'path': '/'},
            {'name': 'csrftoken', 'value': 'csrf_test_456', 'domain': '.instagram.com', 'path': '/'},
            {'name': 'ds_user_id', 'value': '12345678', 'domain': '.instagram.com', 'path': '/'},
        ],
        'origins': []
    }
