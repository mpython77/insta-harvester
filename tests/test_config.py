"""
Unit Tests — ScraperConfig
Covers: defaults, overrides, list/dict fields, immutability of defaults
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from instaharvest.config import ScraperConfig


class TestScraperConfigDefaults:
    """Verify all default values are correct"""

    def test_session_file(self):
        c = ScraperConfig()
        assert c.session_file == 'instagram_session.json'

    def test_headless_default(self):
        c = ScraperConfig()
        assert c.headless is True

    def test_viewport(self):
        c = ScraperConfig()
        assert c.viewport_width == 1280
        assert c.viewport_height == 720

    def test_proxy_defaults(self):
        c = ScraperConfig()
        assert c.proxy_url is None
        assert c.proxies == []
        assert c.proxy_rotation is True
        assert c.proxy_rotation_interval == 10

    def test_stealth_defaults(self):
        c = ScraperConfig()
        assert c.enable_stealth is True
        assert c.stealth_level == 'aggressive'
        assert c.mask_webgl is True
        assert c.human_like_mouse is True

    def test_timeout_defaults(self):
        c = ScraperConfig()
        assert c.default_timeout == 60000
        assert c.navigation_timeout == 60000
        assert c.element_timeout == 10000

    def test_delay_defaults(self):
        c = ScraperConfig()
        assert c.page_load_delay == 2.0
        assert c.button_click_delay == 2.5
        assert c.popup_open_delay == 2.5

    def test_rate_limit_defaults(self):
        c = ScraperConfig()
        assert c.rate_limit_cooldown == 300.0
        assert c.rate_limit_max_retries == 2
        assert len(c.rate_limit_indicators) > 5

    def test_number_suffixes(self):
        c = ScraperConfig()
        assert c.number_suffixes['K'] == 1000
        assert c.number_suffixes['M'] == 1000000
        assert c.number_suffixes['ming'] == 1000  # Uzbek

    def test_url_patterns(self):
        c = ScraperConfig()
        assert '{username}' in c.profile_url_pattern
        assert '{username}' in c.reels_url_pattern

    def test_comment_scraping_defaults(self):
        c = ScraperConfig()
        assert c.scrape_comments is False
        assert c.scrape_comment_replies is True
        assert c.max_comments_per_post is None

    def test_log_defaults(self):
        c = ScraperConfig()
        assert c.log_level == 'INFO'
        assert c.log_emoji_enabled is True


class TestScraperConfigOverrides:
    """Test custom config creation"""

    def test_custom_headless(self):
        c = ScraperConfig(headless=False)
        assert c.headless is False

    def test_custom_proxy(self):
        c = ScraperConfig(proxy_url='http://user:pass@1.2.3.4:8080')
        assert c.proxy_url == 'http://user:pass@1.2.3.4:8080'

    def test_custom_delays(self):
        c = ScraperConfig(page_load_delay=5.0, button_click_delay=3.0)
        assert c.page_load_delay == 5.0
        assert c.button_click_delay == 3.0

    def test_custom_timeout(self):
        c = ScraperConfig(default_timeout=120000)
        assert c.default_timeout == 120000

    def test_custom_session_file(self):
        c = ScraperConfig(session_file='my_session.json')
        assert c.session_file == 'my_session.json'


class TestScraperConfigListIsolation:
    """Ensure list/dict defaults don't share between instances"""

    def test_rate_limit_indicators_isolated(self):
        c1 = ScraperConfig()
        c2 = ScraperConfig()
        c1.rate_limit_indicators.append('Custom Block Text')
        assert 'Custom Block Text' not in c2.rate_limit_indicators

    def test_proxies_isolated(self):
        c1 = ScraperConfig()
        c2 = ScraperConfig()
        c1.proxies.append('http://proxy1:8080')
        assert len(c2.proxies) == 0

    def test_number_suffixes_isolated(self):
        c1 = ScraperConfig()
        c2 = ScraperConfig()
        c1.number_suffixes['X'] = 999
        assert 'X' not in c2.number_suffixes


class TestScraperConfigSelectors:
    """CSS selectors should be non-empty strings"""

    def test_profile_selectors(self):
        c = ScraperConfig()
        assert len(c.selector_posts_count) > 0
        assert len(c.selector_followers_link) > 0
        assert len(c.selector_following_link) > 0

    def test_comment_selectors(self):
        c = ScraperConfig()
        assert len(c.selector_comment_thread) > 0
        assert len(c.selector_comment_username_link) > 0

    def test_like_selectors(self):
        c = ScraperConfig()
        assert len(c.selector_likes_options) > 0
        assert len(c.selector_like_svg) > 0

    def test_notification_selectors(self):
        c = ScraperConfig()
        assert len(c.selector_notif_item) > 0
        assert len(c.notification_url) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
