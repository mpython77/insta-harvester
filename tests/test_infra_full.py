"""
Tests for orchestration modules: orchestrator, parallel_scraper, async_engine
and supporting: proxy, stealth, session_manager, shared_browser,
exporters, diagnostics, performance, notifications, webhooks
"""

import pytest
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from instaharvest.config import ScraperConfig


# ═══════════════════════════════════════════════════════════
# ProxyManager
# ═══════════════════════════════════════════════════════════

class TestProxyManager:
    def test_init_no_proxies(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        assert pm.has_proxies is False
        assert pm.healthy_count == 0

    def test_init_single_proxy(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://user:pass@proxy.com:8080')
        assert pm.has_proxies is True
        assert pm.healthy_count == 1

    def test_init_pool(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxies=['http://p1:8080', 'http://p2:8080'])
        assert pm.has_proxies is True
        assert len(pm._proxy_pool) == 2

    def test_get_proxy_no_pool(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        assert pm.get_proxy() is None

    def test_get_proxy_single(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        proxy = pm.get_proxy()
        assert proxy is not None
        assert proxy.server == 'http://proxy:8080'

    def test_get_for_playwright(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://user:pass@proxy:8080')
        result = pm.get_for_playwright()
        assert result['server'] == 'http://proxy:8080'
        assert result['username'] == 'user'

    def test_get_for_curl(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://user:pass@proxy:8080')
        result = pm.get_for_curl()
        assert 'user:pass' in result

    def test_get_for_requests(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        result = pm.get_for_requests()
        assert 'http' in result
        assert 'https' in result

    def test_get_for_requests_none(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        assert pm.get_for_requests() is None

    def test_mark_success(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        pm.get_proxy()
        pm.mark_success()
        stats = pm._proxy_stats['http://proxy:8080']
        assert stats.successes == 1

    def test_mark_failure(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        pm.get_proxy()
        pm.mark_failure(error='timeout')
        stats = pm._proxy_stats['http://proxy:8080']
        assert stats.failures == 1

    def test_mark_failure_disables_proxy(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080', max_failures=2)
        pm.get_proxy()
        pm.mark_failure()
        pm.mark_failure()
        stats = pm._proxy_stats['http://proxy:8080']
        assert stats.is_healthy is False

    def test_rotation_round_robin(self):
        from instaharvest.proxy import ProxyManager, RotationStrategy
        pm = ProxyManager(
            proxies=['http://p1:80', 'http://p2:80'],
            rotation_strategy=RotationStrategy.ROUND_ROBIN,
            rotation_interval=1
        )
        p1 = pm.get_proxy()
        p2 = pm.get_proxy()
        # After interval they should rotate
        assert p1 is not None and p2 is not None

    def test_rotation_random(self):
        from instaharvest.proxy import ProxyManager, RotationStrategy
        pm = ProxyManager(
            proxies=['http://p1:80', 'http://p2:80'],
            rotation_strategy=RotationStrategy.RANDOM,
        )
        proxy = pm.get_proxy()
        assert proxy is not None

    def test_rotation_sticky(self):
        from instaharvest.proxy import ProxyManager, RotationStrategy
        pm = ProxyManager(
            proxies=['http://p1:80', 'http://p2:80'],
            rotation_strategy=RotationStrategy.STICKY,
        )
        p1 = pm.get_proxy()
        p2 = pm.get_proxy()
        assert p1.server == p2.server

    def test_current_proxy_all_unhealthy_reset(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080', max_failures=1)
        pm.get_proxy()
        pm.mark_failure()
        # All unhealthy, current_proxy should reset
        proxy = pm.current_proxy
        assert proxy is not None

    def test_parse_proxy_no_protocol(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        config = pm._parse_proxy('proxy.com:8080')
        assert config.server == 'http://proxy.com:8080'

    def test_parse_proxy_empty_raises(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        with pytest.raises(ValueError):
            pm._parse_proxy('')

    def test_add_proxy_invalid(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        pm._add_proxy('')  # Should not crash

    def test_get_stats(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        stats = pm.get_stats()
        assert stats['total_proxies'] == 1

    def test_get_stats_summary(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        summary = pm.get_stats_summary()
        assert '1 total' in summary

    def test_repr_no_proxies(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        assert 'no proxies' in repr(pm)

    def test_repr_with_proxies(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        assert '1 proxies' in repr(pm)

    def test_from_config(self):
        from instaharvest.proxy import ProxyManager
        cfg = MagicMock()
        cfg.proxy_url = 'http://proxy:8080'
        cfg.proxies = []
        cfg.proxy_rotation = True
        cfg.proxy_rotation_interval = 10
        cfg.proxy_max_failures = 3
        cfg.proxy_check_on_start = False
        pm = ProxyManager.from_config(cfg)
        assert pm.has_proxies is True

    def test_check_proxy(self):
        from instaharvest.proxy import ProxyManager, ProxyConfig
        pm = ProxyManager(proxy_url='http://proxy:8080')
        proxy_cfg = pm._proxy_pool[0]
        with patch('requests.get', side_effect=Exception("timeout")):
            result = pm.check_proxy(proxy_cfg)
        assert result['is_healthy'] is False

    def test_check_all_proxies(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxy_url='http://proxy:8080')
        with patch.object(pm, 'check_proxy', return_value={'is_healthy': True, 'latency_ms': 100, 'ip': '1.2.3.4', 'country': 'US', 'city': 'NY', 'country_code': 'US'}):
            results = pm.check_all_proxies(verbose=False)
        assert 'http://proxy:8080' in results

    def test_auto_remove_dead(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager(proxies=['http://p1:80', 'http://p2:80'], max_failures=1)
        pm.get_proxy()
        pm._proxy_stats['http://p1:80'].is_healthy = False
        removed = pm.auto_remove_dead()
        assert removed == 1
        assert len(pm._proxy_pool) == 1

    def test_load_from_file_txt(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('http://p1:80\nhttp://p2:80\n# comment\n')
            path = f.name
        import os
        try:
            count = pm.load_from_file(path)
            assert count == 2
        finally:
            os.unlink(path)

    def test_load_from_file_json(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(['http://p1:80', 'http://p2:80'], f)
            path = f.name
        import os
        try:
            count = pm.load_from_file(path)
            assert count == 2
        finally:
            os.unlink(path)

    def test_load_from_file_not_found(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        count = pm.load_from_file('/nonexistent/proxies.txt')
        assert count == 0

    def test_load_from_url(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = 'http://p1:80\nhttp://p2:80\n'
            mock_get.return_value = mock_resp
            count = pm.load_from_url('https://example.com/proxies')
        assert count == 2

    def test_load_from_url_failure(self):
        from instaharvest.proxy import ProxyManager
        pm = ProxyManager()
        with patch('requests.get', side_effect=Exception("err")):
            count = pm.load_from_url('https://example.com/proxies')
        assert count == 0


class TestProxyStats:
    def test_success_rate_no_requests(self):
        from instaharvest.proxy import ProxyStats
        s = ProxyStats(url='http://p:80')
        assert s.success_rate == 1.0

    def test_success_rate_with_requests(self):
        from instaharvest.proxy import ProxyStats
        s = ProxyStats(url='http://p:80', requests=10, successes=8)
        assert s.success_rate == 0.8

    def test_location_full(self):
        from instaharvest.proxy import ProxyStats
        s = ProxyStats(url='http://p:80', city='NY', country='US')
        assert s.location == 'NY, US'

    def test_location_country_only(self):
        from instaharvest.proxy import ProxyStats
        s = ProxyStats(url='http://p:80', country='US')
        assert s.location == 'US'

    def test_location_unknown(self):
        from instaharvest.proxy import ProxyStats
        s = ProxyStats(url='http://p:80')
        assert s.location == 'Unknown'


class TestProxyConfig:
    def test_has_auth_true(self):
        from instaharvest.proxy import ProxyConfig
        c = ProxyConfig(server='http://p:80', username='u', password='p')
        assert c.has_auth is True

    def test_has_auth_false(self):
        from instaharvest.proxy import ProxyConfig
        c = ProxyConfig(server='http://p:80')
        assert c.has_auth is False

    def test_to_playwright(self):
        from instaharvest.proxy import ProxyConfig
        c = ProxyConfig(server='http://p:80', username='u', password='p')
        result = c.to_playwright()
        assert result['server'] == 'http://p:80'
        assert result['username'] == 'u'

    def test_to_curl_with_auth(self):
        from instaharvest.proxy import ProxyConfig
        c = ProxyConfig(server='http://p:80', username='u', password='p', host='p', port=80)
        result = c.to_curl()
        assert 'u:p' in result

    def test_to_curl_no_auth(self):
        from instaharvest.proxy import ProxyConfig
        c = ProxyConfig(server='http://p:80')
        assert c.to_curl() == 'http://p:80'


class TestCreateProxyManagerFromConfig:
    def test_with_rotation(self):
        from instaharvest.proxy import create_proxy_manager_from_config
        cfg = MagicMock()
        cfg.proxy_url = 'http://p:80'
        cfg.proxies = []
        cfg.proxy_rotation = True
        cfg.proxy_rotation_interval = 5
        cfg.proxy_max_failures = 3
        cfg.proxy_check_on_start = False
        pm = create_proxy_manager_from_config(cfg, MagicMock())
        assert pm.has_proxies is True

    def test_without_rotation(self):
        from instaharvest.proxy import create_proxy_manager_from_config, RotationStrategy
        cfg = MagicMock()
        cfg.proxy_url = None
        cfg.proxies = []
        cfg.proxy_rotation = False
        cfg.proxy_rotation_interval = 10
        cfg.proxy_max_failures = 3
        cfg.proxy_check_on_start = False
        pm = create_proxy_manager_from_config(cfg, MagicMock())
        assert pm.rotation_strategy == RotationStrategy.STICKY


# ═══════════════════════════════════════════════════════════
# StealthManager
# ═══════════════════════════════════════════════════════════

class TestStealthManager:
    def test_init(self):
        from instaharvest.stealth import StealthManager
        sm = StealthManager(config=ScraperConfig())
        assert sm is not None

    def test_apply_context_stealth(self):
        from instaharvest.stealth import StealthManager
        sm = StealthManager(config=ScraperConfig())
        ctx = MagicMock()
        sm.apply_context_stealth(ctx)

    def test_apply_page_stealth(self):
        from instaharvest.stealth import StealthManager
        sm = StealthManager(config=ScraperConfig())
        page = MagicMock()
        sm.apply_page_stealth(page)


# ═══════════════════════════════════════════════════════════
# SessionManager
# ═══════════════════════════════════════════════════════════

class TestSessionManager:
    def test_init(self):
        from instaharvest.session_manager import SessionManager
        sm = SessionManager()
        assert sm is not None


# ═══════════════════════════════════════════════════════════
# SharedBrowser
# ═══════════════════════════════════════════════════════════

class TestSharedBrowser:
    def test_import(self):
        from instaharvest.shared_browser import SharedBrowser
        assert SharedBrowser is not None


# ═══════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════

class TestOrchestrator:
    def test_import(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        assert InstagramOrchestrator is not None


# ═══════════════════════════════════════════════════════════
# ParallelScraper
# ═══════════════════════════════════════════════════════════

class TestParallelScraper:
    def test_import(self):
        from instaharvest.parallel_scraper import Manager
        assert Manager is not None


# ═══════════════════════════════════════════════════════════
# AsyncEngine
# ═══════════════════════════════════════════════════════════

class TestAsyncEngine:
    def test_import(self):
        from instaharvest.async_engine import AsyncBaseScraper
        assert AsyncBaseScraper is not None


# ═══════════════════════════════════════════════════════════
# Diagnostics
# ═══════════════════════════════════════════════════════════

class TestDiagnostics:
    def test_import(self):
        import instaharvest.diagnostics as diag_mod
        assert diag_mod is not None


# ═══════════════════════════════════════════════════════════
# Performance
# ═══════════════════════════════════════════════════════════

class TestPerformance:
    def test_import(self):
        from instaharvest.performance import PerformanceMonitor
        assert PerformanceMonitor is not None


# ═══════════════════════════════════════════════════════════
# Exporters
# ═══════════════════════════════════════════════════════════

class TestExporters:
    def test_import(self):
        import instaharvest.exporters as exp
        assert exp is not None


# ═══════════════════════════════════════════════════════════
# Webhooks
# ═══════════════════════════════════════════════════════════

class TestWebhooks:
    def test_import(self):
        import instaharvest.webhooks as webhooks_mod
        assert webhooks_mod is not None


# ═══════════════════════════════════════════════════════════
# SecurityManager (remaining lines)
# ═══════════════════════════════════════════════════════════

class TestSecurityManagerFull:
    def test_get_random_ua_custom_list(self):
        from instaharvest.security import SecurityManager
        result = SecurityManager.get_random_user_agent(custom_list=['CustomUA/1.0'])
        assert result == 'CustomUA/1.0'

    def test_get_random_ua_fake_useragent(self):
        from instaharvest.security import SecurityManager
        mock_ua = MagicMock()
        mock_ua.chrome = 'Chrome/120'
        with patch.dict('sys.modules', {'fake_useragent': MagicMock(UserAgent=MagicMock(return_value=mock_ua))}):
            with patch('random.choice', side_effect=['chrome', 'Chrome/120']):
                result = SecurityManager.get_random_user_agent()
                # Should use fake_useragent or fallback
                assert isinstance(result, str)

    def test_get_random_ua_fallback(self):
        from instaharvest.security import SecurityManager
        with patch('builtins.__import__', side_effect=ImportError("no fake_useragent")):
            result = SecurityManager.get_random_user_agent()
            assert isinstance(result, str)

    def test_format_proxy_none(self):
        from instaharvest.security import SecurityManager
        assert SecurityManager.format_proxy(None) is None
        assert SecurityManager.format_proxy('') is None

    def test_format_proxy_dict(self):
        from instaharvest.security import SecurityManager
        d = {'server': 'http://p:80'}
        assert SecurityManager.format_proxy(d) == d

    def test_format_proxy_no_protocol(self):
        from instaharvest.security import SecurityManager
        result = SecurityManager.format_proxy('proxy:8080')
        assert result['server'] == 'http://proxy:8080'

    def test_format_proxy_with_auth(self):
        from instaharvest.security import SecurityManager
        result = SecurityManager.format_proxy('http://user:pass@proxy:8080')
        assert result['username'] == 'user'
        assert result['password'] == 'pass'

    def test_format_proxy_parse_error(self):
        from instaharvest.security import SecurityManager
        # Force parse error by patching urllib.parse.urlparse used inside format_proxy
        with patch('urllib.parse.urlparse', side_effect=Exception("bad url")):
            result = SecurityManager.format_proxy('bad://url')
        assert 'server' in result

    def test_get_random_proxy_empty(self):
        from instaharvest.security import SecurityManager
        assert SecurityManager.get_random_proxy([]) is None

    def test_get_random_proxy_list(self):
        from instaharvest.security import SecurityManager
        result = SecurityManager.get_random_proxy(['http://p:80'])
        assert result['server'] == 'http://p:80'


# ═══════════════════════════════════════════════════════════
# ErrorHandler extended
# ═══════════════════════════════════════════════════════════

class TestErrorHandlerFull:
    def test_retry_with_backoff_defaults(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        result = eh.retry_with_backoff(lambda: 42)
        assert result == 42

    def test_retry_with_backoff_fails(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        with patch('time.sleep'):
            with pytest.raises(ValueError):
                eh.retry_with_backoff(
                    lambda: (_ for _ in ()).throw(ValueError("fail")),
                    max_retries=1,
                    initial_delay=0.01,
                    backoff_factor=1.0,
                    exceptions=(ValueError,)
                )

    def test_retry_partial_fail_then_success(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        counter = {'n': 0}
        def sometimes_fail():
            counter['n'] += 1
            if counter['n'] < 2:
                raise ValueError("try again")
            return 'ok'
        with patch('time.sleep'):
            result = eh.retry_with_backoff(sometimes_fail, max_retries=3, initial_delay=0.01)
        assert result == 'ok'

    def test_safe_extract_success(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        assert eh.safe_extract(lambda: 'val', 'field') == 'val'

    def test_safe_extract_fail_default(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        result = eh.safe_extract(lambda: 1/0, 'field', default='N/A')
        assert result == 'N/A'

    def test_safe_extract_critical(self):
        from instaharvest.error_handler import ErrorHandler
        from instaharvest.exceptions import HTMLStructureChangedError
        eh = ErrorHandler()
        with pytest.raises(HTMLStructureChangedError):
            eh.safe_extract(lambda: 1/0, 'field', critical=True)

    def test_safe_extract_critical_with_url(self):
        from instaharvest.error_handler import ErrorHandler
        from instaharvest.exceptions import HTMLStructureChangedError
        eh = ErrorHandler()
        with pytest.raises(HTMLStructureChangedError):
            eh.safe_extract(
                lambda: 1/0, 'field', critical=True,
                url='https://ig.com/p/ABC/', selector='div.test'
            )

    def test_with_recovery_primary(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        result = eh.with_recovery(lambda: 'primary', lambda: 'fallback', 'test')
        assert result == 'primary'

    def test_with_recovery_fallback(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        result = eh.with_recovery(lambda: 1/0, lambda: 'fallback', 'test')
        assert result == 'fallback'

    def test_with_recovery_both_fail(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        result = eh.with_recovery(lambda: 1/0, lambda: 1/0, 'test', default='def')
        assert result == 'def'

    def test_with_recovery_no_fallback(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        result = eh.with_recovery(lambda: 1/0, element_name='test', default='def')
        assert result == 'def'

    def test_get_stats(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        assert eh.get_stats() is not None

    def test_print_stats(self):
        from instaharvest.error_handler import ErrorHandler
        eh = ErrorHandler()
        eh.print_stats()  # should not crash


class TestErrorStatsReport:
    def test_report_no_errors(self):
        from instaharvest.error_handler import ErrorStats
        stats = ErrorStats()
        report = stats.get_report()
        assert 'Total Errors: 0' in report
        assert 'Recovery Rate: 100.0%' in report

    def test_report_with_errors(self):
        from instaharvest.error_handler import ErrorStats, ErrorContext
        stats = ErrorStats()
        ctx = ErrorContext(
            timestamp='2025-01-01 12:00:00',
            function_name='test_func',
            error_type='ValueError',
            error_message='short error'
        )
        stats.add_error(ctx, recovered=True)
        report = stats.get_report()
        assert 'Total Errors: 1' in report
        assert 'ValueError' in report

    def test_recovery_rate_zero(self):
        from instaharvest.error_handler import ErrorStats, ErrorContext
        stats = ErrorStats()
        ctx = ErrorContext(timestamp='t', function_name='f', error_type='E', error_message='e')
        stats.add_error(ctx, recovered=False)
        assert stats.get_recovery_rate() == 0.0


class TestRetryOnErrorDecorator:
    def test_success(self):
        from instaharvest.error_handler import retry_on_error
        @retry_on_error(max_retries=2, delay=0.01)
        def good():
            return 'ok'
        with patch('time.sleep'):
            assert good() == 'ok'

    def test_fail_all(self):
        from instaharvest.error_handler import retry_on_error
        @retry_on_error(max_retries=1, delay=0.01)
        def bad():
            raise RuntimeError("always fails")
        with patch('time.sleep'):
            with pytest.raises(RuntimeError):
                bad()

    def test_retry_then_succeed(self):
        from instaharvest.error_handler import retry_on_error
        counter = {'n': 0}
        @retry_on_error(max_retries=3, delay=0.01)
        def flaky():
            counter['n'] += 1
            if counter['n'] < 3:
                raise ValueError("retry")
            return 'done'
        with patch('time.sleep'):
            assert flaky() == 'done'


class TestLogErrorsDecorator:
    def test_success(self):
        from instaharvest.error_handler import log_errors
        @log_errors()
        def good():
            return 'ok'
        assert good() == 'ok'

    def test_error_logged(self):
        from instaharvest.error_handler import log_errors
        @log_errors()
        def bad():
            raise RuntimeError("fail")
        with pytest.raises(RuntimeError):
            bad()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
