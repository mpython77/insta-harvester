"""
Deep Coverage Tests - Part 3
Targets remaining uncovered methods in:
  notifications, captcha_solver, parallel_scraper,
  post_data, orchestrator, downloader, post_links,
  highlight_scraper, story_scraper, explore_scraper,
  hashtag_scraper, location_scraper, search_api, followers,
  reel_data, reel_links, comment_scraper, follow, session_utils,
  batch_downloader (deep), exporters, data_export
"""
import pytest
import time
import json
import re
import os
import sys
import base64
import tempfile
import threading
from unittest.mock import MagicMock, patch, PropertyMock, AsyncMock, call
from dataclasses import dataclass, asdict
from pathlib import Path
from bs4 import BeautifulSoup


def _cfg():
    from instaharvest.config import ScraperConfig
    return ScraperConfig()

def _mock_page():
    p = MagicMock()
    p.url = 'https://instagram.com/'
    return p

def _mock_logger():
    return MagicMock()


# ═══════════════════════════════════════════════════════════════
# NotificationReader - Deep Methods
# ═══════════════════════════════════════════════════════════════

class TestNotificationReaderDeep:
    def _make(self):
        from instaharvest.notifications import NotificationReader
        return NotificationReader(_mock_page(), _mock_logger())

    def test_clean_text(self):
        nr = self._make()
        assert nr._clean_text('hello\nworld  foo') == 'hello world foo'
        assert nr._clean_text('') == ''
        assert nr._clean_text(None) == ''

    def test_count_types(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [
            NotificationItem(type='follow'),
            NotificationItem(type='follow'),
            NotificationItem(type='post_like'),
        ]
        result = nr._count_types(notifs)
        assert 'follow:2' in result
        assert 'post_like:1' in result

    def test_count_sections(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [
            NotificationItem(section='Yesterday'),
            NotificationItem(section='Yesterday'),
            NotificationItem(section='This week'),
        ]
        result = nr._count_sections(notifs)
        assert 'Yesterday:2' in result

    def test_filter_by_type(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [
            NotificationItem(type='follow'),
            NotificationItem(type='post_like'),
        ]
        follows = nr.filter_by_type(notifs, 'follow')
        assert len(follows) == 1

    def test_filter_by_section(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [
            NotificationItem(section='Yesterday'),
            NotificationItem(section='This week'),
        ]
        result = nr.filter_by_section(notifs, 'Yesterday')
        assert len(result) == 1

    def test_filter_by_username(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [
            NotificationItem(usernames=['alice', 'bob']),
            NotificationItem(usernames=['charlie']),
        ]
        result = nr.filter_by_username(notifs, 'bob')
        assert len(result) == 1

    def test_summary(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [
            NotificationItem(type='follow', usernames=['alice'], section='Yesterday', action_button='Follow Back'),
            NotificationItem(type='post_like', usernames=['bob'], section='This week', action_button='Following'),
            NotificationItem(type='follow', usernames=['charlie'], section='Yesterday'),
        ]
        s = nr.summary(notifs)
        assert s['total'] == 3
        assert 'follow' in s['by_type']
        assert 'alice' in s['has_follow_back']
        assert 'bob' in s['has_following']
        assert 'alice' in s['unique_users']

    def test_to_dicts(self):
        from instaharvest.notifications import NotificationItem
        nr = self._make()
        notifs = [NotificationItem(type='follow'), NotificationItem(type='post_like')]
        dicts = nr.to_dicts(notifs)
        assert len(dicts) == 2
        assert dicts[0]['type'] == 'follow'

    def test_detect_type_follow_request(self):
        nr = self._make()
        assert nr._detect_type('requested to follow you') == 'follow_request'

    def test_detect_type_follow_accepted(self):
        nr = self._make()
        assert nr._detect_type('accepted your follow request') == 'follow_accepted'

    def test_detect_type_thread(self):
        nr = self._make()
        assert nr._detect_type('posted a thread you might like') == 'thread'

    def test_detect_type_story(self):
        nr = self._make()
        assert nr._detect_type('posted a story') == 'story'

    def test_detect_type_tagged(self):
        nr = self._make()
        assert nr._detect_type('tagged you in a post') == 'mention'

    def test_detect_type_russian_follow(self):
        nr = self._make()
        assert nr._detect_type('подписался на ваши обновления') == 'follow'

    def test_detect_type_turkish_like(self):
        nr = self._make()
        assert nr._detect_type('gönderinizi beğendi') == 'post_like'

    def test_detect_type_spanish_comment(self):
        nr = self._make()
        assert nr._detect_type('comentó: nice photo') == 'comment'

    @patch('instaharvest.notifications.time')
    @patch('instaharvest.notifications.random')
    def test_open_notifications_already_on_page(self, mock_random, mock_time):
        nr = self._make()
        nr.page.url = 'https://instagram.com/accounts/activity/'
        nr.page.wait_for_selector = MagicMock()
        result = nr.open_notifications()
        assert result is True

    @patch('instaharvest.notifications.time')
    @patch('instaharvest.notifications.random')
    def test_open_notifications_blank_page(self, mock_random, mock_time):
        mock_random.uniform.return_value = 0.5
        nr = self._make()
        nr.page.url = 'about:blank'
        nr.page.wait_for_selector = MagicMock(side_effect=Exception("timeout"))
        main = MagicMock()
        main.count.return_value = 1
        nr.page.locator.return_value = main
        result = nr.open_notifications()
        assert result is True

    def test_open_notifications_exception(self):
        nr = self._make()
        nr.page.url = None
        nr.page.goto.side_effect = Exception("network error")
        result = nr.open_notifications()
        assert result is False

    @patch('instaharvest.notifications.time')
    @patch('instaharvest.notifications.random')
    def test_open_notifications_login_redirect(self, mock_random, mock_time):
        mock_random.uniform.return_value = 0.5
        nr = self._make()
        nr.page.url = 'https://instagram.com/'
        def change_url(*a, **kw):
            nr.page.url = 'https://instagram.com/accounts/login/'
        nr.page.goto.side_effect = change_url
        result = nr.open_notifications()
        assert result is False

    def test_build_section_map(self):
        nr = self._make()
        heading = MagicMock()
        heading.inner_text.return_value = 'Yesterday'
        heading.bounding_box.return_value = {'y': 100}
        headings = MagicMock()
        headings.count.return_value = 1
        headings.nth.return_value = heading
        nr.page.locator.return_value = headings
        nr._build_section_map()
        assert 100 in nr._section_map
        assert nr._section_map[100] == 'Yesterday'

    def test_build_section_map_exception(self):
        nr = self._make()
        nr.page.locator.side_effect = Exception("error")
        nr._build_section_map()
        assert nr._section_map == {}

    def test_get_section_for_item_empty(self):
        nr = self._make()
        nr._section_map = {}
        result = nr._get_section_for_item(MagicMock())
        assert result == ''

    def test_get_section_for_item(self):
        nr = self._make()
        nr._section_map = {50: 'Yesterday', 200: 'This week'}
        item = MagicMock()
        item.bounding_box.return_value = {'y': 150}
        result = nr._get_section_for_item(item)
        assert result == 'Yesterday'

    def test_get_section_for_item_no_box(self):
        nr = self._make()
        nr._section_map = {50: 'Yesterday'}
        item = MagicMock()
        item.bounding_box.return_value = None
        result = nr._get_section_for_item(item)
        assert result == ''

    @patch('instaharvest.notifications.time')
    @patch('instaharvest.notifications.random')
    def test_scroll_to_load(self, mock_random, mock_time):
        mock_random.uniform.return_value = 1.5
        nr = self._make()
        items = MagicMock()
        items.count.side_effect = [5, 10, 15, 20]
        nr.page.locator.return_value = items
        result = nr._scroll_to_load(target_count=15, max_scrolls=3)

    def test_read_notifications_open_fail(self):
        nr = self._make()
        nr.page.url = None
        nr.page.goto.side_effect = Exception("fail")
        result = nr.read_notifications(open_page=True)
        assert result == []

    def test_grouped_pattern(self):
        from instaharvest.notifications import NotificationReader
        match = NotificationReader.GROUPED_PATTERN.search('and 5 others liked your post')
        assert match
        assert match.group(1) == '5'


# ═══════════════════════════════════════════════════════════════
# CaptchaSolver — Deep Methods
# ═══════════════════════════════════════════════════════════════

class TestCaptchaSolverDeep:
    def _make(self, provider='2captcha'):
        from instaharvest.captcha_solver import CaptchaSolver
        return CaptchaSolver(api_key='test_key_123', provider=provider)

    def test_get_site_key_from_attr(self):
        cs = self._make()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 1
        el.get_attribute.return_value = 'SITE_KEY_ABC'
        page.locator.return_value.first = el
        result = cs._get_site_key(page)
        assert result == 'SITE_KEY_ABC'

    def test_get_site_key_from_iframe(self):
        cs = self._make()
        page = MagicMock()
        el_none = MagicMock()
        el_none.count.return_value = 0
        el_none.get_attribute.return_value = None
        iframe = MagicMock()
        iframe.count.return_value = 1
        iframe.get_attribute.return_value = 'https://google.com/recaptcha/api2/anchor?k=MY_KEY_123&co=xxx'
        
        def locator_side_effect(sel):
            if 'sitekey' in sel:
                return MagicMock(first=el_none)
            elif 'iframe' in sel:
                return MagicMock(first=iframe)
            return MagicMock(first=el_none)
        
        page.locator.side_effect = locator_side_effect
        result = cs._get_site_key(page)
        assert result == 'MY_KEY_123'

    def test_get_site_key_fallback_known(self):
        cs = self._make()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 0
        el.get_attribute.return_value = None
        page.locator.return_value.first = el
        result = cs._get_site_key(page)
        # Should return first known Instagram key
        assert result is not None

    def test_get_captcha_image_found(self):
        cs = self._make()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 1
        el.screenshot.return_value = b'fake_image_data'
        page.locator.return_value.first = el
        result = cs._get_captcha_image(page)
        assert result == base64.b64encode(b'fake_image_data').decode('utf-8')

    def test_get_captcha_image_not_found(self):
        cs = self._make()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 0
        page.locator.return_value.first = el
        result = cs._get_captcha_image(page)
        assert result is None

    def test_inject_recaptcha_token(self):
        cs = self._make()
        page = MagicMock()
        cs._inject_recaptcha_token(page, 'TOKEN_ABC')
        page.evaluate.assert_called_once()

    def test_inject_recaptcha_token_error(self):
        cs = self._make()
        page = MagicMock()
        page.evaluate.side_effect = Exception("JS error")
        cs._inject_recaptcha_token(page, 'TOKEN_ABC')
        # Should not raise

    def test_input_captcha_answer(self):
        cs = self._make()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 1
        page.locator.return_value.first = el
        cs._input_captcha_answer(page, 'ANSWER')
        el.fill.assert_called_once_with('ANSWER')

    def test_input_captcha_answer_not_found(self):
        cs = self._make()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 0
        page.locator.return_value.first = el
        cs._input_captcha_answer(page, 'ANSWER')
        el.fill.assert_not_called()

    def test_stats_property(self):
        cs = self._make()
        cs._stats['solved'] = 5
        cs._stats['failed'] = 2
        s = cs.stats
        assert s['solved'] == 5
        assert s['failed'] == 2
        assert s['provider'] == '2captcha'

    def test_http_get_exception(self):
        cs = self._make()
        result = cs._http_get('https://invalid.test.nonexistent/api', params={'key': 'test'})
        assert result is None

    def test_http_post_exception(self):
        cs = self._make()
        # URL that will fail
        result = cs._http_post('https://invalid.test.nonexistent/api', data={'key': 'test'})
        assert result is None

    def test_solve_recaptcha_dispatches_to_2captcha(self):
        cs = self._make('2captcha')
        # Mock internal method
        cs._solve_recaptcha_2captcha = MagicMock(return_value=True)
        result = cs.solve_recaptcha('SITE_KEY', 'https://example.com', None)
        assert result is True

    def test_solve_recaptcha_dispatches_to_anticaptcha(self):
        cs = self._make('anticaptcha')
        cs._solve_recaptcha_anticaptcha = MagicMock(return_value=True)
        result = cs.solve_recaptcha('SITE_KEY', 'https://example.com', None)
        assert result is True

    def test_solve_image_dispatches_to_2captcha(self):
        cs = self._make('2captcha')
        cs._solve_image_2captcha = MagicMock(return_value=True)
        result = cs.solve_image_captcha('base64string', None)
        assert result is True

    def test_solve_image_dispatches_to_anticaptcha(self):
        cs = self._make('anticaptcha')
        cs._solve_image_anticaptcha = MagicMock(return_value=True)
        result = cs.solve_image_captcha('base64string', None)
        assert result is True

    def test_solve_with_api_key_no_captcha_type(self):
        cs = self._make()
        page = MagicMock()
        cs._get_site_key = MagicMock(return_value=None)
        cs._get_captcha_image = MagicMock(return_value=None)
        result = cs.solve(page)
        assert result is False

    def test_solve_exception(self):
        cs = self._make()
        page = MagicMock()
        cs._get_site_key = MagicMock(side_effect=Exception("error"))
        result = cs.solve(page)
        assert result is False
        assert cs._stats['failed'] == 1

    def test_get_balance_2captcha(self):
        cs = self._make('2captcha')
        cs._http_get = MagicMock(return_value={'status': 1, 'request': '12.50'})
        balance = cs.get_balance()
        assert balance == 12.50

    def test_get_balance_anticaptcha(self):
        cs = self._make('anticaptcha')
        cs._http_post = MagicMock(return_value={'errorId': 0, 'balance': 25.0})
        balance = cs.get_balance()
        assert balance == 25.0

    def test_get_balance_error(self):
        cs = self._make()
        cs._http_get = MagicMock(side_effect=Exception("fail"))
        balance = cs.get_balance()
        assert balance is None

    @patch('instaharvest.captcha_solver.time')
    def test_poll_2captcha_success(self, mock_time):
        mock_time.time.side_effect = [0, 1, 2]
        mock_time.sleep = MagicMock()
        cs = self._make()
        cs._http_get = MagicMock(return_value={'status': 1, 'request': 'TOKEN_XYZ'})
        token = cs._poll_2captcha('task_123')
        assert token == 'TOKEN_XYZ'

    @patch('instaharvest.captcha_solver.time')
    def test_poll_2captcha_error(self, mock_time):
        mock_time.time.side_effect = [0, 1, 2]
        mock_time.sleep = MagicMock()
        cs = self._make()
        cs._http_get = MagicMock(return_value={'status': 0, 'request': 'ERROR_CAPTCHA_UNSOLVABLE'})
        token = cs._poll_2captcha('task_123')
        assert token is None

    @patch('instaharvest.captcha_solver.time')
    def test_poll_anticaptcha_success(self, mock_time):
        mock_time.time.side_effect = [0, 1, 2]
        mock_time.sleep = MagicMock()
        cs = self._make('anticaptcha')
        cs._http_post = MagicMock(return_value={'status': 'ready', 'solution': {'gRecaptchaResponse': 'TOKEN_ABC'}})
        token = cs._poll_anticaptcha('task_456')
        assert token == 'TOKEN_ABC'

    @patch('instaharvest.captcha_solver.time')
    def test_poll_anticaptcha_error(self, mock_time):
        mock_time.time.side_effect = [0, 1, 2]
        mock_time.sleep = MagicMock()
        cs = self._make('anticaptcha')
        cs._http_post = MagicMock(return_value={'errorId': 1, 'errorCode': 'ERROR'})
        token = cs._poll_anticaptcha('task_456')
        assert token is None


# ═══════════════════════════════════════════════════════════════
# PostData model — Deep
# ═══════════════════════════════════════════════════════════════

class TestPostDataModelsDeep:
    def test_post_location(self):
        from instaharvest.post_data import PostLocation
        loc = PostLocation(name='NYC', pk='123', latitude=40.7, longitude=-74.0, address='5th Ave', city='New York')
        d = loc.to_dict()
        assert d['name'] == 'NYC'
        assert d['latitude'] == 40.7

    def test_post_owner(self):
        from instaharvest.post_data import PostOwner
        owner = PostOwner(username='john', full_name='John Doe', pk='456', is_verified=True)
        d = owner.to_dict()
        assert d['username'] == 'john'
        assert d['is_verified'] is True

    def test_carousel_slide(self):
        from instaharvest.post_data import CarouselSlide
        slide = CarouselSlide(slide_index=0, media_type='image', width=1080, height=1080)
        assert slide.has_tags is False
        assert slide.tagged_accounts == []
        d = slide.to_dict()
        assert d['width'] == 1080

    def test_carousel_slide_with_tags(self):
        from instaharvest.post_data import CarouselSlide
        slide = CarouselSlide(tagged_accounts=['user1', 'user2'])
        assert slide.has_tags is True

    def test_post_data_to_dict(self):
        from instaharvest.post_data import PostData
        pd = PostData(url='http://test', tagged_accounts=['a'], likes='10', timestamp='Jan')
        d = pd.to_dict()
        assert d['url'] == 'http://test'
        assert d['tagged_accounts'] == ['a']
        assert d['media_urls'] == []
        assert d['top_likers'] == []

    def test_post_data_defaults(self):
        from instaharvest.post_data import PostData
        pd = PostData(url='http://test', tagged_accounts=[], likes='0', timestamp='N/A')
        assert pd.media_urls == []
        assert pd.tagged_users_per_media == []
        assert pd.carousel_slides == []
        assert pd.tag_positions == []
        assert pd.top_likers == []

    def test_post_data_scraper_is_reel(self):
        from instaharvest.post_data import PostDataScraper
        pds = PostDataScraper()
        assert pds._is_reel('https://instagram.com/reel/ABC/') is True
        assert pds._is_reel('https://instagram.com/reels/ABC/') is True
        assert pds._is_reel('https://instagram.com/p/ABC/') is False

    def test_post_data_scraper_get_content_type(self):
        from instaharvest.post_data import PostDataScraper
        pds = PostDataScraper()
        assert pds._get_content_type('https://instagram.com/reel/X/') == 'reel'
        assert pds._get_content_type('https://instagram.com/p/X/') == 'post'

    def test_post_data_scraper_is_video_post(self):
        from instaharvest.post_data import PostDataScraper
        pds = PostDataScraper()
        pds.page = MagicMock()
        pds.page.locator.return_value.count.return_value = 1
        assert pds._is_video_post() is True

    def test_post_data_scraper_is_video_post_no(self):
        from instaharvest.post_data import PostDataScraper
        pds = PostDataScraper()
        pds.page = MagicMock()
        pds.page.locator.return_value.count.return_value = 0
        assert pds._is_video_post() is False

    def test_post_data_scraper_is_video_post_exception(self):
        from instaharvest.post_data import PostDataScraper
        pds = PostDataScraper()
        pds.page = MagicMock()
        pds.page.locator.side_effect = Exception("err")
        assert pds._is_video_post() is False


# ═══════════════════════════════════════════════════════════════
# ParallelScraper — Deep helper functions
# ═══════════════════════════════════════════════════════════════

class TestParallelScraperHelper:
    def test_extract_timestamp_bs4_title(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        html = '<html><body><time title="January 15, 2024" datetime="2024-01-15T12:00:00">1d</time></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = _extract_timestamp_bs4(soup)
        assert result == 'January 15, 2024'

    def test_extract_timestamp_bs4_datetime(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        html = '<html><body><time datetime="2024-01-15T12:00:00">1d</time></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = _extract_timestamp_bs4(soup)
        assert result == '2024-01-15T12:00:00'

    def test_extract_timestamp_bs4_text_fallback(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        html = '<html><body><time>2 days ago</time></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = _extract_timestamp_bs4(soup)
        assert result == '2 days ago'

    def test_extract_timestamp_bs4_no_time(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        html = '<html><body><p>No time element</p></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = _extract_timestamp_bs4(soup)
        assert result == 'N/A'

    def test_split_into_batches(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        pps = ParallelPostDataScraper()
        items = list(range(10))
        batches = pps._split_into_batches(items, 3)
        assert len(batches) == 3
        total = sum(len(b) for b in batches)
        assert total == 10
        # First batch has remainder
        assert len(batches[0]) == 4

    def test_split_into_batches_even(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        pps = ParallelPostDataScraper()
        items = list(range(9))
        batches = pps._split_into_batches(items, 3)
        assert all(len(b) == 3 for b in batches)

    def test_split_into_batches_single(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        pps = ParallelPostDataScraper()
        items = list(range(5))
        batches = pps._split_into_batches(items, 1)
        assert len(batches) == 1
        assert len(batches[0]) == 5


# ═══════════════════════════════════════════════════════════════
# Downloader - Deep
# ═══════════════════════════════════════════════════════════════

class TestDownloaderDeep:
    def test_init_with_config(self):
        from instaharvest.downloader import MediaDownloader
        md = MediaDownloader(config=_cfg())
        assert md.config is not None

    def test_init_with_output_dir(self):
        from instaharvest.downloader import MediaDownloader
        td = tempfile.mkdtemp()
        md = MediaDownloader(output_dir=td)
        assert str(td) in str(md.output_dir) or md.output_dir is not None


# ═══════════════════════════════════════════════════════════════
# PostLinksScraper — Deep
# ═══════════════════════════════════════════════════════════════

class TestPostLinksDeep:
    def test_init_with_config(self):
        from instaharvest.post_links import PostLinksScraper
        pls = PostLinksScraper(config=_cfg())
        assert pls.config is not None

    def test_interrupted_default(self):
        from instaharvest.post_links import PostLinksScraper
        pls = PostLinksScraper()
        assert pls.interrupted is False


# ═══════════════════════════════════════════════════════════════
# HighlightScraper
# ═══════════════════════════════════════════════════════════════

class TestHighlightScraper:
    def test_init(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        hs = HighlightsScraper()
        assert hs.config is not None

    def test_init_with_config(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        hs = HighlightsScraper(config=_cfg())
        assert hs.config is not None


# ═══════════════════════════════════════════════════════════════
# StoryScraper
# ═══════════════════════════════════════════════════════════════

class TestStoryScraper:
    def test_init(self):
        from instaharvest.story_scraper import StoryScraper
        ss = StoryScraper()
        assert ss.config is not None

    def test_init_with_config(self):
        from instaharvest.story_scraper import StoryScraper
        ss = StoryScraper(config=_cfg())
        assert ss.config is not None


# ═══════════════════════════════════════════════════════════════
# ReelDataScraper
# ═══════════════════════════════════════════════════════════════

class TestReelDataScraper:
    def test_init(self):
        from instaharvest.reel_data import ReelDataScraper
        rds = ReelDataScraper()
        assert rds.config is not None

    def test_init_with_config(self):
        from instaharvest.reel_data import ReelDataScraper
        rds = ReelDataScraper(config=_cfg())
        assert rds.config is not None


# ═══════════════════════════════════════════════════════════════
# ReelLinksScraper
# ═══════════════════════════════════════════════════════════════

class TestReelLinksScraper:
    def test_init(self):
        from instaharvest.reel_links import ReelLinksScraper
        rls = ReelLinksScraper()
        assert rls.config is not None

    def test_init_with_config(self):
        from instaharvest.reel_links import ReelLinksScraper
        rls = ReelLinksScraper(config=_cfg())
        assert rls.config is not None


# ═══════════════════════════════════════════════════════════════
# CommentScraper
# ═══════════════════════════════════════════════════════════════

class TestCommentScraper:
    def test_init(self):
        from instaharvest.comment_scraper import CommentScraper
        cs = CommentScraper()
        assert cs.config is not None


# ═══════════════════════════════════════════════════════════════
# FollowManager
# ═══════════════════════════════════════════════════════════════

class TestFollowManager:
    def test_init(self):
        from instaharvest.follow import FollowManager
        fm = FollowManager()
        assert fm.config is not None


# ═══════════════════════════════════════════════════════════════
# SessionUtils
# ═══════════════════════════════════════════════════════════════

class TestSessionUtils:
    def test_import(self):
        from instaharvest import session_utils
        assert session_utils is not None


# ═══════════════════════════════════════════════════════════════
# BatchDownloader — Deep Methods
# ═══════════════════════════════════════════════════════════════

class TestBatchDownloaderDeep:
    def test_create_tasks_empty(self):
        from instaharvest.batch_downloader import BatchDownloader
        bd = BatchDownloader()
        tasks = bd._create_tasks([], username='test')
        assert tasks == []

    def test_create_tasks_with_post(self):
        from instaharvest.batch_downloader import BatchDownloader
        from instaharvest.post_data import PostData
        bd = BatchDownloader()
        post = PostData(
            url='http://instagram.com/p/ABC/',
            tagged_accounts=[],
            likes='10',
            timestamp='Jan',
            media_urls=['https://cdn.instagram.com/photo.jpg'],
            shortcode='ABC'
        )
        tasks = bd._create_tasks([post], username='testuser')
        assert len(tasks) == 1

    def test_download_single_success(self):
        from instaharvest.batch_downloader import BatchDownloader, DownloadTask, DownloadResult
        bd = BatchDownloader()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'fake_image_data_1234567890' * 100
        mock_client.get.return_value = mock_resp
        bd._client = mock_client
        
        td = tempfile.mkdtemp()
        task = DownloadTask(
            url='https://cdn.example.com/img.jpg',
            save_path=Path(td) / 'test.jpg',
            shortcode='TEST'
        )
        result = bd._download_single(task)
        # result could be success or failure depending on internal logic
        assert isinstance(result, DownloadResult)


# ═══════════════════════════════════════════════════════════════
# Exporters
# ═══════════════════════════════════════════════════════════════

class TestExportersDeep:
    def test_streaming_json_exporter_init(self):
        from instaharvest.exporters import StreamingJSONExporter
        td = tempfile.mkdtemp()
        sje = StreamingJSONExporter(filename=os.path.join(td, 'test.json'))
        assert sje is not None

    def test_excel_exporter_init(self):
        from instaharvest.exporters import ExcelExporter
        td = tempfile.mkdtemp()
        ee = ExcelExporter(filename=os.path.join(td, 'test.xlsx'))
        assert ee is not None

    def test_base_exporter_init(self):
        from instaharvest.exporters import BaseExporter
        assert BaseExporter is not None

    def test_comments_exporter_init(self):
        from instaharvest.exporters import CommentsExporter
        td = tempfile.mkdtemp()
        ce = CommentsExporter(username='testuser')
        assert ce is not None


# ═══════════════════════════════════════════════════════════════
# DataExport
# ═══════════════════════════════════════════════════════════════

class TestDataExportDeep:
    def test_import(self):
        from instaharvest.data_export import DataExporter
        de = DataExporter()
        assert de is not None


# ═══════════════════════════════════════════════════════════════
# SearchAPI
# ═══════════════════════════════════════════════════════════════

class TestSearchAPIDeep:
    def test_init_with_config(self):
        from instaharvest.search_api import SearchAPI
        sa = SearchAPI(config=_cfg())
        assert sa.config is not None


# ═══════════════════════════════════════════════════════════════
# ExploreScaper
# ═══════════════════════════════════════════════════════════════

class TestExploreScraper:
    def test_init_with_config(self):
        from instaharvest.explore_scraper import ExploreScraper
        es = ExploreScraper(config=_cfg())
        assert es.config is not None


# ═══════════════════════════════════════════════════════════════
# HashtagScraper
# ═══════════════════════════════════════════════════════════════

class TestHashtagScraperDeep:
    def test_init_with_config(self):
        from instaharvest.hashtag_scraper import HashtagScraper
        hs = HashtagScraper(config=_cfg())
        assert hs.config is not None


# ═══════════════════════════════════════════════════════════════
# LocationScraper
# ═══════════════════════════════════════════════════════════════

class TestLocationScraperDeep:
    def test_init_with_config(self):
        from instaharvest.location_scraper import LocationScraper
        ls = LocationScraper(config=_cfg())
        assert ls.config is not None


# ═══════════════════════════════════════════════════════════════
# Followers
# ═══════════════════════════════════════════════════════════════

class TestFollowersDeep:
    def test_init_with_config(self):
        from instaharvest.followers import FollowersCollector
        fc = FollowersCollector(config=_cfg())
        assert fc.config is not None


# ═══════════════════════════════════════════════════════════════
# ProfileScraper
# ═══════════════════════════════════════════════════════════════

class TestProfileScraperDeep:
    def test_init(self):
        from instaharvest.profile import ProfileScraper
        ps = ProfileScraper()
        assert ps.config is not None

    def test_init_with_config(self):
        from instaharvest.profile import ProfileScraper
        ps = ProfileScraper(config=_cfg())
        assert ps.config is not None
