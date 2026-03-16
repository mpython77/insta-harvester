"""
Deep coverage tests for the highest-impact, lowest-coverage modules:
- PostData / PostOwner / PostLocation / CarouselSlide / PostDataScraper
- InstagramOrchestrator  
- ParallelPostDataScraper + module-level functions
- ExcelExporter / CommentsExporter / RealTimeCommentsExporter / StreamingJSONExporter / StreamingExcelExporter
- Event / EventEmitter / EventTypes / FollowerWatcher
- SelectorTest / DiagnosticReport / HTMLDiagnostics / run_diagnostic_mode
- MousePoint / StealthManager / apply_stealth_to_context
- SessionStats / SessionRotationStrategy / SessionManager
"""

import pytest
import json
import time
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, mock_open, call
from dataclasses import asdict
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


# ══════════════════════════════════════════════════════════════
# PostData Model Tests
# ══════════════════════════════════════════════════════════════

class TestPostLocation:
    def test_defaults(self):
        from instaharvest.post_data import PostLocation
        loc = PostLocation()
        assert loc.name == ''
        assert loc.pk == ''
        assert loc.latitude == 0.0

    def test_to_dict(self):
        from instaharvest.post_data import PostLocation
        loc = PostLocation(name='NYC', pk='1', latitude=40.7, longitude=-74.0, address='123 St', city='NY')
        d = loc.to_dict()
        assert d['name'] == 'NYC'
        assert d['city'] == 'NY'

class TestPostOwner:
    def test_defaults(self):
        from instaharvest.post_data import PostOwner
        o = PostOwner()
        assert o.username == ''
        assert o.is_verified is False

    def test_to_dict(self):
        from instaharvest.post_data import PostOwner
        o = PostOwner(username='test', full_name='Test User', pk='99', is_verified=True)
        d = o.to_dict()
        assert d['username'] == 'test'
        assert d['is_verified'] is True

class TestCarouselSlide:
    def test_defaults(self):
        from instaharvest.post_data import CarouselSlide
        s = CarouselSlide()
        assert s.tagged_accounts == []
        assert s.tag_positions == []
        assert s.has_tags is False

    def test_has_tags(self):
        from instaharvest.post_data import CarouselSlide
        s = CarouselSlide(tagged_accounts=['u1'])
        assert s.has_tags is True

    def test_to_dict(self):
        from instaharvest.post_data import CarouselSlide
        s = CarouselSlide(slide_index=0, media_type='video', width=1080, height=1920)
        d = s.to_dict()
        assert d['media_type'] == 'video'

class TestPostData:
    def test_defaults(self):
        from instaharvest.post_data import PostData
        p = PostData(url='u', tagged_accounts=[], likes='0', timestamp='N/A')
        assert p.media_urls == []
        assert p.tagged_users_per_media == []
        assert p.top_likers == []
        assert p.carousel_slides == []
        assert p.tag_positions == []

    def test_to_dict(self):
        from instaharvest.post_data import PostData
        p = PostData(url='u', tagged_accounts=['a'], likes='100', timestamp='2024-01-01', content_type='Post')
        d = p.to_dict()
        assert d['url'] == 'u'
        assert d['content_type'] == 'Post'

    def test_with_location(self):
        from instaharvest.post_data import PostData, PostLocation
        loc = PostLocation(name='NYC')
        p = PostData(url='u', tagged_accounts=[], likes='0', timestamp='N/A', location=loc)
        assert p.location.name == 'NYC'

    def test_with_owner(self):
        from instaharvest.post_data import PostData, PostOwner
        o = PostOwner(username='user1')
        p = PostData(url='u', tagged_accounts=[], likes='0', timestamp='N/A', owner=o)
        assert p.owner.username == 'user1'

    def test_json_extracted(self):
        from instaharvest.post_data import PostData
        p = PostData(url='u', tagged_accounts=[], likes='0', timestamp='N/A', json_extracted=True)
        assert p.json_extracted is True


# ══════════════════════════════════════════════════════════════
# PostDataScraper Tests
# ══════════════════════════════════════════════════════════════

class TestPostDataScraper:
    def test_init(self):
        from instaharvest.post_data import PostDataScraper
        s = _make_scraper(PostDataScraper)
        assert s.captured_media_urls == []

    def test_is_reel(self):
        from instaharvest.post_data import PostDataScraper
        s = _make_scraper(PostDataScraper)
        assert s._is_reel('https://www.instagram.com/reel/ABC/') is True
        assert s._is_reel('https://www.instagram.com/reels/ABC/') is True
        assert s._is_reel('https://www.instagram.com/p/ABC/') is False

    def test_get_content_type(self):
        from instaharvest.post_data import PostDataScraper
        s = _make_scraper(PostDataScraper)
        assert s._get_content_type('https://www.instagram.com/reel/ABC/') == 'reel'
        assert s._get_content_type('https://www.instagram.com/p/ABC/') == 'post'

    def test_is_video_post(self):
        from instaharvest.post_data import PostDataScraper
        s = _make_scraper(PostDataScraper)
        s.page.locator.return_value.count.return_value = 1
        assert s._is_video_post() is True

    def test_is_video_post_false(self):
        from instaharvest.post_data import PostDataScraper
        s = _make_scraper(PostDataScraper)
        s.page.locator.return_value.count.return_value = 0
        assert s._is_video_post() is False

    def test_setup_network_interception(self):
        from instaharvest.post_data import PostDataScraper
        s = _make_scraper(PostDataScraper)
        s._setup_network_interception()
        # Verify page.on was called with 'response' event
        s.page.on.assert_called_once()
        call_args = s.page.on.call_args
        assert call_args[0][0] == 'response'
        assert s.captured_media_urls == []


# ══════════════════════════════════════════════════════════════
# Diagnostics Tests
# ══════════════════════════════════════════════════════════════

class TestSelectorTest:
    def test_defaults(self):
        from instaharvest.diagnostics import SelectorTest
        t = SelectorTest(selector='div.test', selector_type='css', found=True, count=3)
        assert t.selector == 'div.test'
        assert t.found is True
        assert t.count == 3

class TestDiagnosticReport:
    def test_add_test(self):
        from instaharvest.diagnostics import DiagnosticReport, SelectorTest
        r = DiagnosticReport(timestamp='now', url='url', content_type='Post')
        r.add_test(SelectorTest(selector='a', selector_type='css', found=True, count=1))
        r.add_test(SelectorTest(selector='b', selector_type='css', found=False, count=0))
        assert len(r.test_results) == 2

    def test_get_failed_selectors(self):
        from instaharvest.diagnostics import DiagnosticReport, SelectorTest
        r = DiagnosticReport(timestamp='now', url='url', content_type='Post')
        r.add_test(SelectorTest(selector='a', selector_type='css', found=True))
        r.add_test(SelectorTest(selector='b', selector_type='css', found=False))
        failed = r.get_failed_selectors()
        assert failed == ['b']

    def test_get_success_rate_empty(self):
        from instaharvest.diagnostics import DiagnosticReport
        r = DiagnosticReport(timestamp='now', url='url', content_type='Post')
        assert r.get_success_rate() == 0.0

    def test_get_success_rate(self):
        from instaharvest.diagnostics import DiagnosticReport, SelectorTest
        r = DiagnosticReport(timestamp='now', url='url', content_type='Post')
        for i in range(8):
            r.add_test(SelectorTest(selector=f's{i}', selector_type='css', found=True))
        r.add_test(SelectorTest(selector='fail1', selector_type='css', found=False))
        r.add_test(SelectorTest(selector='fail2', selector_type='css', found=False))
        assert r.get_success_rate() == 80.0

class TestHTMLDiagnostics:
    def test_init(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        d = HTMLDiagnostics(page)
        assert d.page is page

    def test_test_selector_css(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.return_value = 5
        d = HTMLDiagnostics(page)
        t = d.test_selector('div.test', 'css')
        assert t.found is True
        assert t.count == 5

    def test_test_selector_xpath(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.return_value = 2
        d = HTMLDiagnostics(page)
        t = d.test_selector('//div', 'xpath')
        assert t.found is True

    def test_test_selector_error(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.side_effect = Exception("timeout")
        d = HTMLDiagnostics(page)
        t = d.test_selector('div.test')
        assert t.found is False
        assert 'timeout' in t.error

    def test_diagnose_post(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.return_value = 1
        d = HTMLDiagnostics(page)
        report = d.diagnose_post('https://instagram.com/p/ABC/')
        assert report.content_type == 'Post'
        assert report.overall_status in ('OK', 'PARTIAL', 'FAILED')

    def test_diagnose_reel(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        d = HTMLDiagnostics(page)
        report = d.diagnose_reel('https://instagram.com/reel/ABC/')
        assert report.content_type == 'Reel'

    def test_quick_validate_true(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.return_value = 3
        d = HTMLDiagnostics(page)
        assert d.quick_validate('div.test', 'test element') is True

    def test_quick_validate_false(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        d = HTMLDiagnostics(page)
        assert d.quick_validate('div.test', 'test element') is False

    def test_quick_validate_error(self):
        from instaharvest.diagnostics import HTMLDiagnostics
        page = MagicMock()
        page.locator.side_effect = Exception("crash")
        d = HTMLDiagnostics(page)
        assert d.quick_validate('div.test', 'test element') is False

    def test_generate_report_text(self):
        from instaharvest.diagnostics import HTMLDiagnostics, DiagnosticReport, SelectorTest
        page = MagicMock()
        d = HTMLDiagnostics(page)
        report = DiagnosticReport(timestamp='2024-01-01', url='url', content_type='Post', overall_status='OK')
        report.add_test(SelectorTest(selector='s1', selector_type='css', found=True, count=1, test_time=0.01))
        report.add_test(SelectorTest(selector='s2', selector_type='css', found=False, count=0, test_time=0.02, error='not found'))
        text = d.generate_report_text(report)
        assert 'DIAGNOSTIC REPORT' in text
        assert '✓' in text
        assert '✗' in text

    def test_run_diagnostic_mode_post(self):
        from instaharvest.diagnostics import run_diagnostic_mode
        page = MagicMock()
        page.locator.return_value.count.return_value = 1
        logger = MagicMock()
        report = run_diagnostic_mode(page, 'https://instagram.com/p/ABC/', logger)
        assert report.content_type == 'Post'

    def test_run_diagnostic_mode_reel(self):
        from instaharvest.diagnostics import run_diagnostic_mode
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        logger = MagicMock()
        report = run_diagnostic_mode(page, 'https://instagram.com/reel/ABC/', logger)
        assert report.content_type == 'Reel'


# ══════════════════════════════════════════════════════════════
# Webhooks / Event System Tests
# ══════════════════════════════════════════════════════════════

class TestEvent:
    def test_defaults(self):
        from instaharvest.webhooks import Event
        e = Event(type='test')
        assert e.type == 'test'
        assert e.data == {}
        assert e.source == 'instaharvest'

    def test_to_dict(self):
        from instaharvest.webhooks import Event
        e = Event(type='test', data={'key': 'value'})
        d = e.to_dict()
        assert d['type'] == 'test'
        assert d['data']['key'] == 'value'
        assert 'timestamp' in d

    def test_repr(self):
        from instaharvest.webhooks import Event
        e = Event(type='test', data={'k': 'v'})
        assert 'test' in repr(e)

class TestEventTypes:
    def test_constants(self):
        from instaharvest.webhooks import EventTypes
        assert EventTypes.NEW_FOLLOWER == 'new_follower'
        assert EventTypes.UNFOLLOW == 'unfollow'
        assert EventTypes.SCRAPE_START == 'scrape_start'
        assert EventTypes.DOWNLOAD_ERROR == 'download_error'
        assert EventTypes.RATE_LIMITED == 'rate_limited'

class TestEventEmitter:
    def test_init(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter(max_history=500)
        assert e._max_history == 500

    def test_on_direct(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        def handler(event): pass
        e.on('test', handler)
        assert 'test' in e._listeners
        assert handler in e._listeners['test']

    def test_on_decorator(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        @e.on('test')
        def handler(event): pass
        assert handler.__name__ == 'handler'
        assert len(e._listeners['test']) == 1

    def test_off(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        def handler(event): pass
        e.on('test', handler)
        assert e.off('test', handler) is True
        assert len(e._listeners.get('test', [])) == 0

    def test_off_not_found(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        def handler(event): pass
        assert e.off('test', handler) is False

    def test_emit(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        received = []
        e.on('test', lambda ev: received.append(ev))
        event = e.emit('test', {'key': 'val'})
        assert len(received) == 1
        assert received[0].data['key'] == 'val'
        assert event.type == 'test'

    def test_emit_wildcard(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        received = []
        e.on('*', lambda ev: received.append(ev))
        e.emit('anything', {'data': 1})
        assert len(received) == 1

    def test_emit_error_isolation(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        def bad_handler(ev): raise ValueError("boom")
        good_received = []
        e.on('test', bad_handler)
        e.on('test', lambda ev: good_received.append(ev))
        e.emit('test')  # Should not crash
        assert len(good_received) == 1

    def test_once(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        received = []
        @e.once('test')
        def handler(event): received.append(event)
        e.emit('test', {'n': 1})
        e.emit('test', {'n': 2})
        assert len(received) == 1

    def test_history(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter(max_history=5)
        for i in range(10):
            e.emit('test', {'n': i})
        assert len(e.history) == 5
        assert e.history[-1].data['n'] == 9

    def test_listener_count(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        e.on('a', lambda ev: None)
        e.on('a', lambda ev: None)
        e.on('b', lambda ev: None)
        counts = e.listener_count
        assert counts['a'] == 2
        assert counts['b'] == 1

    def test_clear(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        e.on('test', lambda ev: None)
        e.emit('test')
        e.clear()
        assert len(e._listeners) == 0
        assert len(e._history) == 0

    def test_repr(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        e.on('test', lambda ev: None)
        assert 'listeners=1' in repr(e)

    @pytest.mark.asyncio
    async def test_emit_async(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        received = []
        e.on('test', lambda ev: received.append(ev))
        await e.emit_async('test', {'key': 'val'})
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_emit_async_coroutine(self):
        from instaharvest.webhooks import EventEmitter
        e = EventEmitter()
        received = []
        async def handler(ev): received.append(ev)
        e.on('test', handler)
        await e.emit_async('test')
        assert len(received) == 1


class TestFollowerWatcher:
    def test_init(self):
        from instaharvest.webhooks import FollowerWatcher
        with patch.object(Path, 'exists', return_value=False):
            w = FollowerWatcher(interval=600)
        assert w.interval == 600
        assert w.is_running is False
        assert w.tracked_count == 0

    def test_repr(self):
        from instaharvest.webhooks import FollowerWatcher
        with patch.object(Path, 'exists', return_value=False):
            w = FollowerWatcher()
        assert 'stopped' in repr(w)

    def test_load_snapshot(self):
        from instaharvest.webhooks import FollowerWatcher
        data = json.dumps({'followers': ['user1', 'user2'], 'timestamp': '2024-01-01'})
        with patch.object(Path, 'exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=data)):
            w = FollowerWatcher()
        assert w.tracked_count == 2

    def test_save_snapshot(self):
        from instaharvest.webhooks import FollowerWatcher
        with patch.object(Path, 'exists', return_value=False):
            w = FollowerWatcher()
        m = mock_open()
        with patch('builtins.open', m):
            w._save_snapshot({'user1', 'user2'})
        m.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self):
        from instaharvest.webhooks import FollowerWatcher
        with patch.object(Path, 'exists', return_value=False):
            w = FollowerWatcher()
        w._running = True
        await w.stop()
        assert w.is_running is False


# ══════════════════════════════════════════════════════════════
# Stealth Tests
# ══════════════════════════════════════════════════════════════

class TestMousePoint:
    def test_creation(self):
        from instaharvest.stealth import MousePoint
        p = MousePoint(100.5, 200.3)
        assert p.x == 100.5
        assert p.y == 200.3

class TestStealthManager:
    def _make(self):
        from instaharvest.stealth import StealthManager
        config = ScraperConfig()
        with patch.object(StealthManager, '_check_playwright_stealth'):
            s = StealthManager(config)
        s._playwright_stealth_available = False
        return s

    def test_init(self):
        s = self._make()
        assert s is not None

    def test_random_delay(self):
        s = self._make()
        d = s.random_delay(1.0)
        assert 0.5 < d < 2.0

    @patch('time.sleep')
    def test_sleep_human(self, mock_sleep):
        s = self._make()
        s.sleep_human(1.0)
        mock_sleep.assert_called_once()

    def test_bezier_point(self):
        from instaharvest.stealth import MousePoint
        s = self._make()
        points = [MousePoint(0, 0), MousePoint(100, 100)]
        p = s._bezier_point(0.5, points)
        assert abs(p.x - 50) < 1
        assert abs(p.y - 50) < 1

    def test_generate_bezier_path(self):
        from instaharvest.stealth import MousePoint
        s = self._make()
        path = s._generate_bezier_path(MousePoint(0, 0), MousePoint(100, 100), num_points=10)
        assert len(path) == 11  # num_points + 1
        assert path[0].x == pytest.approx(0, abs=1)
        assert path[-1].x == pytest.approx(100, abs=1)

    @patch('time.sleep')
    def test_move_mouse_human(self, mock_sleep):
        s = self._make()
        page = MagicMock()
        page.viewport_size = {'width': 1920, 'height': 1080}
        s.config.human_like_mouse = True
        s.move_mouse_human(page, 500, 300, duration=0.001)
        assert page.mouse.move.called

    def test_move_mouse_fast(self):
        s = self._make()
        page = MagicMock()
        s.config.human_like_mouse = False
        s.move_mouse_human(page, 500, 300)
        page.mouse.move.assert_called_once_with(500, 300)

    @patch('time.sleep')
    def test_click_human(self, mock_sleep):
        s = self._make()
        page = MagicMock()
        page.viewport_size = {'width': 1920, 'height': 1080}
        s.config.human_like_mouse = True
        s.click_human(page, 500, 300)
        assert page.mouse.click.called

    @patch('time.sleep')
    def test_type_human_fast(self, mock_sleep):
        s = self._make()
        page = MagicMock()
        s.config.human_like_typing = False
        s.type_human(page, '#input', 'hello')
        page.type.assert_called_once_with('#input', 'hello')

    @patch('time.sleep')
    def test_type_human_slow(self, mock_sleep):
        s = self._make()
        page = MagicMock()
        s.config.human_like_typing = True
        s.type_human(page, '#input', 'hi')
        assert page.keyboard.type.called

    @patch('time.sleep')
    def test_scroll_human(self, mock_sleep):
        s = self._make()
        page = MagicMock()
        s.config.human_like_scrolling = True
        s.scroll_human(page, 'down', 300)
        assert page.mouse.wheel.called

    def test_scroll_fast(self):
        s = self._make()
        page = MagicMock()
        s.config.human_like_scrolling = False
        s.scroll_human(page, 'up', 200)
        page.mouse.wheel.assert_called_once_with(0, -200)

    def test_get_randomized_viewport(self):
        s = self._make()
        s.config.randomize_viewport = True
        w, h = s.get_randomized_viewport()
        assert 1200 < w < 2000
        assert 700 < h < 1200

    def test_get_fixed_viewport(self):
        s = self._make()
        s.config.randomize_viewport = False
        w, h = s.get_randomized_viewport()
        assert w == s.config.viewport_width
        assert h == s.config.viewport_height

    def test_apply_context_stealth(self):
        s = self._make()
        context = MagicMock()
        s.config.stealth_level = 'aggressive'
        s.config.mask_webgl = True
        s.config.mask_canvas = True
        s.apply_context_stealth(context)
        assert context.add_init_script.call_count >= 1

    def test_apply_page_stealth_no_library(self):
        s = self._make()
        s._playwright_stealth_available = False
        page = MagicMock()
        s.apply_page_stealth(page)  # Should not crash

    def test_apply_stealth_to_context_utility(self):
        from instaharvest.stealth import apply_stealth_to_context, StealthManager
        config = ScraperConfig()
        context = MagicMock()
        logger = MagicMock()
        with patch.object(StealthManager, '_check_playwright_stealth'):
            manager = apply_stealth_to_context(context, config, logger)
        assert isinstance(manager, StealthManager)


# ══════════════════════════════════════════════════════════════
# Session Manager Tests
# ══════════════════════════════════════════════════════════════

class TestSessionStats:
    def test_defaults(self):
        from instaharvest.session_manager import SessionStats
        s = SessionStats(path='/tmp/test.json')
        assert s.requests == 0
        assert s.is_healthy is True
        assert s.is_expired is False

    def test_success_rate_zero(self):
        from instaharvest.session_manager import SessionStats
        s = SessionStats(path='/tmp/test.json')
        assert s.success_rate == 1.0

    def test_success_rate(self):
        from instaharvest.session_manager import SessionStats
        s = SessionStats(path='/tmp/test.json', requests=10, successes=8)
        assert s.success_rate == 0.8

    def test_status_healthy(self):
        from instaharvest.session_manager import SessionStats
        s = SessionStats(path='/tmp/test.json')
        assert s.status == 'healthy'

    def test_status_expired(self):
        from instaharvest.session_manager import SessionStats
        s = SessionStats(path='/tmp/test.json', is_expired=True)
        assert s.status == 'expired'

    def test_status_unhealthy(self):
        from instaharvest.session_manager import SessionStats
        s = SessionStats(path='/tmp/test.json', is_healthy=False)
        assert s.status == 'unhealthy'

class TestSessionRotationStrategy:
    def test_values(self):
        from instaharvest.session_manager import SessionRotationStrategy
        assert SessionRotationStrategy.ROUND_ROBIN.value == 'round_robin'
        assert SessionRotationStrategy.RANDOM.value == 'random'
        assert SessionRotationStrategy.LEAST_USED.value == 'least_used'

class TestSessionManager:
    def test_init(self):
        from instaharvest.session_manager import SessionManager, SessionRotationStrategy
        sm = SessionManager(rotation=SessionRotationStrategy.RANDOM, max_failures=3, cooldown_seconds=10)
        assert sm.rotation == SessionRotationStrategy.RANDOM
        assert sm.max_failures == 3

    def test_add_session_not_found(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        assert sm.add_session('/nonexistent/path.json') is False

    def test_add_session_valid(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        session_data = json.dumps({'cookies': [{'name': 'ds_user_id', 'value': '12345'}]})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(session_data)
            f.flush()
            result = sm.add_session(f.name)
        os.unlink(f.name)
        assert result is True
        assert sm.total_sessions == 1

    def test_add_session_duplicate(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        session_data = json.dumps({'cookies': [{'name': 'test', 'value': '1'}]})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(session_data)
            f.flush()
            sm.add_session(f.name)
            result = sm.add_session(f.name)
        os.unlink(f.name)
        assert result is False

    def test_add_session_no_cookies(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        session_data = json.dumps({'cookies': []})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(session_data)
            f.flush()
            result = sm.add_session(f.name)
        os.unlink(f.name)
        assert result is False

    def test_add_session_invalid_json(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json')
            f.flush()
            result = sm.add_session(f.name)
        os.unlink(f.name)
        assert result is False

    def test_get_session_empty(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        assert sm.get_session() is None

    def test_get_session_round_robin(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        session_data = json.dumps({'cookies': [{'name': 'test', 'value': '1'}]})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(session_data)
            f.flush()
            sm.add_session(f.name)
            data = sm.get_session()
        os.unlink(f.name)
        assert data is not None
        assert 'cookies' in data

    def test_mark_success(self):
        from instaharvest.session_manager import SessionManager, SessionStats
        sm = SessionManager()
        stats = SessionStats(path='/tmp/test.json')
        sm._sessions.append(stats)
        sm._current_session = stats
        sm.mark_success()
        assert stats.successes == 1
        assert stats.consecutive_failures == 0

    def test_mark_failure(self):
        from instaharvest.session_manager import SessionManager, SessionStats
        sm = SessionManager(max_failures=2)
        stats = SessionStats(path='/tmp/test.json')
        sm._sessions.append(stats)
        sm._current_session = stats
        sm.mark_failure()
        assert stats.failures == 1
        sm.mark_failure()
        assert stats.is_healthy is False

    def test_mark_expired(self):
        from instaharvest.session_manager import SessionManager, SessionStats
        sm = SessionManager()
        stats = SessionStats(path='/tmp/test.json')
        sm._sessions.append(stats)
        sm._current_session = stats
        sm.mark_expired()
        assert stats.is_expired is True
        assert stats.is_healthy is False

    def test_properties(self):
        from instaharvest.session_manager import SessionManager, SessionStats
        sm = SessionManager()
        sm._sessions = [
            SessionStats(path='a', is_healthy=True),
            SessionStats(path='b', is_healthy=False),
            SessionStats(path='c', is_expired=True),
        ]
        assert sm.total_sessions == 3
        assert sm.healthy_count == 1
        assert sm.expired_count == 1

    def test_get_stats(self):
        from instaharvest.session_manager import SessionManager, SessionStats
        sm = SessionManager()
        sm._sessions = [SessionStats(path='/tmp/test.json', requests=5, successes=4, failures=1)]
        stats = sm.get_stats()
        assert len(stats) == 1
        assert stats[0]['requests'] == 5

    def test_reset_all(self):
        from instaharvest.session_manager import SessionManager, SessionStats
        sm = SessionManager()
        s = SessionStats(path='/tmp/test.json', requests=10, failures=5, is_healthy=False)
        sm._sessions = [s]
        sm.reset_all()
        assert s.requests == 0
        assert s.failures == 0
        assert s.is_healthy is True

    def test_current_session_path_none(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        assert sm.current_session_path is None

    def test_add_sessions_from_dir_not_found(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        assert sm.add_sessions_from_dir('/nonexistent/dir/') == 0

    def test_select_session_strategies(self):
        from instaharvest.session_manager import SessionManager, SessionStats, SessionRotationStrategy
        # Random strategy
        sm = SessionManager(rotation=SessionRotationStrategy.RANDOM)
        sessions = [SessionStats(path=f'/tmp/{i}.json', last_used=0) for i in range(3)]
        result = sm._select_session(sessions)
        assert result in sessions

        # Least used
        sm2 = SessionManager(rotation=SessionRotationStrategy.LEAST_USED)
        sessions[0].requests = 10
        sessions[1].requests = 1
        sessions[2].requests = 5
        result2 = sm2._select_session(sessions)
        assert result2.requests == 1


# ══════════════════════════════════════════════════════════════
# ExcelExporter Tests
# ══════════════════════════════════════════════════════════════

class TestExcelExporter:
    def test_init(self):
        from instaharvest.exporters import ExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = ExcelExporter(path)
            assert e.batch_size == 10
            assert e.separate_tags is True
            assert Path(path).exists()

    def test_add_row_with_tags(self):
        from instaharvest.exporters import ExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = ExcelExporter(path)
            e.add_row(post_url='u', tagged_accounts=['a', 'b'], likes='100', post_date='2024-01-01')
            assert len(e.rows) == 2  # separate_tags=True

    def test_add_row_no_tags(self):
        from instaharvest.exporters import ExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = ExcelExporter(path)
            e.add_row(post_url='u', tagged_accounts=[], likes='0', post_date='N/A')
            assert len(e.rows) == 1
            assert e.rows[0]['Tagged Account'] == 'No tags'

    def test_add_multiple_rows(self):
        from instaharvest.exporters import ExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = ExcelExporter(path)
            data = [
                {'url': 'u1', 'tagged_accounts': ['a'], 'likes': '10', 'timestamp': 'd1'},
                {'url': 'u2', 'tagged_accounts': [], 'likes': '20', 'timestamp': 'd2'},
            ]
            e.add_multiple_rows(data)
            assert len(e.rows) == 2

    def test_finalize(self):
        from instaharvest.exporters import ExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = ExcelExporter(path)
            e.add_row(post_url='u', tagged_accounts=['a'], likes='10', post_date='d')
            e.finalize()
            assert len(e.rows) == 0  # Should be flushed


class TestCommentsExporter:
    def test_init(self):
        from instaharvest.exporters import CommentsExporter
        e = CommentsExporter(username='test')
        assert e.username == 'test'
        assert e.export_json is True
        assert e.export_excel is True

    def test_add_post_comments(self):
        from instaharvest.exporters import CommentsExporter
        e = CommentsExporter(username='test', export_excel=True)
        
        # Create mock comment with all required attributes
        mock_comment = MagicMock()
        mock_comment.id = '1'
        mock_comment.author.username = 'user1'
        mock_comment.author.is_verified = False
        mock_comment.text = 'test comment'
        mock_comment.likes_count = 5
        mock_comment.reply_count = 0
        mock_comment.timestamp = '2024-01-01'
        mock_comment.timestamp_iso = '2024-01-01T00:00:00Z'
        mock_comment.permalink = 'url'
        mock_comment.replies = []
        
        # Create mock post_comments
        post_comments = MagicMock()
        post_comments.post_url = 'post_url'
        post_comments.post_id = 'post_id'
        post_comments.get_all_comments_flat.return_value = [mock_comment]
        
        e.add_post_comments(post_comments)
        assert len(e.comments_data) == 1
        assert len(e.excel_rows) == 1


class TestStreamingJSONExporter:
    def test_append_item(self):
        from instaharvest.exporters import StreamingJSONExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.jsonl')
            e = StreamingJSONExporter(path)
            e.append_item({'key': 'value'})
            with open(path) as f:
                content = f.read()
            assert 'value' in content

class TestStreamingExcelExporter:
    def test_init(self):
        from instaharvest.exporters import StreamingExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = StreamingExcelExporter(path, ['Col1', 'Col2'])
            assert Path(path).exists()

    def test_append_row(self):
        from instaharvest.exporters import StreamingExcelExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.xlsx')
            e = StreamingExcelExporter(path, ['Col1', 'Col2'])
            e.append_row(['v1', 'v2'])
            # File should be updated


class TestExportUtilityFunctions:
    def test_export_comments_to_json_list(self):
        from instaharvest.exporters import export_comments_to_json
        mock_data = MagicMock()
        mock_data.to_dict.return_value = {'test': 'data'}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.json')
            result = export_comments_to_json([mock_data], path)
            assert result is True
            with open(path) as f:
                data = json.load(f)
            assert len(data) == 1

    def test_export_comments_to_json_single(self):
        from instaharvest.exporters import export_comments_to_json
        mock_data = MagicMock()
        mock_data.to_dict.return_value = {'test': 'data'}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.json')
            result = export_comments_to_json(mock_data, path)
            assert result is True

    def test_export_comments_to_json_error(self):
        from instaharvest.exporters import export_comments_to_json
        mock_data = MagicMock()
        mock_data.to_dict.side_effect = Exception("fail")
        result = export_comments_to_json(mock_data, '/impossible/path.json', MagicMock())
        assert result is False


# ══════════════════════════════════════════════════════════════
# Parallel Scraper Module-Level Functions
# ══════════════════════════════════════════════════════════════

class TestParallelScraperFunctions:
    def test_parse_number(self):
        from instaharvest.parallel_scraper import _parse_number
        config = ScraperConfig()
        assert _parse_number('1000', config) == 1000
        assert _parse_number('1,000', config) == 1000
        assert _parse_number('', config) is None
        assert _parse_number(None, config) is None

    def test_parse_number_with_suffix(self):
        from instaharvest.parallel_scraper import _parse_number
        config = ScraperConfig()
        result = _parse_number('1.5K', config)
        assert result == 1500

    def test_extract_timestamp_bs4(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        from bs4 import BeautifulSoup
        
        # With title attribute
        html = '<time title="January 1, 2024" datetime="2024-01-01T00:00:00Z">1d</time>'
        soup = BeautifulSoup(html, 'html.parser')
        assert _extract_timestamp_bs4(soup) == 'January 1, 2024'

    def test_extract_timestamp_bs4_datetime(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        from bs4 import BeautifulSoup
        
        html = '<time datetime="2024-01-01T00:00:00Z">1d</time>'
        soup = BeautifulSoup(html, 'html.parser')
        assert _extract_timestamp_bs4(soup) == '2024-01-01T00:00:00Z'

    def test_extract_timestamp_bs4_text(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        from bs4 import BeautifulSoup
        
        html = '<time>January 1, 2024</time>'
        soup = BeautifulSoup(html, 'html.parser')
        assert _extract_timestamp_bs4(soup) == 'January 1, 2024'

    def test_extract_timestamp_bs4_no_time(self):
        from instaharvest.parallel_scraper import _extract_timestamp_bs4
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup('<div>no time</div>', 'html.parser')
        assert _extract_timestamp_bs4(soup) == 'N/A'

    def test_get_worker_logger(self):
        from instaharvest.parallel_scraper import _get_worker_logger
        logger = _get_worker_logger(1)
        assert logger.name == 'Worker-1'

    def test_worker_signal_handler(self):
        from instaharvest.parallel_scraper import _worker_signal_handler
        import instaharvest.parallel_scraper as ps
        event = MagicMock()
        old_event = ps._shutdown_event
        ps._shutdown_event = event
        _worker_signal_handler(2, None)
        event.set.assert_called_once()
        ps._shutdown_event = old_event


class TestParallelPostDataScraper:
    def test_init(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        s = ParallelPostDataScraper()
        assert s.page is None
        assert s.browser is None

    def test_split_into_batches(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        s = ParallelPostDataScraper()
        items = [{'url': f'u{i}', 'type': 'Post'} for i in range(10)]
        batches = s._split_into_batches(items, 3)
        assert len(batches) == 3
        total = sum(len(b) for b in batches)
        assert total == 10


# ══════════════════════════════════════════════════════════════
# Orchestrator Tests
# ══════════════════════════════════════════════════════════════

class TestInstagramOrchestrator:
    def test_init(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert o.shutdown_requested is False
        assert o.config is not None

    def test_init_with_shared_browser(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        sb = MagicMock()
        o = InstagramOrchestrator(shared_browser=sb)
        assert o.shared_browser is sb

    def test_cleanup(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        o._cleanup()  # Should not crash


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
