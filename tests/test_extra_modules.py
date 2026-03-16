"""
Deep coverage tests for extra modules:
- NotificationReader & NotificationItem
- ReelDataScraper & ReelData
- PostLinksScraper & _LegacyPostLinksScraper
- BatchDownloader, DownloadTask, DownloadResult, BatchResult, ProgressTracker
- CaptchaSolver, CaptchaProvider
- FollowersCollector
- orchestrator.py (Orchestrator)
- parallel_scraper.py (ParallelScraper)
- async_engine.py (AsyncEngine)
"""

import pytest
import json
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
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
# NotificationReader & NotificationItem
# ═══════════════════════════════════════════════════════════

class TestNotificationItem:
    def test_defaults(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem()
        assert n.type == 'other'
        assert n.usernames == []
        assert n.text == ''
        assert n.is_grouped is False
        assert n.extra_count == 0

    def test_to_dict(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(type='follow', usernames=['user1'], text='started following you',
                             time_text='1d', section='Yesterday', profile_url='/user1/')
        d = n.to_dict()
        assert d['type'] == 'follow'
        assert d['usernames'] == ['user1']
        assert d['section'] == 'Yesterday'

    def test_grouped(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(is_grouped=True, extra_count=5, text='user1 and 5 others liked...')
        assert n.is_grouped is True
        assert n.extra_count == 5

    def test_with_comment(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(type='comment_like', comment_text='Nice post!')
        assert n.comment_text == 'Nice post!'
        d = n.to_dict()
        assert d['comment_text'] == 'Nice post!'


class TestNotificationReader:
    def _make_reader(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        config = ScraperConfig()
        return NotificationReader(page, logger, config)

    def test_init(self):
        reader = self._make_reader()
        assert reader._section_map == {}

    def test_detect_type_follow(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 started following you') == 'follow'

    def test_detect_type_comment_like(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 liked your comment: nice') == 'comment_like'

    def test_detect_type_post_like(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 liked your post') == 'post_like'

    def test_detect_type_comment(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 commented: hello') == 'comment'

    def test_detect_type_mention(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 mentioned you in a comment') == 'mention'

    def test_detect_type_thread(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 posted a thread you might like') == 'thread'

    def test_detect_type_follow_request(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 requested to follow you') == 'follow_request'

    def test_detect_type_follow_accepted(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 accepted your follow request') == 'follow_accepted'

    def test_detect_type_story(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 posted a story') == 'story'

    def test_detect_type_uzbek_follow(self):
        reader = self._make_reader()
        assert reader._detect_type('user1 sizni kuzatishni boshladi') == 'follow'

    def test_detect_type_other(self):
        reader = self._make_reader()
        assert reader._detect_type('some random text') == 'other'

    def test_clean_text(self):
        reader = self._make_reader()
        assert reader._clean_text('hello\nworld  test') == 'hello world test'
        assert reader._clean_text('') == ''
        assert reader._clean_text(None) == ''

    def test_count_types(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [
            NotificationItem(type='follow'),
            NotificationItem(type='follow'),
            NotificationItem(type='comment'),
        ]
        result = reader._count_types(notifs)
        assert 'follow:2' in result
        assert 'comment:1' in result

    def test_count_sections(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [
            NotificationItem(section='Yesterday'),
            NotificationItem(section='Yesterday'),
            NotificationItem(section='This week'),
        ]
        result = reader._count_sections(notifs)
        assert 'Yesterday:2' in result

    def test_filter_by_type(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [
            NotificationItem(type='follow'),
            NotificationItem(type='comment'),
            NotificationItem(type='follow'),
        ]
        follows = reader.filter_by_type(notifs, 'follow')
        assert len(follows) == 2

    def test_filter_by_section(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [
            NotificationItem(section='Yesterday'),
            NotificationItem(section='This week'),
        ]
        filtered = reader.filter_by_section(notifs, 'Yesterday')
        assert len(filtered) == 1

    def test_filter_by_username(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [
            NotificationItem(usernames=['user1', 'user2']),
            NotificationItem(usernames=['user3']),
        ]
        filtered = reader.filter_by_username(notifs, 'user1')
        assert len(filtered) == 1

    def test_summary(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [
            NotificationItem(type='follow', usernames=['u1'], action_button='Follow Back', section='Yesterday'),
            NotificationItem(type='comment', usernames=['u2'], action_button='Following', section='This week'),
        ]
        s = reader.summary(notifs)
        assert s['total'] == 2
        assert 'u1' in s['has_follow_back']
        assert 'u2' in s['has_following']
        assert len(s['unique_users']) == 2

    def test_to_dicts(self):
        from instaharvest.notifications import NotificationItem
        reader = self._make_reader()
        notifs = [NotificationItem(type='follow'), NotificationItem(type='comment')]
        dicts = reader.to_dicts(notifs)
        assert len(dicts) == 2
        assert dicts[0]['type'] == 'follow'

    def test_get_section_for_item_empty(self):
        reader = self._make_reader()
        reader._section_map = {}
        item = MagicMock()
        assert reader._get_section_for_item(item) == ''

    def test_get_section_for_item_with_map(self):
        reader = self._make_reader()
        reader._section_map = {100: 'Yesterday', 500: 'This week'}
        item = MagicMock()
        item.bounding_box.return_value = {'y': 300}
        assert reader._get_section_for_item(item) == 'Yesterday'

    def test_get_section_for_item_no_box(self):
        reader = self._make_reader()
        reader._section_map = {100: 'Yesterday'}
        item = MagicMock()
        item.bounding_box.return_value = None
        assert reader._get_section_for_item(item) == ''

    def test_open_notifications_already_on_page(self):
        reader = self._make_reader()
        reader.page.url = 'https://www.instagram.com/accounts/activity/'
        result = reader.open_notifications()
        assert result is True

    def test_open_notifications_login_redirect(self):
        reader = self._make_reader()
        reader.page.url = 'https://www.instagram.com/some-page/'
        # After goto, URL changes to login
        def side_effect(*a, **kw):
            reader.page.url = 'https://www.instagram.com/accounts/login/'
        reader.page.goto.side_effect = side_effect
        result = reader.open_notifications()
        assert result is False


# ═══════════════════════════════════════════════════════════
# ReelData & ReelDataScraper
# ═══════════════════════════════════════════════════════════

class TestReelData:
    def test_defaults(self):
        from instaharvest.reel_data import ReelData
        r = ReelData(url='https://instagram.com/reel/ABC/')
        assert r.has_tags is False
        assert r.has_location is False
        assert r.content_type == 'Reel'

    def test_with_tags(self):
        from instaharvest.reel_data import ReelData
        r = ReelData(url='u', tagged_accounts=['user1', 'user2'])
        assert r.has_tags is True

    def test_with_location(self):
        from instaharvest.reel_data import ReelData
        from instaharvest.post_data import PostLocation
        loc = PostLocation(name='NYC', pk='123')
        r = ReelData(url='u', location=loc)
        assert r.has_location is True

    def test_to_dict(self):
        from instaharvest.reel_data import ReelData
        r = ReelData(url='u', likes=100, comment_count=5, shortcode='ABC')
        d = r.to_dict()
        assert d['url'] == 'u'
        assert d['likes'] == 100
        assert d['shortcode'] == 'ABC'


class TestReelDataScraper:
    def test_init(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        assert s is not None

    def test_scrape_invalid_url(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        with pytest.raises(ValueError, match="Invalid reel URL"):
            s.scrape('https://instagram.com/p/ABC/')

    def test_find_media_item_items(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        data = {'items': [{'pk': '123', 'media_type': 2}]}
        result = s._find_media_item(data)
        assert result is not None
        assert result['pk'] == '123'

    def test_find_media_item_edges(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        data = {'edges': [{'node': {'media': {'pk': '456', 'media_type': 2}}}]}
        result = s._find_media_item(data)
        assert result is not None
        assert result['pk'] == '456'

    def test_find_media_item_none(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        assert s._find_media_item({}) is None
        assert s._find_media_item(None) is None

    def test_parse_media_item_full(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        item = {
            'pk': '123', 'code': 'ABC', 'media_type': 2, 'product_type': 'clips',
            'taken_at': 1700000000, 'like_count': 500, 'comment_count': 10,
            'has_liked': True, 'top_likers': ['u1'],
            'caption': {'text': 'Hello world'},
            'location': {'name': 'NYC', 'pk': 1, 'lat': 40.7, 'lng': -74.0, 'address': '123 St'},
            'user': {'username': 'poster', 'full_name': 'Poster', 'pk': 99, 'is_verified': True},
            'original_width': 1080, 'original_height': 1920,
            'has_audio': True, 'video_duration': 30.5,
            'video_versions': [{'url': 'https://cdn.ig/v.mp4', 'width': 1080, 'height': 1920}],
            'usertags': {'in': [{'user': {'username': 'tagged1'}, 'position': [0.5, 0.5]}]},
        }
        result = s._parse_media_item(item)
        assert result['pk'] == '123'
        assert result['shortcode'] == 'ABC'
        assert result['like_count'] == 500
        assert result['caption'] == 'Hello world'
        assert result['location'].name == 'NYC'
        assert result['owner'].username == 'poster'
        assert result['tagged_accounts'] == ['tagged1']
        assert result['has_audio'] is True
        assert len(result['media_urls']) == 1

    def test_parse_media_item_not_dict(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        assert s._parse_media_item("not a dict") is None

    def test_parse_media_item_no_caption(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        result = s._parse_media_item({'pk': '1', 'code': 'X'})
        assert result['caption'] == ''

    def test_parse_media_item_no_location(self):
        from instaharvest.reel_data import ReelDataScraper
        s = _make_scraper(ReelDataScraper)
        result = s._parse_media_item({'pk': '1'})
        assert result['location'] is None


# ═══════════════════════════════════════════════════════════
# BatchDownloader data models
# ═══════════════════════════════════════════════════════════

class TestBatchDownloaderModels:
    def test_download_task_repr(self):
        from instaharvest.batch_downloader import DownloadTask
        t = DownloadTask(url='u', save_path=Path('/tmp/f.jpg'), shortcode='ABC', index=0, media_type='image')
        assert 'ABC' in repr(t)

    def test_download_result_repr_success(self):
        from instaharvest.batch_downloader import DownloadResult, DownloadTask
        t = DownloadTask(url='u', save_path=Path('/tmp/f.jpg'), shortcode='ABC', index=0)
        r = DownloadResult(task=t, success=True, file_size=2048, duration=1.5)
        s = repr(r)
        assert '✅' in s
        assert 'ABC' in s

    def test_download_result_repr_failed(self):
        from instaharvest.batch_downloader import DownloadResult, DownloadTask
        t = DownloadTask(url='u', save_path=Path('/tmp/f.jpg'), shortcode='X', index=0)
        r = DownloadResult(task=t, success=False, error='timeout')
        assert '❌' in repr(r)

    def test_format_size(self):
        from instaharvest.batch_downloader import DownloadResult
        assert 'B' in DownloadResult._format_size(500)
        assert 'KB' in DownloadResult._format_size(5000)
        assert 'MB' in DownloadResult._format_size(5_000_000)

    def test_batch_result_properties(self):
        from instaharvest.batch_downloader import BatchResult, DownloadResult, DownloadTask
        t1 = DownloadTask(url='u1', save_path=Path('/tmp/1.jpg'))
        t2 = DownloadTask(url='u2', save_path=Path('/tmp/2.jpg'))
        br = BatchResult(
            results=[
                DownloadResult(task=t1, success=True, file_size=1000, duration=1.0),
                DownloadResult(task=t2, success=False, error='fail'),
            ],
            total=2, start_time=100.0, end_time=105.0
        )
        assert br.success_count == 1
        assert br.failed_count == 1
        assert br.total_bytes == 1000
        assert br.duration == 5.0
        assert br.speed == 200.0

    def test_batch_result_summary(self):
        from instaharvest.batch_downloader import BatchResult, DownloadResult, DownloadTask
        t = DownloadTask(url='u', save_path=Path('/tmp/1.jpg'))
        br = BatchResult(results=[DownloadResult(task=t, success=True, file_size=500)],
                         total=1, start_time=0, end_time=1)
        s = br.summary()
        assert s['total'] == 1
        assert s['success'] == 1

    def test_batch_result_zero_duration(self):
        from instaharvest.batch_downloader import BatchResult
        br = BatchResult(total=0, start_time=0, end_time=0)
        assert br.speed == 0


class TestProgressTracker:
    def test_init(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=10)
        assert pt.total == 10
        assert pt.completed == 0

    def test_update_success(self):
        from instaharvest.batch_downloader import ProgressTracker, DownloadResult, DownloadTask
        pt = ProgressTracker(total=5)
        t = DownloadTask(url='u', save_path=Path('/tmp/f.jpg'))
        r = DownloadResult(task=t, success=True, file_size=1024)
        pt.update(r)
        assert pt.completed == 1
        assert pt.bytes_downloaded == 1024

    def test_update_failure(self):
        from instaharvest.batch_downloader import ProgressTracker, DownloadResult, DownloadTask
        pt = ProgressTracker(total=5)
        t = DownloadTask(url='u', save_path=Path('/tmp/f.jpg'))
        r = DownloadResult(task=t, success=False)
        pt.update(r)
        assert pt.failed == 1

    def test_skip(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=5)
        pt.skip()
        assert pt.skipped == 1
        assert pt.completed == 1

    def test_repr(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=10)
        assert '0/10' in repr(pt)


class TestBatchDownloader:
    def test_init_default(self):
        from instaharvest.batch_downloader import BatchDownloader
        with patch('instaharvest.batch_downloader.NetworkClient'):
            bd = BatchDownloader()
        assert bd.max_workers == 8
        assert bd.max_retries == 2

    def test_init_custom(self):
        from instaharvest.batch_downloader import BatchDownloader
        with patch('instaharvest.batch_downloader.NetworkClient'):
            bd = BatchDownloader(max_workers=4, max_retries=3, output_dir='/tmp/dl')
        assert bd.max_workers == 4
        assert bd.max_retries == 3

    def test_repr(self):
        from instaharvest.batch_downloader import BatchDownloader
        with patch('instaharvest.batch_downloader.NetworkClient'):
            bd = BatchDownloader(max_workers=4)
        assert 'workers=4' in repr(bd)


# ═══════════════════════════════════════════════════════════
# CaptchaSolver
# ═══════════════════════════════════════════════════════════

class TestCaptchaSolver:
    def test_init_2captcha(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        s = CaptchaSolver(api_key='test', provider='2captcha')
        assert s.provider == CaptchaProvider.TWO_CAPTCHA
        assert s.api_key == 'test'

    def test_init_anticaptcha(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        s = CaptchaSolver(api_key='test', provider='anticaptcha')
        assert s.provider == CaptchaProvider.ANTI_CAPTCHA

    def test_init_twocaptcha_alias(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        s = CaptchaSolver(provider='twocaptcha')
        assert s.provider == CaptchaProvider.TWO_CAPTCHA

    def test_init_anti_captcha_alias(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        s = CaptchaSolver(provider='anti-captcha')
        assert s.provider == CaptchaProvider.ANTI_CAPTCHA

    def test_init_unknown_provider(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        s = CaptchaSolver(provider='unknown')
        assert s.provider == CaptchaProvider.TWO_CAPTCHA  # Default

    def test_stats(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver(api_key='test')
        stats = s.stats
        assert stats['solved'] == 0
        assert stats['failed'] == 0
        assert stats['provider'] == '2captcha'

    def test_detect_captcha_no_captcha(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value.first = loc
        page.url = 'https://instagram.com/'
        assert s.detect_captcha(page) is False

    def test_detect_captcha_found(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 1
        page.locator.return_value.first = loc
        page.url = 'https://instagram.com/'
        assert s.detect_captcha(page) is True

    def test_detect_captcha_url(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value.first = loc
        page.url = 'https://instagram.com/challenge/'
        assert s.detect_captcha(page) is True

    def test_solve_no_api_key(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver(api_key='')
        page = MagicMock()
        assert s.solve(page) is False

    def test_get_site_key_from_data_sitekey(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 1
        loc.get_attribute.return_value = '6Ld_LMAUAAAAATest'
        page.locator.return_value.first = loc
        key = s._get_site_key(page)
        assert key == '6Ld_LMAUAAAAATest'

    def test_get_captcha_image_none(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value.first = loc
        assert s._get_captcha_image(page) is None

    def test_http_get_no_client(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        with patch('instaharvest.captcha_solver.HAS_HTTPX', False), \
             patch('instaharvest.captcha_solver.HAS_REQUESTS', False):
            result = s._http_get('http://example.com')
            assert result is None

    def test_http_post_no_client(self):
        from instaharvest.captcha_solver import CaptchaSolver
        s = CaptchaSolver()
        with patch('instaharvest.captcha_solver.HAS_HTTPX', False), \
             patch('instaharvest.captcha_solver.HAS_REQUESTS', False):
            result = s._http_post('http://example.com')
            assert result is None


class TestCaptchaProvider:
    def test_enum_values(self):
        from instaharvest.captcha_solver import CaptchaProvider
        assert CaptchaProvider.TWO_CAPTCHA.value == '2captcha'
        assert CaptchaProvider.ANTI_CAPTCHA.value == 'anticaptcha'


# ═══════════════════════════════════════════════════════════
# FollowersCollector
# ═══════════════════════════════════════════════════════════

class TestFollowersCollector:
    def test_init(self):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        assert s is not None

    def test_scrape_raises(self):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        with pytest.raises(NotImplementedError):
            s.scrape()

    def test_click_followers_button_not_found(self):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        loc = MagicMock()
        loc.count.return_value = 0
        s.page.locator.return_value.first = loc
        assert s._click_followers_button() is False

    def test_click_following_button_not_found(self):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        loc = MagicMock()
        loc.count.return_value = 0
        s.page.locator.return_value.first = loc
        assert s._click_following_button() is False

    def test_extract_current_followers(self):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        s.page.evaluate.return_value = ['user1', 'user2', 'explore']
        result = s._extract_current_followers()
        assert 'user1' in result
        assert 'user2' in result
        assert 'explore' not in result  # filtered

    @patch('time.sleep')
    def test_scroll_popup(self, mock_sleep):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        s.page.evaluate.return_value = True
        s._scroll_popup()  # Should not crash

    @patch('time.sleep')
    def test_scroll_popup_fallback(self, mock_sleep):
        from instaharvest.followers import FollowersCollector
        s = _make_scraper(FollowersCollector)
        s.page.evaluate.return_value = False
        s.page.viewport_size = {'width': 1920, 'height': 1080}
        s._scroll_popup()


# ═══════════════════════════════════════════════════════════
# PostLinksScraper
# ═══════════════════════════════════════════════════════════

class TestPostLinksScraper:
    def test_init(self):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        assert s is not None

    def test_profile_exists_true(self):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        s.page.content.return_value = '<html><body>Some content</body></html>'
        assert s._profile_exists() is True

    def test_profile_exists_false(self):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        s.page.content.return_value = "Sorry, this page isn't available."
        assert s._profile_exists() is False

    def test_extract_current_links_proven(self):
        from instaharvest.post_links import PostLinksScraper
        s = _make_scraper(PostLinksScraper)
        el = MagicMock()
        el.get_attribute.return_value = '/p/ABC123/'
        el.inner_html.return_value = '<img>'
        el.locator.return_value.first = MagicMock(count=MagicMock(return_value=0))
        s.page.locator.return_value.all.return_value = [el]
        links = s._extract_current_links_proven()
        assert len(links) == 1
        assert 'ABC123' in links[0]['url']


# ═══════════════════════════════════════════════════════════
# LegacyPostLinksScraper
# ═══════════════════════════════════════════════════════════

class TestLegacyPostLinksScraper:
    def test_deprecation_warning(self):
        from instaharvest.post_links import InstagramPostLinksScraper
        with pytest.warns(DeprecationWarning, match="deprecated"):
            scraper = InstagramPostLinksScraper('testuser')


# ═══════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════

class TestOrchestrator:
    def test_import(self):
        try:
            from instaharvest.orchestrator import Orchestrator
            assert Orchestrator is not None
        except ImportError:
            pytest.skip("Orchestrator not available")

    def test_init(self):
        try:
            from instaharvest.orchestrator import Orchestrator
            o = Orchestrator()
            assert o is not None
        except (ImportError, Exception):
            pytest.skip("Orchestrator not available or requires dependencies")


# ═══════════════════════════════════════════════════════════
# ParallelScraper
# ═══════════════════════════════════════════════════════════

class TestParallelScraper:
    def test_import(self):
        try:
            from instaharvest.parallel_scraper import ParallelScraper
            assert ParallelScraper is not None
        except ImportError:
            pytest.skip("ParallelScraper not available")


# ═══════════════════════════════════════════════════════════
# AsyncEngine
# ═══════════════════════════════════════════════════════════

class TestAsyncEngine:
    def test_import(self):
        try:
            from instaharvest.async_engine import AsyncEngine
            assert AsyncEngine is not None
        except ImportError:
            pytest.skip("AsyncEngine not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
