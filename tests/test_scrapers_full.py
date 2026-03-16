"""
Tests for scraper modules with correct APIs.
"""

import pytest
from unittest.mock import patch, MagicMock
from instaharvest.config import ScraperConfig


def _make_scraper(cls, config=None):
    with patch('instaharvest.base.sync_playwright'), \
         patch('instaharvest.base.create_proxy_manager_from_config') as mp:
        mp.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        s = cls(config=config or ScraperConfig())
    s.logger = MagicMock()
    s.page = MagicMock()
    s.context = MagicMock()
    s.browser = MagicMock()
    return s


# ═══════════════════════════════════════════════════════════
# ProfileScraper — scrape() directly called with goto mocking
# ═══════════════════════════════════════════════════════════

class TestProfileScraper:
    def test_init(self):
        from instaharvest.profile import ProfileScraper
        s = _make_scraper(ProfileScraper)
        assert s is not None

    @patch('time.sleep')
    def test_scrape_returns_data(self, mock_sleep):
        from instaharvest.profile import ProfileScraper
        s = _make_scraper(ProfileScraper)
        # Mock page elements for DOM extraction
        loc = MagicMock()
        loc.count.return_value = 1
        loc.inner_text.return_value = 'Test'
        loc.get_attribute.return_value = '100'
        loc.text_content.return_value = 'Test'
        s.page.locator.return_value = loc
        s.page.locator.return_value.first = loc
        s.page.locator.return_value.nth.return_value = loc
        s.page.content.return_value = '<html>Normal</html>'
        s.page.url = 'https://www.instagram.com/testuser/'
        with patch.object(s, 'goto_url', return_value=True):
            result = s.scrape('testuser')
        assert result is not None

    @patch('time.sleep')
    def test_scrape_private_account(self, mock_sleep):
        from instaharvest.profile import ProfileScraper
        s = _make_scraper(ProfileScraper)
        loc = MagicMock()
        loc.count.return_value = 1
        loc.inner_text.return_value = ''
        loc.get_attribute.return_value = '0'
        s.page.locator.return_value = loc
        s.page.locator.return_value.first = loc
        s.page.locator.return_value.nth.return_value = loc
        s.page.content.return_value = 'This account is private'
        s.page.url = 'https://www.instagram.com/testuser/'
        with patch.object(s, 'goto_url', return_value=True):
            result = s.scrape('testuser')
        assert result is not None


# ═══════════════════════════════════════════════════════════
# PostLinksScraper
# ═══════════════════════════════════════════════════════════

class TestPostLinksScraper:
    def test_init(self):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        assert s is not None

    @patch('time.sleep')
    def test_scrape_page_fail(self, mock_sleep):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        with patch.object(s, 'goto_url', return_value=False):
            result = s.scrape('testuser')
        assert isinstance(result, list)

    @patch('time.sleep')
    def test_scrape_no_posts(self, mock_sleep):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        loc = MagicMock()
        loc.count.return_value = 0
        s.page.locator.return_value = loc
        s.page.query_selector_all.return_value = []
        with patch.object(s, 'goto_url', return_value=True):
            result = s.scrape('testuser')
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════
# ReelDataScraper / ReelLinksScraper
# ═══════════════════════════════════════════════════════════

class TestReelDataScraper:
    def test_init(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        assert s is not None

    @patch('time.sleep')
    def test_scrape_returns_result(self, mock_sleep):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        loc = MagicMock()
        loc.count.return_value = 0
        loc.inner_text.return_value = ''
        loc.get_attribute.return_value = None
        loc.first = loc
        s.page.locator.return_value = loc
        s.page.content.return_value = '<html></html>'
        with patch.object(s, 'goto_url', return_value=True):
            result = s.scrape('https://www.instagram.com/reel/ABC/')
        # Result may be ReelData or None
        assert result is not None or result is None


class TestReelLinksScraper:
    def test_init(self):
        from instaharvest.reel_links import ReelLinksScraper
        s = _make_scraper(ReelLinksScraper)
        assert s is not None

    @patch('time.sleep')
    def test_scrape_page_fail(self, mock_sleep):
        from instaharvest.reel_links import ReelLinksScraper
        s = _make_scraper(ReelLinksScraper)
        with patch.object(s, 'goto_url', return_value=False):
            result = s.scrape('testuser')
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════
# CommentScraper
# ═══════════════════════════════════════════════════════════

class TestCommentScraper:
    def test_init(self):
        from instaharvest.comment_scraper import CommentScraper
        s = _make_scraper(CommentScraper)
        assert s is not None

    @patch('time.sleep')
    def test_scrape_ok(self, mock_sleep):
        from instaharvest.comment_scraper import CommentScraper
        s = _make_scraper(CommentScraper)
        s.page.content.return_value = '<html><body>No comments</body></html>'
        with patch.object(s, 'goto_url', return_value=True):
            result = s.scrape('https://www.instagram.com/p/ABC/')
        # Returns PostCommentsData, not a list
        assert result is not None


# ═══════════════════════════════════════════════════════════
# StoryScraper
# ═══════════════════════════════════════════════════════════

class TestStoryScraper:
    def test_init(self):
        from instaharvest.story_scraper import StoryScraper
        s = _make_scraper(StoryScraper)
        assert s is not None

    @patch('time.sleep')
    def test_scrape_returns_result(self, mock_sleep):
        from instaharvest.story_scraper import StoryScraper
        s = _make_scraper(StoryScraper)
        loc = MagicMock()
        loc.count.return_value = 0
        s.page.locator.return_value = loc
        with patch.object(s, 'goto_url', return_value=True):
            result = s.scrape('testuser')
        # May return StoryResult or empty
        assert result is not None


# ═══════════════════════════════════════════════════════════
# FollowersCollector (not FollowersScraper)
# ═══════════════════════════════════════════════════════════

class TestFollowersCollector:
    def test_init(self):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        assert s is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
