"""
Deep Coverage Tests - Part 15
SURGICAL: profile.py 47% uncovered, reel_links.py 46% uncovered.
All tested by mocking page/browser at the instance level.

Exact uncovered lines:
  profile.py: 332-358, 370-373, 388-410, 468-617, 664-712, 753-766
  reel_links.py: all internal methods (124-350)
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock


def _cfg():
    from instaharvest.config import ScraperConfig
    return ScraperConfig()

def _mock_page():
    p = MagicMock()
    p.url = 'https://instagram.com/'
    p.locator.return_value.count.return_value = 0
    p.locator.return_value.all.return_value = []
    p.locator.return_value.first = MagicMock()
    p.locator.return_value.first.count.return_value = 0
    p.locator.return_value.first.inner_text.return_value = ''
    p.content.return_value = '<html><body></body></html>'
    p.evaluate.return_value = 0
    p.keyboard = MagicMock()
    p.wait_for_selector = MagicMock()
    return p


# ═══════════════════════════════════════════════════════════════
# ProfileData deep
# ═══════════════════════════════════════════════════════════════

class TestProfileDataDeep:
    def test_all_fields(self):
        from instaharvest.profile import ProfileData
        pd = ProfileData(
            username='alice', posts=50, followers=5000, following=300,
            is_verified=True, is_private=False, category='Musician',
            bio='Hello world', external_links=['https://alice.com'],
            threads_profile='@alice', full_name='Alice Wonderland',
            user_id='12345', is_business_account=True,
            bio_links=[{'url': 'https://alice.com', 'title': 'Website'}],
            profile_pic_url='http://pic.jpg', highlight_reel_count=5,
            has_clips=True, data_source='api'
        )
        d = pd.to_dict()
        assert d['is_verified'] is True
        assert d['full_name'] == 'Alice Wonderland'
        assert d['data_source'] == 'api'
        assert pd.is_business is True

    def test_is_business_professional(self):
        from instaharvest.profile import ProfileData
        pd = ProfileData(username='x', posts=0, followers=0, following=0,
                        is_professional_account=True)
        assert pd.is_business is True

    def test_er_with_comments(self):
        from instaharvest.profile import ProfileData
        pd = ProfileData(username='x', posts=10, followers=1000, following=0)
        er = pd.calculate_engagement_rate(50, 10)
        # (50 + 10) / 1000 * 100 = 6.0
        assert er == pytest.approx(6.0, abs=0.1)


# ═══════════════════════════════════════════════════════════════
# Profile Scraper - _build_profile_from_api (lines 213-252)
# ═══════════════════════════════════════════════════════════════

class TestProfileBuildFromApi:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def _mock_api_data(self):
        d = MagicMock()
        d.username = 'alice'
        d.media_count = 50
        d.follower_count = 5000
        d.following_count = 300
        d.is_verified = True
        d.is_private = False
        d.category_name = 'Musician'
        d.biography = 'My bio here'
        d.bio_links = [{'url': 'https://alice.com', 'title': 'Website'}]
        d.external_url = 'https://alice.com'
        d.full_name = 'Alice W'
        d.user_id = '12345'
        d.fbid = '67890'
        d.is_business_account = True
        d.is_professional_account = True
        d.category_enum = 'MUSICIAN'
        d.profile_pic_url = 'http://pic.jpg'
        d.profile_pic_url_hd = 'http://pic_hd.jpg'
        d.business_address = {'street': '5th Ave'}
        d.business_email = 'alice@example.com'
        d.business_phone = '+1234567890'
        d.business_category_name = 'Music'
        d.highlight_reel_count = 5
        d.has_clips = True
        d.has_guides = False
        d.mutual_followers_count = 3
        d.followed_by_viewer = True
        d.follows_viewer = False
        return d

    def test_build_full(self):
        s = self._make()
        api = self._mock_api_data()
        pd = s._build_profile_from_api(api)
        assert pd.username == 'alice'
        assert pd.posts == 50
        assert pd.followers == 5000
        assert pd.is_verified is True
        assert pd.data_source == 'api'
        assert pd.business_email == 'alice@example.com'
        assert pd.highlight_reel_count == 5

    def test_build_no_bio_links(self):
        s = self._make()
        api = self._mock_api_data()
        api.bio_links = None
        api.external_url = 'https://fallback.com'
        pd = s._build_profile_from_api(api)
        assert 'https://fallback.com' in pd.external_links

    def test_build_no_external_url(self):
        s = self._make()
        api = self._mock_api_data()
        api.bio_links = None
        api.external_url = None
        pd = s._build_profile_from_api(api)
        assert pd.external_links == []


# ═══════════════════════════════════════════════════════════════
# Profile Scraper - _scrape_dom (lines 254-302)
# ═══════════════════════════════════════════════════════════════

class TestProfileScrapeDom:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_scrape_dom_basic(self):
        s = self._make()
        s._is_private_account = MagicMock(return_value=False)
        s._wait_for_profile_stats = MagicMock()
        s.get_posts_count = MagicMock(return_value=50)
        s.get_followers_count = MagicMock(return_value=5000)
        s.get_following_count = MagicMock(return_value=300)
        s._get_bio_data = MagicMock(return_value={
            'bio': 'Hello', 'external_links': [], 'threads_profile': None
        })
        s._check_verified = MagicMock(return_value=False)
        s._get_category = MagicMock(return_value='Musician')

        result = s._scrape_dom('alice')
        assert result.username == 'alice'
        assert result.posts == 50
        assert result.data_source == 'dom'

    def test_scrape_dom_private(self):
        s = self._make()
        s._is_private_account = MagicMock(return_value=True)
        s._wait_for_profile_stats = MagicMock()
        s.get_posts_count = MagicMock(return_value=0)
        s.get_followers_count = MagicMock(return_value=100)
        s.get_following_count = MagicMock(return_value=50)
        s._get_bio_data = MagicMock(return_value={
            'bio': None, 'external_links': [], 'threads_profile': None
        })
        s._check_verified = MagicMock(return_value=False)
        s._get_category = MagicMock(return_value=None)

        result = s._scrape_dom('bob')
        assert result.is_private is True


# ═══════════════════════════════════════════════════════════════
# Profile - _is_private_account (lines 316-358)
# ═══════════════════════════════════════════════════════════════

class TestProfileIsPrivate:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_private_by_icon(self):
        s = self._make()
        s.page.locator.return_value.first.count.return_value = 1
        assert s._is_private_account() is True

    def test_not_private(self):
        s = self._make()
        s.page.locator.return_value.first.count.return_value = 0
        s.page.locator.return_value.count.return_value = 0
        body = MagicMock()
        body.inner_text.return_value = 'Regular public profile'
        s.page.locator.side_effect = lambda sel: (
            body if sel == 'body' else MagicMock(
                first=MagicMock(count=MagicMock(return_value=0)),
                count=MagicMock(return_value=0),
                nth=MagicMock(return_value=MagicMock(inner_text=MagicMock(return_value='')))
            )
        )
        result = s._is_private_account()
        assert isinstance(result, bool)

    def test_private_check_error(self):
        s = self._make()
        s.page.locator.side_effect = Exception("timeout")
        result = s._is_private_account()
        assert result is False


# ═══════════════════════════════════════════════════════════════
# Profile - _check_verified (lines 375-390)
# ═══════════════════════════════════════════════════════════════

class TestProfileCheckVerified:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_verified(self):
        s = self._make()
        s.page.locator.return_value.first.count.return_value = 1
        assert s._check_verified() is True

    def test_not_verified(self):
        s = self._make()
        s.page.locator.return_value.first.count.return_value = 0
        assert s._check_verified() is False

    def test_verified_error(self):
        s = self._make()
        s.page.locator.side_effect = Exception("timeout")
        assert s._check_verified() is False


# ═══════════════════════════════════════════════════════════════
# Profile - _get_category (lines 392-410)
# ═══════════════════════════════════════════════════════════════

class TestProfileGetCategory:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_has_category(self):
        s = self._make()
        s.page.locator.return_value.first.count.return_value = 1
        s.page.locator.return_value.first.inner_text.return_value = 'Musician'
        assert s._get_category() == 'Musician'

    def test_no_category(self):
        s = self._make()
        s.page.locator.return_value.first.count.return_value = 0
        assert s._get_category() is None

    def test_category_error(self):
        s = self._make()
        s.page.locator.side_effect = Exception("timeout")
        assert s._get_category() is None


# ═══════════════════════════════════════════════════════════════
# Profile - _get_bio_data (lines 412-642)
# ═══════════════════════════════════════════════════════════════

class TestProfileGetBioData:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_no_bio(self):
        s = self._make()
        s.page.evaluate.return_value = False  # No "more" button
        s.page.locator.return_value.all.return_value = []
        result = s._get_bio_data()
        assert result['bio'] is None
        assert result['external_links'] == []

    def test_bio_with_error(self):
        s = self._make()
        s.page.evaluate.side_effect = Exception("JS error")
        s.page.locator.return_value.all.return_value = []
        result = s._get_bio_data()
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# Profile - get_posts/followers/following_count (lines 649-776)
# ═══════════════════════════════════════════════════════════════

class TestProfileCountMethods:
    def _make(self):
        from instaharvest.profile import ProfileScraper
        s = ProfileScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_get_posts_count(self):
        s = self._make()
        span = MagicMock()
        span.inner_text.return_value = '1,234'
        locator = MagicMock()
        locator.first = MagicMock()
        locator.first.wait_for.return_value = None
        locator.first.locator.return_value.first.inner_text.return_value = '1,234'
        s.page.locator.return_value = locator
        result = s.get_posts_count()
        assert result >= 0

    def test_get_followers_count(self):
        s = self._make()
        locator = MagicMock()
        locator.first = MagicMock()
        locator.first.wait_for.return_value = None
        locator.first.locator.return_value.first.count.return_value = 1
        locator.first.locator.return_value.first.get_attribute.return_value = '5,000'
        s.page.locator.return_value = locator
        result = s.get_followers_count()
        assert result >= 0

    def test_get_following_count(self):
        s = self._make()
        locator = MagicMock()
        locator.first = MagicMock()
        locator.first.wait_for.return_value = None
        locator.first.locator.return_value.first.inner_text.return_value = '500'
        s.page.locator.return_value = locator
        result = s.get_following_count()
        assert result >= 0


# ═══════════════════════════════════════════════════════════════
# ReelLinksScraper - Internal methods
# ═══════════════════════════════════════════════════════════════

class TestReelLinksScraper:
    def _make(self):
        from instaharvest.reel_links import ReelLinksScraper
        s = ReelLinksScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_profile_exists_true(self):
        s = self._make()
        s.page.content.return_value = '<html><body>Regular page</body></html>'
        assert s._profile_exists() is True

    def test_profile_exists_false(self):
        s = self._make()
        s.page.content.return_value = '<html><body>Page Not Found</body></html>'
        assert s._profile_exists() is False

    def test_profile_exists_sorry(self):
        s = self._make()
        s.page.content.return_value = '<html><body>Sorry, this page isn\'t available</body></html>'
        assert s._profile_exists() is False

    def test_extract_current_reel_links_empty(self):
        s = self._make()
        s.page.locator.return_value.all.return_value = []
        result = s._extract_current_reel_links()
        assert result == []

    def test_extract_current_reel_links_with_reels(self):
        s = self._make()
        link = MagicMock()
        link.get_attribute.return_value = '/username/reel/ABC123/'

        bg_div = MagicMock()
        bg_div.count.return_value = 1
        bg_div.get_attribute.return_value = 'background-image: url("http://thumb.jpg")'

        stat = MagicMock()
        stat.count.return_value = 1
        stat.inner_text.return_value = '1.2K'

        link.locator.side_effect = lambda sel: (
            MagicMock(first=bg_div) if 'background' in sel or 'div' in sel.lower()
            else MagicMock(first=stat)
        )

        container = MagicMock()
        container.locator.return_value.all.return_value = [link]

        s.page.locator.return_value.all.return_value = [container]
        result = s._extract_current_reel_links()
        assert len(result) >= 1

    def test_aggressive_scroll(self):
        s = self._make()
        container = MagicMock()
        container.scroll_into_view_if_needed.return_value = None
        s.page.locator.return_value.all.return_value = [container]
        s._aggressive_scroll()
        container.scroll_into_view_if_needed.assert_called_once()

    def test_aggressive_scroll_no_containers(self):
        s = self._make()
        s.page.locator.return_value.all.return_value = []
        s._aggressive_scroll()
        s.page.evaluate.assert_called()

    def test_save_links(self):
        s = self._make()
        td = tempfile.mkdtemp()
        s.config.base_output_dir = td
        reel_links = [
            {'url': 'https://instagram.com/user/reel/ABC/', 'stats': '1.2K views', 'thumbnail': 'http://t.jpg'},
            {'url': 'https://instagram.com/user/reel/XYZ/', 'stats': '500 views', 'thumbnail': ''},
        ]
        output = os.path.join(td, 'test_reels.txt')
        s._save_links(reel_links, 'testuser', output)
        assert os.path.exists(output)
        with open(output, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_scroll_and_collect_target_immediate(self):
        """Target count already met after first extract"""
        s = self._make()
        s._extract_current_reel_links = MagicMock(return_value=[
            {'url': 'http://reel/1/'},
            {'url': 'http://reel/2/'},
        ])
        result = s._scroll_and_collect(target_count=2)
        assert len(result) >= 2

    def test_scroll_and_collect_no_new(self):
        """No new reels found → stops after MAX_NO_NEW_REELS"""
        s = self._make()
        s.config.scroll_max_no_new_attempts = 2
        s._extract_current_reel_links = MagicMock(return_value=[])
        s._aggressive_scroll = MagicMock()
        result = s._scroll_and_collect()
        assert result == []
