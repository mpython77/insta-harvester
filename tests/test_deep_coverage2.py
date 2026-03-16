"""
Deep Coverage Tests - Part 2
Targets: interactions, performance, batch_downloader, captcha_solver,
notifications, explore_scraper, hashtag_scraper, location_scraper,
search_api, followers, downloader, post_links, orchestrator deep methods
"""
import pytest
import time
import json
import os
import sys
import tempfile
import threading
from unittest.mock import MagicMock, patch, PropertyMock, AsyncMock, call
from dataclasses import dataclass
from pathlib import Path


def _cfg():
    from instaharvest.config import ScraperConfig
    return ScraperConfig()


# ═══════════════════════════════════════════════════════════════
# InteractionManager
# ═══════════════════════════════════════════════════════════════

class TestInteractionManager:
    def _make(self):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        logger = MagicMock()
        return InteractionManager(page, logger)

    def test_init(self):
        im = self._make()
        assert im.page is not None
        assert im.config is not None

    def test_like_post_already_liked(self):
        im = self._make()
        im.page.locator.side_effect = lambda sel: (
            MagicMock(first=MagicMock(count=MagicMock(return_value=0))) if 'Like' in sel
            else MagicMock(first=MagicMock(count=MagicMock(return_value=1)))
        )
        result = im.like_post()
        assert result is True

    @patch('instaharvest.interactions.time')
    @patch('instaharvest.interactions.random')
    def test_like_post_with_url(self, mock_random, mock_time):
        im = self._make()
        mock_random.uniform.return_value = 0.5
        # Navigate to URL first
        im.page.locator.side_effect = Exception("fail")
        result = im.like_post(url='https://instagram.com/p/ABC/')
        im.page.goto.assert_called_once_with('https://instagram.com/p/ABC/')
        assert result is False

    def test_like_post_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("error")
        assert im.like_post() is False

    @patch('instaharvest.interactions.time')
    @patch('instaharvest.interactions.random')
    def test_comment_post_success(self, mock_random, mock_time):
        im = self._make()
        mock_random.uniform.return_value = 0.5
        mock_random.randint.return_value = 50
        comment_box = MagicMock()
        comment_box.count.return_value = 1
        post_btn = MagicMock()
        post_btn.count.return_value = 1
        post_btn.is_visible.return_value = True
        im.page.locator.side_effect = lambda sel: (
            MagicMock(first=comment_box) if 'comment' in sel.lower() or 'textarea' in sel.lower()
            else MagicMock(first=post_btn)
        )
        result = im.comment_post('Nice post!')
        assert result is True

    @patch('instaharvest.interactions.time')
    @patch('instaharvest.interactions.random')
    def test_comment_post_no_box(self, mock_random, mock_time):
        im = self._make()
        mock_random.uniform.return_value = 0.5
        box = MagicMock()
        box.count.return_value = 0
        im.page.locator.return_value.first = box
        assert im.comment_post('test') is False

    def test_comment_post_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("error")
        assert im.comment_post('test') is False

    @patch('instaharvest.interactions.time')
    def test_like_comment_no_comments(self, mock_time):
        im = self._make()
        items = MagicMock()
        items.count.return_value = 0
        im.page.locator.return_value = items
        assert im.like_comment() is False

    def test_like_comment_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("error")
        assert im.like_comment() is False

    @patch('instaharvest.interactions.time')
    def test_like_all_comments_no_comments(self, mock_time):
        im = self._make()
        items = MagicMock()
        items.count.return_value = 0
        im.page.locator.return_value = items
        result = im.like_all_comments()
        assert result['total'] == 0

    def test_like_reel(self):
        im = self._make()
        im.page.locator.side_effect = Exception("error")
        assert im.like_reel() is False

    def test_comment_reel(self):
        im = self._make()
        im.page.locator.side_effect = Exception("error")
        assert im.comment_reel('test') is False

    @patch('instaharvest.interactions.time')
    @patch('instaharvest.interactions.random')
    def test_next_reel(self, mock_random, mock_time):
        im = self._make()
        mock_random.uniform.return_value = 0.5
        im.next_reel()
        im.page.keyboard.press.assert_called_once_with("ArrowDown")


# ═══════════════════════════════════════════════════════════════
# Performance
# ═══════════════════════════════════════════════════════════════

class TestPerformanceMetrics:
    def test_finalize(self):
        from instaharvest.performance import PerformanceMetrics
        m = PerformanceMetrics(operation_name='test', start_time=time.time() - 1.0, memory_before_mb=100.0)
        m.finalize(memory_after=120.0, cpu_percent=50.0)
        assert m.duration > 0
        assert m.memory_after_mb == 120.0
        assert m.memory_delta_mb == 20.0
        assert m.cpu_percent == 50.0
        assert m.success is True

    def test_finalize_with_error(self):
        from instaharvest.performance import PerformanceMetrics
        m = PerformanceMetrics(operation_name='fail', start_time=time.time())
        m.finalize(memory_after=100.0, cpu_percent=10.0, success=False, error='timeout')
        assert m.success is False
        assert m.error == 'timeout'


class TestPerformanceStats:
    def test_init(self):
        from instaharvest.performance import PerformanceStats
        ps = PerformanceStats()
        assert ps.config is not None
        assert len(ps.metrics) == 0

    def test_add_metric(self):
        from instaharvest.performance import PerformanceStats, PerformanceMetrics
        ps = PerformanceStats()
        m = PerformanceMetrics(operation_name='test', start_time=time.time())
        m.finalize(100.0, 10.0)
        ps.add_metric(m)
        assert len(ps.metrics) == 1

    def test_get_average_duration(self):
        from instaharvest.performance import PerformanceStats, PerformanceMetrics
        ps = PerformanceStats()
        for i in range(3):
            m = PerformanceMetrics(operation_name='op', start_time=time.time(), duration=float(i+1))
            m.end_time = m.start_time + m.duration
            ps.add_metric(m)
        avg = ps.get_average_duration('op')
        assert avg == 2.0

    def test_get_average_no_metrics(self):
        from instaharvest.performance import PerformanceStats
        ps = PerformanceStats()
        assert ps.get_average_duration() == 0.0

    def test_get_total_memory(self):
        from instaharvest.performance import PerformanceStats, PerformanceMetrics
        ps = PerformanceStats()
        m1 = PerformanceMetrics(operation_name='op', start_time=time.time(), memory_after_mb=100.0)
        m2 = PerformanceMetrics(operation_name='op', start_time=time.time(), memory_after_mb=200.0)
        ps.add_metric(m1)
        ps.add_metric(m2)
        assert ps.get_total_memory_used() == 200.0

    def test_get_total_memory_empty(self):
        from instaharvest.performance import PerformanceStats
        ps = PerformanceStats()
        assert ps.get_total_memory_used() == 0.0

    def test_get_success_rate(self):
        from instaharvest.performance import PerformanceStats, PerformanceMetrics
        ps = PerformanceStats()
        m1 = PerformanceMetrics(operation_name='op', start_time=time.time(), success=True)
        m2 = PerformanceMetrics(operation_name='op', start_time=time.time(), success=False)
        ps.add_metric(m1)
        ps.add_metric(m2)
        assert ps.get_success_rate() == 50.0

    def test_get_success_rate_empty(self):
        from instaharvest.performance import PerformanceStats
        ps = PerformanceStats()
        assert ps.get_success_rate() == 100.0

    def test_get_report(self):
        from instaharvest.performance import PerformanceStats, PerformanceMetrics
        ps = PerformanceStats()
        m = PerformanceMetrics(operation_name='scrape', start_time=time.time() - 1.0, duration=1.0, memory_after_mb=100.0, memory_delta_mb=5.0)
        m.end_time = m.start_time + 1.0
        ps.add_metric(m)
        report = ps.get_report()
        assert 'PERFORMANCE REPORT' in report
        assert 'scrape' in report

    def test_get_ops_per_second(self):
        from instaharvest.performance import PerformanceStats, PerformanceMetrics
        ps = PerformanceStats()
        m = PerformanceMetrics(operation_name='op', start_time=time.time())
        ps.add_metric(m)
        ops = ps.get_operations_per_second()
        assert ops > 0


class TestPerformanceMonitor:
    def test_init(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        assert pm.stats is not None

    def test_get_memory_usage(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        mem = pm.get_memory_usage()
        assert mem > 0

    def test_get_cpu_percent(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        cpu = pm.get_cpu_percent()
        assert isinstance(cpu, float)

    def test_measure_context_manager(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        with pm.measure('test_op') as metric:
            _ = sum(range(1000))
        assert len(pm.stats.metrics) == 1
        assert pm.stats.metrics[0].operation_name == 'test_op'
        assert pm.stats.metrics[0].duration >= 0

    def test_measure_context_exception(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        with pytest.raises(ValueError):
            with pm.measure('fail_op'):
                raise ValueError("test error")
        assert len(pm.stats.metrics) == 1
        assert pm.stats.metrics[0].success is False
        assert pm.stats.metrics[0].error == 'test error'

    def test_measure_function_decorator(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        
        @pm.measure_function('my_func')
        def my_func():
            return 42
        
        result = my_func()
        assert result == 42
        assert len(pm.stats.metrics) == 1

    def test_print_report(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        with pm.measure('op'):
            pass
        pm.print_report()  # should not raise

    def test_check_memory_threshold_ok(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        assert pm.check_memory_threshold(threshold_mb=100000) is True

    def test_check_memory_threshold_exceeded(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        assert pm.check_memory_threshold(threshold_mb=0.001) is False

    def test_optimize_memory(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        pm.optimize_memory()  # should not raise

    def test_get_system_info(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        info = pm.get_system_info()
        assert 'cpu_count' in info
        assert 'memory_total_gb' in info
        assert 'process_memory_mb' in info

    def test_log_system_info(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        pm.log_system_info()  # should not raise

    def test_get_stats(self):
        from instaharvest.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        assert pm.get_stats() is pm.stats


class TestPerformanceGlobal:
    def test_get_monitor(self):
        from instaharvest.performance import get_monitor
        import instaharvest.performance as perf_mod
        old = perf_mod._global_monitor
        perf_mod._global_monitor = None
        m = get_monitor()
        assert m is not None
        m2 = get_monitor()
        assert m is m2
        perf_mod._global_monitor = old

    def test_measure_decorator(self):
        from instaharvest.performance import measure
        @measure('decorated_op')
        def my_fn():
            return 99
        result = my_fn()
        assert result == 99


# ═══════════════════════════════════════════════════════════════
# BatchDownloader data models
# ═══════════════════════════════════════════════════════════════

class TestBatchDownloaderModels:
    def test_download_task_repr(self):
        from instaharvest.batch_downloader import DownloadTask
        t = DownloadTask(url='http://example.com', save_path=Path('/tmp/f'), shortcode='ABC', index=0, media_type='image')
        assert 'ABC' in repr(t)

    def test_download_result_repr(self):
        from instaharvest.batch_downloader import DownloadResult, DownloadTask
        task = DownloadTask(url='http://x', save_path=Path('/tmp'), shortcode='DEF', index=1)
        r = DownloadResult(task=task, success=True, file_size=1024, duration=1.0)
        assert '✅' in repr(r)
        r2 = DownloadResult(task=task, success=False, duration=0.5)
        assert '❌' in repr(r2)

    def test_format_size(self):
        from instaharvest.batch_downloader import DownloadResult
        assert DownloadResult._format_size(500) == '500B'
        assert 'KB' in DownloadResult._format_size(2048)
        assert 'MB' in DownloadResult._format_size(2 * 1024 * 1024)

    def test_batch_result_properties(self):
        from instaharvest.batch_downloader import BatchResult, DownloadResult, DownloadTask
        task = DownloadTask(url='http://x', save_path=Path('/tmp'))
        r1 = DownloadResult(task=task, success=True, file_size=1024)
        r2 = DownloadResult(task=task, success=False)
        batch = BatchResult(results=[r1, r2], total=2, start_time=1.0, end_time=3.0)
        assert batch.success_count == 1
        assert batch.failed_count == 1
        assert batch.total_bytes == 1024
        assert batch.duration == 2.0
        assert batch.speed == 512.0
        summary = batch.summary()
        assert summary['total'] == 2
        assert summary['success'] == 1

    def test_batch_result_zero_duration(self):
        from instaharvest.batch_downloader import BatchResult
        batch = BatchResult()
        assert batch.duration == 0.0
        assert batch.speed == 0


class TestProgressTracker:
    def test_init(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=100)
        assert pt.total == 100
        assert pt.completed == 0

    def test_update_success(self):
        from instaharvest.batch_downloader import ProgressTracker, DownloadResult, DownloadTask
        pt = ProgressTracker(total=10)
        task = DownloadTask(url='http://x', save_path=Path('/tmp'))
        result = DownloadResult(task=task, success=True, file_size=512)
        pt.update(result)
        assert pt.completed == 1
        assert pt.bytes_downloaded == 512

    def test_update_failure(self):
        from instaharvest.batch_downloader import ProgressTracker, DownloadResult, DownloadTask
        pt = ProgressTracker(total=10)
        task = DownloadTask(url='http://x', save_path=Path('/tmp'))
        result = DownloadResult(task=task, success=False)
        pt.update(result)
        assert pt.failed == 1

    def test_skip(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=10)
        pt.skip()
        assert pt.skipped == 1
        assert pt.completed == 1

    def test_print_progress(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=10)
        pt.print_progress(force=True)  # should not raise

    def test_finish(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=10)
        pt.finish()  # should not raise

    def test_repr(self):
        from instaharvest.batch_downloader import ProgressTracker
        pt = ProgressTracker(total=5)
        assert '0/5' in repr(pt)


class TestBatchDownloaderInit:
    def test_init_default(self):
        from instaharvest.batch_downloader import BatchDownloader
        bd = BatchDownloader()
        assert bd.max_workers == 8
        assert bd.max_retries == 2

    def test_init_custom_dir(self):
        from instaharvest.batch_downloader import BatchDownloader
        import tempfile
        td = tempfile.mkdtemp()
        bd = BatchDownloader(output_dir=td)
        assert bd.output_dir == Path(td)

    def test_download_posts_empty(self):
        from instaharvest.batch_downloader import BatchDownloader
        bd = BatchDownloader()
        result = bd.download_posts([], username='test')
        assert result.total == 0


# ═══════════════════════════════════════════════════════════════
# CaptchaSolver
# ═══════════════════════════════════════════════════════════════

class TestCaptchaSolver:
    def test_init_2captcha(self):
        from instaharvest.captcha_solver import CaptchaSolver
        cs = CaptchaSolver(api_key='test', provider='2captcha')
        assert cs.api_key == 'test'
        from instaharvest.captcha_solver import CaptchaProvider
        assert cs.provider == CaptchaProvider.TWO_CAPTCHA

    def test_init_anticaptcha(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        cs = CaptchaSolver(api_key='key', provider='anticaptcha')
        assert cs.provider == CaptchaProvider.ANTI_CAPTCHA

    def test_init_anti_captcha_hyphen(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        cs = CaptchaSolver(api_key='key', provider='anti-captcha')
        assert cs.provider == CaptchaProvider.ANTI_CAPTCHA

    def test_init_default_provider(self):
        from instaharvest.captcha_solver import CaptchaSolver, CaptchaProvider
        cs = CaptchaSolver(api_key='key', provider='unknown')
        assert cs.provider == CaptchaProvider.TWO_CAPTCHA

    def test_detect_captcha_not_found(self):
        from instaharvest.captcha_solver import CaptchaSolver
        cs = CaptchaSolver()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 0
        page.locator.return_value.first = el
        page.url = 'https://instagram.com/feed/'
        assert cs.detect_captcha(page) is False

    def test_detect_captcha_recaptcha_found(self):
        from instaharvest.captcha_solver import CaptchaSolver
        cs = CaptchaSolver()
        page = MagicMock()
        el_found = MagicMock()
        el_found.count.return_value = 1
        page.locator.return_value.first = el_found
        page.url = 'https://instagram.com/'
        assert cs.detect_captcha(page) is True

    def test_detect_captcha_url(self):
        from instaharvest.captcha_solver import CaptchaSolver
        cs = CaptchaSolver()
        page = MagicMock()
        el = MagicMock()
        el.count.return_value = 0
        page.locator.return_value.first = el
        page.url = 'https://instagram.com/challenge/abc'
        assert cs.detect_captcha(page) is True

    def test_detect_captcha_exception(self):
        from instaharvest.captcha_solver import CaptchaSolver
        cs = CaptchaSolver()
        page = MagicMock()
        page.locator.side_effect = Exception("error")
        page.url = 'https://instagram.com/'
        # Should not raise, returns False
        assert cs.detect_captcha(page) is False

    def test_solve_no_api_key(self):
        from instaharvest.captcha_solver import CaptchaSolver
        cs = CaptchaSolver(api_key='')
        page = MagicMock()
        assert cs.solve(page) is False


# ═══════════════════════════════════════════════════════════════
# NotificationItem data model
# ═══════════════════════════════════════════════════════════════

class TestNotificationItem:
    def test_to_dict(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(
            type='post_like',
            usernames=['user1'],
            text='liked your post',
            time_text='1d',
            section='Yesterday'
        )
        d = n.to_dict()
        assert d['type'] == 'post_like'
        assert d['usernames'] == ['user1']
        assert d['section'] == 'Yesterday'

    def test_defaults(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem()
        assert n.type == 'other'
        assert n.usernames == []
        assert n.is_grouped is False
        assert n.extra_count == 0


class TestNotificationReader:
    def test_init(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr.page is page

    def test_detect_type_comment_like(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('liked your comment: nice pic!') == 'comment_like'

    def test_detect_type_post_like(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('liked your post') == 'post_like'

    def test_detect_type_follow(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('started following you') == 'follow'

    def test_detect_type_comment(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('commented: hello there') == 'comment'

    def test_detect_type_mention(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('mentioned you in a comment') == 'mention'

    def test_detect_type_other(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('some random text') == 'other'

    def test_detect_type_uzbek_comment_like(self):
        from instaharvest.notifications import NotificationReader
        page = MagicMock()
        logger = MagicMock()
        nr = NotificationReader(page, logger)
        assert nr._detect_type('kommentingizni yoqtirdi') == 'comment_like'


# ═══════════════════════════════════════════════════════════════
# CaptchaProvider enum
# ═══════════════════════════════════════════════════════════════

class TestCaptchaProvider:
    def test_values(self):
        from instaharvest.captcha_solver import CaptchaProvider
        assert CaptchaProvider.TWO_CAPTCHA.value == '2captcha'
        assert CaptchaProvider.ANTI_CAPTCHA.value == 'anticaptcha'


# ═══════════════════════════════════════════════════════════════
# Downloader
# ═══════════════════════════════════════════════════════════════

class TestDownloader:
    def test_init(self):
        from instaharvest.downloader import MediaDownloader
        md = MediaDownloader()
        assert md is not None

    def test_has_attributes(self):
        from instaharvest.downloader import MediaDownloader
        md = MediaDownloader()
        assert hasattr(md, 'config') or hasattr(md, 'logger')

    def test_config_default(self):
        from instaharvest.downloader import MediaDownloader
        md = MediaDownloader()
        assert md.config is not None


# ═══════════════════════════════════════════════════════════════
# PostLinksScraper
# ═══════════════════════════════════════════════════════════════

class TestPostLinksScraperInit:
    def test_init(self):
        from instaharvest.post_links import PostLinksScraper
        pls = PostLinksScraper()
        assert pls.config is not None
        assert pls.interrupted is False


# ═══════════════════════════════════════════════════════════════
# Orchestrator — interact_with_post
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorInteraction:
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

    @patch('instaharvest.orchestrator.PostDataScraper')
    @patch('instaharvest.orchestrator.InteractionManager')
    @patch('instaharvest.orchestrator.time')
    def test_interact_like_success(self, mock_time, MockIM, MockPDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        MockPDS.return_value = mock_scraper
        mock_interaction = MagicMock()
        mock_interaction.like_post.return_value = True
        MockIM.return_value = mock_interaction
        result = o.interact_with_post('http://post', like=True)
        assert result is True
        mock_scraper.close.assert_called_once()

    @patch('instaharvest.orchestrator.PostDataScraper')
    @patch('instaharvest.orchestrator.InteractionManager')
    @patch('instaharvest.orchestrator.time')
    def test_interact_comment(self, mock_time, MockIM, MockPDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        MockPDS.return_value = mock_scraper
        mock_interaction = MagicMock()
        mock_interaction.comment_post.return_value = True
        MockIM.return_value = mock_interaction
        result = o.interact_with_post('http://post', comment='Nice!')
        assert result is True

    @patch('instaharvest.orchestrator.InteractionManager')
    @patch('instaharvest.orchestrator.time')
    def test_interact_shared_browser(self, mock_time, MockIM):
        o = self._make_orch()
        sb = MagicMock()
        o.shared_browser = sb
        mock_interaction = MagicMock()
        mock_interaction.like_post.return_value = True
        MockIM.return_value = mock_interaction
        result = o.interact_with_post('http://post', like=True)
        assert result is True

    @patch('instaharvest.orchestrator.PostDataScraper')
    @patch('instaharvest.orchestrator.InteractionManager')
    @patch('instaharvest.orchestrator.time')
    def test_interact_fail(self, mock_time, MockIM, MockPDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        MockPDS.return_value = mock_scraper
        mock_interaction = MagicMock()
        mock_interaction.like_post.return_value = False
        MockIM.return_value = mock_interaction
        result = o.interact_with_post('http://post', like=True)
        assert result is False


# ═══════════════════════════════════════════════════════════════
# Orchestrator — scrape_comments_only
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorComments:
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

    @patch('instaharvest.orchestrator.CommentsExporter')
    @patch('instaharvest.orchestrator.CommentScraper')
    def test_scrape_comments_only_with_urls(self, MockCS, MockCE):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_comment = MagicMock()
        mock_comment.total_comments_scraped = 5
        mock_comment.total_replies_scraped = 1
        mock_scraper.scrape.return_value = mock_comment
        MockCS.return_value = mock_scraper
        
        result = o.scrape_comments_only(
            username='test',
            post_urls=['http://p1'],
            save_excel=False,
            export_json=False
        )
        assert result is not None

    @patch('instaharvest.orchestrator.PostLinksScraper')
    @patch('instaharvest.orchestrator.CommentScraper')
    def test_scrape_comments_no_urls(self, MockCS, MockPLS):
        o = self._make_orch()
        mock_links = MagicMock()
        mock_links.interrupted = False
        mock_links.scrape.return_value = [{'url': 'http://p1', 'type': 'Post'}]
        MockPLS.return_value = mock_links
        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = MagicMock(total_comments_scraped=0, total_replies_scraped=0)
        MockCS.return_value = mock_scraper
        
        result = o.scrape_comments_only(username='test', save_excel=False, export_json=False)
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# Orchestrator — _scrape_posts_sequential & _scrape_reels_sequential
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorSequential:
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

    @patch('instaharvest.orchestrator.PostDataScraper')
    @patch('instaharvest.orchestrator.time')
    def test_scrape_posts_sequential_success(self, mock_time, MockPDS):
        o = self._make_orch()
        from instaharvest.post_data import PostData
        mock_scraper = MagicMock()
        mock_data = PostData(url='http://p1', tagged_accounts=['a'], likes='10', timestamp='Jan', content_type='Post')
        mock_scraper.scrape.return_value = mock_data
        MockPDS.return_value = mock_scraper
        result = o._scrape_posts_sequential([{'url': 'http://p1', 'type': 'Post'}])
        assert len(result) == 1

    @patch('instaharvest.orchestrator.PostDataScraper')
    @patch('instaharvest.orchestrator.time')
    def test_scrape_posts_sequential_error(self, mock_time, MockPDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.scrape.side_effect = Exception("fail")
        MockPDS.return_value = mock_scraper
        result = o._scrape_posts_sequential([{'url': 'http://p1', 'type': 'Post'}])
        assert len(result) == 1
        assert result[0].likes == 'ERROR'

    @patch('instaharvest.orchestrator.PostDataScraper')
    @patch('instaharvest.orchestrator.time')
    def test_scrape_posts_sequential_shutdown(self, mock_time, MockPDS):
        o = self._make_orch()
        o.shutdown_requested = True
        mock_scraper = MagicMock()
        MockPDS.return_value = mock_scraper
        result = o._scrape_posts_sequential([{'url': 'http://p1', 'type': 'Post'}])
        assert len(result) == 0

    @patch('instaharvest.orchestrator.ReelDataScraper')
    @patch('instaharvest.orchestrator.time')
    def test_scrape_reels_sequential_success(self, mock_time, MockRDS):
        o = self._make_orch()
        from instaharvest.reel_data import ReelData
        mock_scraper = MagicMock()
        mock_data = ReelData(url='http://r1', tagged_accounts=[], likes='5', timestamp='Feb', content_type='Reel')
        mock_scraper.scrape.return_value = mock_data
        MockRDS.return_value = mock_scraper
        result = o._scrape_reels_sequential(['http://r1'])
        assert len(result) == 1

    @patch('instaharvest.orchestrator.ReelDataScraper')
    @patch('instaharvest.orchestrator.time')
    def test_scrape_reels_sequential_error(self, mock_time, MockRDS):
        o = self._make_orch()
        mock_scraper = MagicMock()
        mock_scraper.scrape.side_effect = Exception("fail")
        MockRDS.return_value = mock_scraper
        result = o._scrape_reels_sequential(['http://r1'])
        assert len(result) == 1
        assert result[0].likes == 'ERROR'

    @patch('instaharvest.orchestrator.ReelDataScraper')
    @patch('instaharvest.orchestrator.time')
    def test_scrape_reels_sequential_shutdown(self, mock_time, MockRDS):
        o = self._make_orch()
        o.shutdown_requested = True
        mock_scraper = MagicMock()
        MockRDS.return_value = mock_scraper
        result = o._scrape_reels_sequential(['http://r1'])
        assert len(result) == 0


# ═══════════════════════════════════════════════════════════════
# ExploreScaper / HashtagScraper / LocationScraper / SearchAPI
# ═══════════════════════════════════════════════════════════════

class TestDiscoveryScrapers:
    def test_explore_scraper_init(self):
        from instaharvest.explore_scraper import ExploreScraper
        es = ExploreScraper()
        assert es.config is not None

    def test_hashtag_scraper_init(self):
        from instaharvest.hashtag_scraper import HashtagScraper
        hs = HashtagScraper()
        assert hs.config is not None

    def test_location_scraper_init(self):
        from instaharvest.location_scraper import LocationScraper
        ls = LocationScraper()
        assert ls.config is not None

    def test_search_api_init(self):
        from instaharvest.search_api import SearchAPI
        sa = SearchAPI()
        assert sa.config is not None


# ═══════════════════════════════════════════════════════════════
# Followers
# ═══════════════════════════════════════════════════════════════

class TestFollowersCollector:
    def test_init(self):
        from instaharvest.followers import FollowersCollector
        fc = FollowersCollector()
        assert fc.config is not None
