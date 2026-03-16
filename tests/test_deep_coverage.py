"""
Deep Coverage Tests - Part 1: post_data.py methods
Targets _find_media_item, _parse_media_item, _parse_json_for_urls,
_extract_with_recovery, scrape_multiple, get_tagged_accounts,
get_likes_count, get_timestamp, get_reel_likes_count,
get_reel_timestamp, get_reel_tagged_accounts, _count_visible_videos,
_extract_from_page_json, _extract_from_dom, _extract_from_full_page,
_extract_tagged_users, _extract_carousel_media, _extract_all_from_json
"""
import pytest
import time
import json
import asyncio
from unittest.mock import MagicMock, patch, PropertyMock, AsyncMock, call
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _cfg():
    from instaharvest.config import ScraperConfig
    return ScraperConfig()

def _make(cls, **extra):
    """Create scraper with all browser mocks injected"""
    cfg = _cfg()
    s = cls.__new__(cls)
    s.config = cfg
    from instaharvest.logging_config import get_logger
    s.logger = get_logger(cls.__name__)
    s.page = MagicMock()
    s.browser = MagicMock()
    s.context = MagicMock()
    s.playwright = MagicMock()
    s.performance_monitor = MagicMock()
    s.error_handler = MagicMock()
    s.captured_media_urls = []
    s.tags_per_media = []
    s.detected_video_count = 0
    s.main_scope = MagicMock()
    for k, v in extra.items():
        setattr(s, k, v)
    return s


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _find_media_item
# ═══════════════════════════════════════════════════════════════

class TestFindMediaItem:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_find_items_array(self):
        s = self._make_scraper()
        data = {'require': [{'xdt': {'items': [{'pk': '123', 'media_type': 1}]}}]}
        result = s._find_media_item(data)
        assert result['pk'] == '123'

    def test_find_edges_node_media(self):
        s = self._make_scraper()
        data = {'edges': [{'node': {'media': {'pk': '456', 'media_type': 2}}}]}
        result = s._find_media_item(data)
        assert result['pk'] == '456'

    def test_find_edges_node_direct(self):
        s = self._make_scraper()
        data = {'edges': [{'node': {'pk': '789', 'media_type': 1}}]}
        result = s._find_media_item(data)
        assert result['pk'] == '789'

    def test_max_depth_exceeded(self):
        s = self._make_scraper()
        assert s._find_media_item({'a': {'b': {'pk': '1'}}}, depth=100) is None

    def test_none_input(self):
        s = self._make_scraper()
        assert s._find_media_item(None) is None

    def test_list_input(self):
        s = self._make_scraper()
        data = [{'items': [{'pk': '111', 'media_type': 1}]}]
        result = s._find_media_item(data)
        assert result['pk'] == '111'

    def test_no_match(self):
        s = self._make_scraper()
        assert s._find_media_item({'hello': 'world'}) is None


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _parse_media_item
# ═══════════════════════════════════════════════════════════════

class TestParseMediaItem:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_basic_parse(self):
        s = self._make_scraper()
        item = {
            'pk': '123456',
            'code': 'ABC123',
            'media_type': 1,
            'product_type': 'feed',
            'taken_at': 1700000000,
            'like_count': 5000,
            'comment_count': 100,
            'caption': {'text': 'Hello world'},
        }
        result = s._parse_media_item(item)
        assert result['pk'] == '123456'
        assert result['shortcode'] == 'ABC123'
        assert result['likes'] == '5000'
        assert result['comment_count'] == 100
        assert result['caption'] == 'Hello world'
        assert 'timestamp' in result

    def test_location(self):
        s = self._make_scraper()
        item = {
            'pk': '1',
            'location': {'name': 'NYC', 'pk': 99, 'lat': 40.7, 'lng': -74.0, 'address': '5th Ave', 'city': 'NYC'}
        }
        result = s._parse_media_item(item)
        assert result['location'].name == 'NYC'
        assert result['location'].latitude == 40.7

    def test_owner(self):
        s = self._make_scraper()
        item = {
            'pk': '1',
            'user': {'username': 'testuser', 'full_name': 'Test', 'pk': 42, 'is_verified': True}
        }
        result = s._parse_media_item(item)
        assert result['owner'].username == 'testuser'
        assert result['owner'].is_verified is True

    def test_carousel(self):
        s = self._make_scraper()
        item = {
            'pk': '1',
            'carousel_media_count': 3,
            'carousel_media': [
                {
                    'media_type': 1,
                    'original_width': 1080,
                    'original_height': 1080,
                    'image_versions2': {'candidates': [{'url': 'https://img.jpg'}]},
                    'usertags': {'in': [{'user': {'username': 'brand1'}, 'position': [0.5, 0.5]}]}
                },
                {
                    'media_type': 2,
                    'video_versions': [{'url': 'https://vid.mp4'}],
                    'video_duration': 15.5,
                    'has_audio': True
                }
            ]
        }
        result = s._parse_media_item(item)
        assert len(result['carousel_slides']) == 2
        assert result['carousel_slides'][0].media_type == 'image'
        assert result['carousel_slides'][1].media_type == 'video'
        assert 'brand1' in result['tagged_accounts']

    def test_usertags(self):
        s = self._make_scraper()
        item = {
            'pk': '1',
            'usertags': {
                'in': [
                    {'user': {'username': 'tag1'}, 'position': [0.1, 0.2]},
                    {'user': {'username': 'tag2'}, 'position': [0.3, 0.4]}
                ]
            }
        }
        result = s._parse_media_item(item)
        assert result['tagged_accounts'] == ['tag1', 'tag2']
        assert len(result['tag_positions']) == 2

    def test_video_fields(self):
        s = self._make_scraper()
        item = {'pk': '1', 'media_type': 2, 'video_duration': 30.5, 'has_audio': True}
        result = s._parse_media_item(item)
        assert result['is_video'] is True
        assert result['video_duration'] == 30.5

    def test_caption_string(self):
        s = self._make_scraper()
        item = {'pk': '1', 'caption': 'Direct string caption'}
        result = s._parse_media_item(item)
        assert result['caption'] == 'Direct string caption'

    def test_caption_none(self):
        s = self._make_scraper()
        item = {'pk': '1', 'caption': None}
        result = s._parse_media_item(item)
        assert result['caption'] == ''

    def test_non_dict_returns_none(self):
        s = self._make_scraper()
        assert s._parse_media_item("not a dict") is None

    def test_image_versions(self):
        s = self._make_scraper()
        item = {
            'pk': '1',
            'image_versions2': {'candidates': [{'url': 'https://img.jpg'}]},
            'video_versions': [{'url': 'https://vid.mp4'}]
        }
        result = s._parse_media_item(item)
        assert 'https://img.jpg' in result['media_urls']
        assert 'https://vid.mp4' in result['media_urls']


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _parse_json_for_urls
# ═══════════════════════════════════════════════════════════════

class TestParseJsonForUrls:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_cdn_urls(self):
        s = self._make_scraper()
        content = '"url":"https://scontent-iad3.cdninstagram.com/v/photo.jpg"'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1
        assert any('cdninstagram' in u for u in urls)

    def test_display_url_pattern(self):
        s = self._make_scraper()
        content = '"display_url": "https://scontent.fbcdn.net/v/image.jpg"'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1

    def test_video_url_pattern(self):
        s = self._make_scraper()
        content = '"video_url": "https://scontent.fbcdn.net/v/clip.mp4"'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1

    def test_escaped_unicode(self):
        s = self._make_scraper()
        content = '"url":"https://scontent.cdninstagram.com/v/photo.jpg?param=1\\u0026other=2"'
        urls = s._parse_json_for_urls(content)
        assert any('&' in u for u in urls)

    def test_dedup(self):
        s = self._make_scraper()
        content = (
            '"display_url":"https://scontent.cdninstagram.com/v/photo.jpg"'
            '"display_url":"https://scontent.cdninstagram.com/v/photo.jpg"'
        )
        urls = s._parse_json_for_urls(content)
        assert len(urls) == 1

    def test_no_match(self):
        s = self._make_scraper()
        urls = s._parse_json_for_urls('nothing here')
        assert urls == []


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _extract_with_recovery
# ═══════════════════════════════════════════════════════════════

class TestExtractWithRecovery:
    def test_calls_error_handler(self):
        from instaharvest.post_data import PostDataScraper
        s = _make(PostDataScraper)
        s.error_handler.safe_extract = MagicMock(return_value='result')
        result = s._extract_with_recovery(lambda: 'val', 'test', 'default')
        s.error_handler.safe_extract.assert_called_once()
        assert result == 'result'


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _count_visible_videos
# ═══════════════════════════════════════════════════════════════

class TestCountVisibleVideos:
    def test_count_videos(self):
        from instaharvest.post_data import PostDataScraper
        s = _make(PostDataScraper)
        v1 = MagicMock()
        v1.bounding_box.return_value = {'width': 300, 'height': 300, 'y': 100, 'x': 0}
        v2 = MagicMock()
        v2.bounding_box.return_value = {'width': 50, 'height': 50, 'y': 100, 'x': 0}
        s.page.locator.return_value.all.return_value = [v1, v2]
        assert s._count_visible_videos() == 1

    def test_no_videos(self):
        from instaharvest.post_data import PostDataScraper
        s = _make(PostDataScraper)
        s.page.locator.return_value.all.return_value = []
        assert s._count_visible_videos() == 0

    def test_exception_handling(self):
        from instaharvest.post_data import PostDataScraper
        s = _make(PostDataScraper)
        s.page.locator.side_effect = Exception("error")
        assert s._count_visible_videos() == 0


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — get_likes_count, get_timestamp
# ═══════════════════════════════════════════════════════════════

class TestGetLikesCount:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        s = _make(PostDataScraper)
        # Add safe_extract used by get_timestamp
        s.safe_extract = MagicMock(side_effect=lambda fn, **kw: fn())
        return s

    def test_method1_numeric(self):
        s = self._make_scraper()
        span = MagicMock()
        span.inner_text.return_value = '1,234'
        section = MagicMock()
        section.locator.return_value.all.return_value = [span]
        s.page.locator.return_value.first = section
        result = s.get_likes_count()
        assert result == '1234'

    def test_method1_k_notation(self):
        s = self._make_scraper()
        span = MagicMock()
        span.inner_text.return_value = '5.2K'
        section = MagicMock()
        section.locator.return_value.all.return_value = [span]
        s.page.locator.return_value.first = section
        result = s.get_likes_count()
        assert result == '5.2K'

    def test_all_methods_fail(self):
        s = self._make_scraper()
        s.page.locator.side_effect = Exception("fail")
        result = s.get_likes_count()
        assert result == 'N/A'


class TestGetTimestamp:
    def test_title_attr(self):
        from instaharvest.post_data import PostDataScraper
        s = _make(PostDataScraper)
        time_elem = MagicMock()
        time_elem.get_attribute.side_effect = lambda attr: 'Nov 17, 2025' if attr == 'title' else None
        s.page.locator.return_value.first = time_elem
        s.safe_extract = MagicMock(side_effect=lambda fn, **kw: fn())
        result = s.get_timestamp()
        assert result == 'Nov 17, 2025'


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — Reel methods
# ═══════════════════════════════════════════════════════════════

class TestReelMethods:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_get_reel_likes_config_selector(self):
        s = self._make_scraper()
        likes_elem = MagicMock()
        likes_elem.count.return_value = 1
        likes_elem.inner_text.return_value = '10,500'
        s.page.locator.return_value.first = likes_elem
        result = s.get_reel_likes_count()
        assert result == '10500'

    def test_get_reel_likes_fail(self):
        s = self._make_scraper()
        s.page.locator.side_effect = Exception("no")
        assert s.get_reel_likes_count() == 'N/A'

    def test_get_reel_timestamp_title(self):
        s = self._make_scraper()
        time_el = MagicMock()
        time_el.count.return_value = 1
        time_el.get_attribute.side_effect = lambda attr, **kw: 'Dec 1, 2025' if attr == 'title' else None
        s.page.locator.return_value.first = time_el
        result = s.get_reel_timestamp()
        assert result == 'Dec 1, 2025'

    def test_get_reel_timestamp_no_element(self):
        s = self._make_scraper()
        s.page.locator.side_effect = Exception("no")
        assert s.get_reel_timestamp() == 'N/A'


# ═══════════════════════════════════════════════════════════════
# Parallel Scraper — Module-level functions
# ═══════════════════════════════════════════════════════════════

class TestParallelScraperFunctions:
    def test_parse_number_basic(self):
        from instaharvest.parallel_scraper import _parse_number
        cfg = _cfg()
        assert _parse_number('1,234', cfg) == 1234

    def test_parse_number_k(self):
        from instaharvest.parallel_scraper import _parse_number
        cfg = _cfg()
        result = _parse_number('5.2K', cfg)
        assert result == 5200

    def test_parse_number_m(self):
        from instaharvest.parallel_scraper import _parse_number
        cfg = _cfg()
        result = _parse_number('1.5M', cfg)
        assert result == 1500000

    def test_parse_number_empty(self):
        from instaharvest.parallel_scraper import _parse_number
        cfg = _cfg()
        assert _parse_number('', cfg) is None
        assert _parse_number(None, cfg) is None

    def test_parse_number_invalid(self):
        from instaharvest.parallel_scraper import _parse_number
        cfg = _cfg()
        assert _parse_number('abc', cfg) is None

    def test_get_worker_logger(self):
        from instaharvest.parallel_scraper import _get_worker_logger
        logger = _get_worker_logger(1)
        assert logger.name == 'Worker-1'

    def test_worker_signal_handler(self):
        from instaharvest.parallel_scraper import _worker_signal_handler
        import instaharvest.parallel_scraper as ps
        old = ps._shutdown_event
        mock_event = MagicMock()
        ps._shutdown_event = mock_event
        _worker_signal_handler(2, None)
        mock_event.set.assert_called_once()
        ps._shutdown_event = old

    def test_extract_reel_timestamp(self):
        from instaharvest.parallel_scraper import _extract_reel_timestamp
        cfg = _cfg()
        page = MagicMock()
        time_el = MagicMock()
        time_el.get_attribute.side_effect = lambda attr, **kw: 'Jan 1, 2026' if attr == 'title' else None
        page.locator.return_value.first = time_el
        result = _extract_reel_timestamp(None, page, 0, cfg)
        assert result == 'Jan 1, 2026'

    def test_extract_reel_timestamp_fail(self):
        from instaharvest.parallel_scraper import _extract_reel_timestamp
        cfg = _cfg()
        page = MagicMock()
        page.locator.side_effect = Exception("no")
        assert _extract_reel_timestamp(None, page, 0, cfg) == 'N/A'

    def test_extract_likes_bs4_playwright_fallback(self):
        from instaharvest.parallel_scraper import _extract_likes_bs4
        from bs4 import BeautifulSoup
        cfg = _cfg()
        soup = BeautifulSoup('<html><body></body></html>', 'lxml')
        page = MagicMock()
        span = MagicMock()
        span.inner_text.return_value = '999'
        section = MagicMock()
        section.locator.return_value.all.return_value = [span]
        page.locator.return_value.first = section
        result = _extract_likes_bs4(soup, page, 0, cfg)
        assert result == 999

    def test_extract_reel_likes(self):
        from instaharvest.parallel_scraper import _extract_reel_likes
        cfg = _cfg()
        page = MagicMock()
        span = MagicMock()
        span.inner_text.return_value = '5,200'
        page.locator.return_value.first = span
        result = _extract_reel_likes(None, page, 0, cfg)
        assert result == 5200

    def test_extract_reel_likes_fail(self):
        from instaharvest.parallel_scraper import _extract_reel_likes
        cfg = _cfg()
        page = MagicMock()
        page.locator.side_effect = Exception("err")
        assert _extract_reel_likes(None, page, 0, cfg) == 0


# ═══════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorInit:
    def test_init_default(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert o.shutdown_requested is False
        assert o.excel_exporter is None
        assert o.shared_browser is None

    def test_init_with_shared_browser(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        sb = MagicMock()
        o = InstagramOrchestrator(shared_browser=sb)
        assert o.shared_browser is sb

    def test_cleanup(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        o._cleanup()  # should not raise


class TestOrchestratorMethods:
    def _make_orch(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator.__new__(InstagramOrchestrator)
        o.config = _cfg()
        from instaharvest.logging_config import get_logger
        o.logger = get_logger("TestOrch")
        o.shutdown_requested = False
        o.excel_exporter = None
        o.current_results = None
        o.current_username = None
        o.shared_browser = None
        return o

    @patch('instaharvest.orchestrator.ProfileScraper')
    def test_scrape_profile_stats(self, MockPS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        MockPS.return_value = mock_scraper
        mock_data = MagicMock()
        mock_scraper.scrape.return_value = mock_data
        result = o._scrape_profile_stats('testuser')
        assert result == mock_data

    @patch('instaharvest.orchestrator.PostLinksScraper')
    def test_collect_post_links(self, MockPLS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.interrupted = False
        mock_scraper.scrape.return_value = [{'url': 'http://a', 'type': 'Post'}]
        MockPLS.return_value = mock_scraper
        result = o._collect_post_links('user')
        assert len(result) == 1

    @patch('instaharvest.orchestrator.PostLinksScraper')
    def test_collect_post_links_interrupted(self, MockPLS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.interrupted = True
        mock_scraper.scrape.return_value = []
        MockPLS.return_value = mock_scraper
        o._collect_post_links('user')
        assert o.shutdown_requested is True

    @patch('instaharvest.orchestrator.ReelLinksScraper')
    def test_collect_reel_links(self, MockRLS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.interrupted = False
        mock_scraper.scrape.return_value = ['http://reel1']
        MockRLS.return_value = mock_scraper
        result = o._collect_reel_links('user')
        assert result == ['http://reel1']

    @patch('instaharvest.orchestrator.PostDataScraper')
    def test_scrape_posts_data(self, MockPDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.scrape_multiple.return_value = [MagicMock()]
        MockPDS.return_value = mock_scraper
        result = o._scrape_posts_data([{'url': 'http://p1'}])
        assert len(result) == 1

    def test_scrape_posts_data_shared(self):
        o = self._make_orch()
        sb = MagicMock()
        sb.post_data_scraper.scrape_multiple.return_value = [MagicMock()]
        o.shared_browser = sb
        result = o._scrape_posts_data([{'url': 'http://p1'}])
        assert len(result) == 1

    @patch('instaharvest.orchestrator.ReelDataScraper')
    def test_scrape_reels_data(self, MockRDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.scrape_multiple.return_value = [MagicMock()]
        MockRDS.return_value = mock_scraper
        result = o._scrape_reels_data(['http://reel1'])
        assert len(result) == 1

    def test_scrape_reels_data_shared(self):
        o = self._make_orch()
        sb = MagicMock()
        sb.reel_data_scraper.scrape_multiple.return_value = [MagicMock()]
        o.shared_browser = sb
        result = o._scrape_reels_data(['http://reel1'])
        assert len(result) == 1

    @patch('instaharvest.orchestrator.ParallelPostDataScraper')
    def test_scrape_posts_parallel(self, MockPPS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.scrape_multiple.return_value = [MagicMock()]
        MockPPS.return_value = mock_scraper
        result = o._scrape_posts_parallel([{'url': 'http://p1'}], 3)
        assert len(result) == 1

    @patch('instaharvest.orchestrator.ParallelPostDataScraper')
    def test_scrape_reels_parallel(self, MockPPS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_data = MagicMock()
        mock_data.url = 'http://r1'
        mock_data.tagged_accounts = []
        mock_data.likes = '100'
        mock_data.timestamp = 'Jan'
        mock_scraper.scrape_multiple.return_value = [mock_data]
        MockPPS.return_value = mock_scraper
        result = o._scrape_reels_parallel(['http://r1'], 3)
        assert len(result) == 1
        assert result[0].content_type == 'Reel'


# ═══════════════════════════════════════════════════════════════
# Async Engine
# ═══════════════════════════════════════════════════════════════

class TestAsyncBaseScraper:
    def test_init(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        assert s.page is None
        assert s.browser is None

    @pytest.mark.asyncio
    async def test_close_all_none(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        await s.close()
        assert s.page is None

    @pytest.mark.asyncio
    async def test_close_with_context(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        s.context = AsyncMock()
        s.browser = AsyncMock()
        s.playwright = AsyncMock()
        await s.close()
        assert s.context is None
        assert s.browser is None

    @pytest.mark.asyncio
    async def test_is_rate_limited_url(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        s.page = AsyncMock()
        s.page.url = 'https://instagram.com/challenge/'
        assert await s._is_rate_limited() is True

    @pytest.mark.asyncio
    async def test_is_rate_limited_false(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        s.page = AsyncMock()
        s.page.url = 'https://instagram.com/p/ABC123/'
        body_mock = AsyncMock()
        body_mock.inner_text = AsyncMock(return_value='normal page content')
        s.page.locator = MagicMock(return_value=body_mock)
        assert await s._is_rate_limited() is False

    @pytest.mark.asyncio
    async def test_is_login_page_true(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        s.page = AsyncMock()
        s.page.url = 'https://instagram.com/accounts/login/'
        assert await s._is_login_page() is True

    @pytest.mark.asyncio
    async def test_is_login_page_false(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        s.page = AsyncMock()
        s.page.url = 'https://instagram.com/user/'
        s.page.content = AsyncMock(return_value='<html>Hello</html>')
        assert await s._is_login_page() is False

    @pytest.mark.asyncio
    async def test_update_session_no_context(self):
        from instaharvest.async_engine import AsyncBaseScraper
        s = AsyncBaseScraper()
        s.context = None
        await s.update_session()  # should not raise


class TestAsyncProfileScraper:
    def test_parse_number(self):
        from instaharvest.async_engine import AsyncProfileScraper
        s = AsyncProfileScraper()
        assert s._parse_number('1,234') == 1234
        assert s._parse_number('5.2K') == 5200
        assert s._parse_number('1.5M') == 1500000
        assert s._parse_number('') == 0
        assert s._parse_number(None) == 0
        assert s._parse_number('abc') == 0


class TestAsyncBatchScraper:
    def test_init(self):
        from instaharvest.async_engine import AsyncBatchScraper
        s = AsyncBatchScraper(max_concurrent=3)
        assert s.max_concurrent == 3

    def test_repr(self):
        from instaharvest.async_engine import AsyncBatchScraper
        s = AsyncBatchScraper(max_concurrent=5)
        assert 'concurrent=5' in repr(s)

    def test_errors_property(self):
        from instaharvest.async_engine import AsyncBatchScraper
        s = AsyncBatchScraper()
        s._errors = {'user1': 'not_found'}
        assert s.errors == {'user1': 'not_found'}


# ═══════════════════════════════════════════════════════════════
# SharedBrowser
# ═══════════════════════════════════════════════════════════════

class TestSharedBrowserInit:
    def test_init(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser()
        assert sb.page is None
        assert sb.browser is None

    def test_init_custom_session(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser(session_file='custom.json')
        assert sb.session_file == 'custom.json'


class TestSharedBrowserProperties:
    def _make_sb(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser.__new__(SharedBrowser)
        sb.config = _cfg()
        from instaharvest.logging_config import get_logger
        sb.logger = get_logger('TestSB')
        sb.playwright = MagicMock()
        sb.browser = MagicMock()
        sb.context = MagicMock()
        sb.page = MagicMock()
        sb.session_file = 'test.json'
        # All private managers None
        for attr in [
            '_follow_manager', '_message_manager', '_followers_collector',
            '_profile_scraper', '_post_links_scraper', '_reel_links_scraper',
            '_downloader', '_post_data_scraper', '_reel_data_scraper',
            '_story_scraper', '_comment_scraper', '_search_api',
            '_hashtag_scraper', '_location_scraper', '_explore_scraper',
            '_notification_reader', '_web_api'
        ]:
            setattr(sb, attr, None)
        return sb

    def test_follow_manager_lazy(self):
        sb = self._make_sb()
        assert sb._follow_manager is None
        fm = sb.follow_manager
        assert fm is not None
        assert fm.page == sb.page
        # Should cache
        assert sb.follow_manager is fm

    def test_message_manager_lazy(self):
        sb = self._make_sb()
        mm = sb.message_manager
        assert mm is not None
        assert mm.browser == sb.browser

    def test_profile_scraper_lazy(self):
        sb = self._make_sb()
        ps = sb.profile_scraper
        assert ps is not None
        assert ps.context == sb.context

    def test_post_data_scraper_lazy(self):
        sb = self._make_sb()
        pds = sb.post_data_scraper
        assert pds is not None
        assert pds.page == sb.page

    def test_reel_data_scraper_lazy(self):
        sb = self._make_sb()
        rds = sb.reel_data_scraper
        assert rds is not None

    def test_story_scraper_lazy(self):
        sb = self._make_sb()
        ss = sb.story_scraper
        assert ss is not None

    def test_comment_scraper_lazy(self):
        sb = self._make_sb()
        cs = sb.comment_scraper
        assert cs is not None

    def test_search_api_lazy(self):
        sb = self._make_sb()
        sa = sb.search_api
        assert sa is not None

    def test_hashtag_scraper_lazy(self):
        sb = self._make_sb()
        hs = sb.hashtag_scraper
        assert hs is not None

    def test_location_scraper_lazy(self):
        sb = self._make_sb()
        ls = sb.location_scraper
        assert ls is not None

    def test_explore_scraper_lazy(self):
        sb = self._make_sb()
        es = sb.explore_scraper
        assert es is not None

    def test_notification_reader_lazy(self):
        sb = self._make_sb()
        with patch('instaharvest.shared_browser.NotificationReader') as MockNR:
            MockNR.return_value = MagicMock()
            sb._notification_reader = None
            nr = sb.notification_reader
            assert nr is not None

    def test_downloader_lazy(self):
        sb = self._make_sb()
        dl = sb.downloader
        assert dl is not None

    def test_post_links_scraper_lazy(self):
        sb = self._make_sb()
        pls = sb.post_links_scraper
        assert pls is not None

    def test_reel_links_scraper_lazy(self):
        sb = self._make_sb()
        rls = sb.reel_links_scraper
        assert rls is not None

    def test_followers_collector_lazy(self):
        sb = self._make_sb()
        fc = sb.followers_collector
        assert fc is not None

    def test_inject_browser(self):
        sb = self._make_sb()
        mock_scraper = MagicMock()
        result = sb._inject_browser(mock_scraper)
        assert result.page == sb.page
        assert result.browser == sb.browser
        assert result.context == sb.context
        assert result.playwright == sb.playwright


class TestSharedBrowserClose:
    def test_close(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser.__new__(SharedBrowser)
        sb.config = _cfg()
        from instaharvest.logging_config import get_logger
        sb.logger = get_logger('TestSB')
        sb.context = MagicMock()
        sb.page = MagicMock()
        sb.browser = MagicMock()
        sb.playwright = MagicMock()
        sb.session_file = 'test.json'
        # Managers
        sb._follow_manager = MagicMock()
        sb._message_manager = MagicMock()
        sb._followers_collector = MagicMock()
        sb._profile_scraper = MagicMock()
        sb._post_links_scraper = MagicMock()
        sb._reel_links_scraper = MagicMock()
        sb._downloader = MagicMock()
        sb._post_data_scraper = MagicMock()
        sb._reel_data_scraper = MagicMock()
        sb._story_scraper = MagicMock()
        sb._comment_scraper = MagicMock()
        sb._search_api = MagicMock()
        sb._hashtag_scraper = MagicMock()
        sb._location_scraper = MagicMock()
        sb._explore_scraper = MagicMock()
        sb._notification_reader = MagicMock()
        sb._web_api = None
        # Mock _update_session
        sb._update_session = MagicMock()
        sb.close()
        assert sb._follow_manager is None
        assert sb._message_manager is None


class TestSharedBrowserConvenience:
    def _make_sb(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser.__new__(SharedBrowser)
        sb.config = _cfg()
        from instaharvest.logging_config import get_logger
        sb.logger = get_logger('TestSB')
        sb.playwright = MagicMock()
        sb.browser = MagicMock()
        sb.context = MagicMock()
        sb.page = MagicMock()
        sb.session_file = 'test.json'
        for attr in [
            '_follow_manager', '_message_manager', '_followers_collector',
            '_profile_scraper', '_post_links_scraper', '_reel_links_scraper',
            '_downloader', '_post_data_scraper', '_reel_data_scraper',
            '_story_scraper', '_comment_scraper', '_search_api',
            '_hashtag_scraper', '_location_scraper', '_explore_scraper',
            '_notification_reader', '_web_api'
        ]:
            setattr(sb, attr, None)
        return sb

    def test_get_profile_json(self):
        sb = self._make_sb()
        sb._web_api = MagicMock()
        sb._web_api.get_profile.return_value = 'profile_data'
        assert sb.get_profile_json('user') == 'profile_data'

    def test_search_users(self):
        sb = self._make_sb()
        sb._web_api = MagicMock()
        sb._web_api.search.return_value = 'results'
        assert sb.search_users('query') == 'results'

    def test_follow(self):
        sb = self._make_sb()
        sb._follow_manager = MagicMock()
        sb._follow_manager.follow.return_value = {'status': 'ok'}
        assert sb.follow('user') == {'status': 'ok'}

    def test_unfollow(self):
        sb = self._make_sb()
        sb._follow_manager = MagicMock()
        sb._follow_manager.unfollow.return_value = {'status': 'ok'}
        assert sb.unfollow('user') == {'status': 'ok'}

    def test_send_message(self):
        sb = self._make_sb()
        sb._message_manager = MagicMock()
        sb._message_manager.send_message.return_value = {'status': 'sent'}
        assert sb.send_message('user', 'hi') == {'status': 'sent'}

    def test_scrape_profile(self):
        sb = self._make_sb()
        from instaharvest.profile import ProfileData
        mock_data = ProfileData(username='test', posts=10, followers=100, following=50)
        sb._profile_scraper = MagicMock()
        sb._profile_scraper.scrape.return_value = mock_data
        result = sb.scrape_profile('test')
        assert result['username'] == 'test'


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _extract_all_from_json
# ═══════════════════════════════════════════════════════════════

class TestExtractAllFromJson:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_extract_from_json_success(self):
        s = self._make_scraper()
        item = {
            'pk': '999',
            'media_type': 1,
            'like_count': 500,
            'comment_count': 10,
            'caption': {'text': 'test'}
        }
        # _find_media_item expects items[] at some nesting level
        json_content = json.dumps({'data': {'items': [item]}})
        # Pad to exceed 500 char minimum
        json_content = json_content + ' ' * 500
        script = MagicMock()
        script.inner_text.return_value = json_content
        s.page.locator.return_value.all.return_value = [script]
        result = s._extract_all_from_json()
        assert result is not None
        assert result['pk'] == '999'

    def test_extract_from_json_short_content(self):
        s = self._make_scraper()
        script = MagicMock()
        script.inner_text.return_value = '{}'
        s.page.locator.return_value.all.return_value = [script]
        result = s._extract_all_from_json()
        assert result is None

    def test_extract_from_json_exception(self):
        s = self._make_scraper()
        s.page.locator.side_effect = Exception("error")
        result = s._extract_all_from_json()
        assert result is None


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _extract_tags_from_json
# ═══════════════════════════════════════════════════════════════

class TestExtractTagsFromJson:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_tags_found(self):
        s = self._make_scraper()
        result = {'tagged_accounts': ['user1', 'user2'], 'tagged_users_per_media': [['user1']]}
        with patch.object(s, '_extract_all_from_json', return_value=result):
            tags, per_slide = s._extract_tags_from_json()
            assert tags == ['user1', 'user2']

    def test_no_tags(self):
        s = self._make_scraper()
        with patch.object(s, '_extract_all_from_json', return_value=None):
            tags, per_slide = s._extract_tags_from_json()
            assert tags == []


# ═══════════════════════════════════════════════════════════════
# PostDataScraper — _extract_from_page_json
# ═══════════════════════════════════════════════════════════════

class TestExtractFromPageJson:
    def _make_scraper(self):
        from instaharvest.post_data import PostDataScraper
        return _make(PostDataScraper)

    def test_script_type_json(self):
        s = self._make_scraper()
        script = MagicMock()
        script.inner_text.return_value = '"display_url":"https://scontent.cdninstagram.com/v/photo.jpg"'
        s.page.locator.side_effect = [
            MagicMock(all=MagicMock(return_value=[script])),
            MagicMock(all=MagicMock(return_value=[]))
        ]
        urls = s._extract_from_page_json()
        assert len(urls) >= 1

    def test_exception_handling(self):
        s = self._make_scraper()
        s.page.locator.side_effect = Exception("error")
        urls = s._extract_from_page_json()
        assert urls == []


# ═══════════════════════════════════════════════════════════════
# SharedBrowser — _update_session
# ═══════════════════════════════════════════════════════════════

class TestSharedBrowserUpdateSession:
    def test_update_session_falco_cleanup(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser.__new__(SharedBrowser)
        sb.config = _cfg()
        from instaharvest.logging_config import get_logger
        sb.logger = get_logger('TestSB')
        sb.session_file = '/tmp/test_session_update.json'
        sb.context = MagicMock()
        sb.context.storage_state.return_value = {
            'cookies': [{'name': 'c1'}],
            'origins': [{
                'localStorage': [
                    {'name': 'falco_queue_log_123', 'value': 'data'},
                    {'name': 'important_key', 'value': 'val'}
                ]
            }]
        }
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            sb.session_file = f.name
        try:
            sb._update_session()
            with open(sb.session_file, 'r') as f:
                saved = json.load(f)
            # falco_queue_log should be removed
            ls = saved['origins'][0]['localStorage']
            assert not any(e['name'].startswith('falco_queue_log') for e in ls)
            assert any(e['name'] == 'important_key' for e in ls)
        finally:
            os.unlink(sb.session_file)

    def test_update_session_exception(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser.__new__(SharedBrowser)
        sb.config = _cfg()
        from instaharvest.logging_config import get_logger
        sb.logger = get_logger('TestSB')
        sb.context = MagicMock()
        sb.context.storage_state.side_effect = Exception("fail")
        sb.session_file = 'test.json'
        sb._update_session()  # should not raise


# ═══════════════════════════════════════════════════════════════
# ParallelPostDataScraper class
# ═══════════════════════════════════════════════════════════════

class TestParallelPostDataScraperClass:
    def test_init(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        s = ParallelPostDataScraper()
        assert s.config is not None

    def test_scrape_multiple_exists(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        s = ParallelPostDataScraper()
        assert hasattr(s, 'scrape_multiple')
