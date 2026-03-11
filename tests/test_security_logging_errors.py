"""
Unit Tests — SecurityManager, SmartLogger, ErrorHandler, ErrorStats, ErrorContext
Covers pure logic only (no browser/network needed)
"""

import sys, os, time, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch
from instaharvest.security import SecurityManager
from instaharvest.logging_config import SmartLogger, get_logger, set_default_logger
from instaharvest.error_handler import (
    ErrorHandler, ErrorContext, ErrorStats, retry_on_error, log_errors
)
from instaharvest.config import ScraperConfig


# ═══════════════════════════════════════════════════════════
# SecurityManager
# ═══════════════════════════════════════════════════════════

class TestSecurityManagerUserAgent:
    def test_default_returns_string(self):
        ua = SecurityManager.get_random_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 20

    def test_custom_list(self):
        custom = ['MyBot/1.0', 'MyBot/2.0']
        ua = SecurityManager.get_random_user_agent(custom)
        assert ua in custom

    def test_user_agents_list_not_empty(self):
        assert len(SecurityManager.USER_AGENTS) >= 5

    def test_all_agents_valid(self):
        for ua in SecurityManager.USER_AGENTS:
            assert 'Mozilla' in ua or 'AppleWebKit' in ua


class TestSecurityManagerFormatProxy:
    def test_full_url(self):
        result = SecurityManager.format_proxy('http://user:pass@1.2.3.4:8080')
        assert result['server'] == 'http://1.2.3.4:8080'
        assert result['username'] == 'user'
        assert result['password'] == 'pass'

    def test_no_auth(self):
        result = SecurityManager.format_proxy('http://1.2.3.4:8080')
        assert result['server'] == 'http://1.2.3.4:8080'
        assert 'username' not in result

    def test_no_protocol(self):
        result = SecurityManager.format_proxy('1.2.3.4:8080')
        assert 'http' in result['server']
        assert '8080' in result['server']

    def test_empty_string(self):
        result = SecurityManager.format_proxy('')
        assert result is None

    def test_none(self):
        result = SecurityManager.format_proxy(None)
        assert result is None

    def test_dict_passthrough(self):
        d = {'server': 'http://1.2.3.4:8080'}
        result = SecurityManager.format_proxy(d)
        assert result is d

    def test_socks5(self):
        result = SecurityManager.format_proxy('socks5://user:pass@5.6.7.8:1080')
        assert result['server'] == 'socks5://5.6.7.8:1080'
        assert result['username'] == 'user'


class TestSecurityManagerGetRandomProxy:
    def test_empty_list(self):
        result = SecurityManager.get_random_proxy([])
        assert result is None

    def test_single_proxy(self):
        result = SecurityManager.get_random_proxy(['http://1.2.3.4:8080'])
        assert result is not None
        assert 'server' in result

    def test_picks_from_list(self):
        proxies = [f'http://1.2.3.{i}:8080' for i in range(5)]
        results = set()
        for _ in range(20):
            r = SecurityManager.get_random_proxy(proxies)
            results.add(r['server'])
        assert len(results) >= 2  # Should pick multiple different proxies


# ═══════════════════════════════════════════════════════════
# SmartLogger
# ═══════════════════════════════════════════════════════════

class TestSmartLoggerFormatMessage:
    def test_basic(self):
        logger = SmartLogger('test', log_to_console=False)
        msg = logger._format_message('success', 'Profile scraped')
        assert '[OK]' in msg
        assert 'Profile scraped' in msg

    def test_with_context(self):
        logger = SmartLogger('test', log_to_console=False)
        msg = logger._format_message('info', 'Loaded', count=5)
        assert 'count=5' in msg

    def test_no_emoji(self):
        logger = SmartLogger('test', show_emoji=False, log_to_console=False)
        msg = logger._format_message('error', 'Failed')
        assert '[ERROR]' not in msg
        assert 'Failed' in msg

    def test_unknown_emoji_key(self):
        logger = SmartLogger('test', log_to_console=False)
        msg = logger._format_message('custom_key', 'Test')
        assert 'Test' in msg


class TestSmartLoggerMethods:
    def test_success(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.success('Done')  # Should not raise

    def test_error(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.error('Oops')

    def test_warning(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.warning('Careful')

    def test_info(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.info('FYI')

    def test_debug(self):
        logger = SmartLogger('test', level='DEBUG', log_to_console=False)
        logger.debug('Details')

    def test_proxy(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.proxy('Connected', ip='1.2.3.4')

    def test_browser(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.browser('Launched')

    def test_network(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.network('Request sent')

    def test_progress(self):
        logger = SmartLogger('test', log_to_console=False)
        logger.progress('Loading', step=3)


class TestSmartLoggerOperation:
    def test_success_context(self):
        logger = SmartLogger('test', log_to_console=False)
        with logger.operation('Test op'):
            pass  # Should complete successfully

    def test_error_context(self):
        logger = SmartLogger('test', log_to_console=False)
        with pytest.raises(ValueError):
            with logger.operation('Failing op'):
                raise ValueError('test error')


class TestSmartLoggerTimed:
    def test_timed_decorator(self):
        logger = SmartLogger('test', log_to_console=False)

        @logger.timed
        def my_func():
            return 42

        assert my_func() == 42


class TestSmartLoggerFromConfig:
    def test_from_config(self):
        config = ScraperConfig(log_level='DEBUG')
        logger = SmartLogger.from_config(config, name='TestConfig')
        assert logger.name == 'TestConfig'


class TestSmartLoggerModuleLevel:
    def test_get_logger(self):
        l = get_logger('TestModule')
        assert isinstance(l, SmartLogger)

    def test_get_logger_cached(self):
        l1 = get_logger('CachedTest')
        l2 = get_logger('CachedTest')
        assert l1 is l2

    def test_set_default_logger(self):
        custom = SmartLogger('Custom', log_to_console=False)
        set_default_logger('CustomSlot', custom)
        assert get_logger('CustomSlot') is custom


# ═══════════════════════════════════════════════════════════
# ErrorContext & ErrorStats
# ═══════════════════════════════════════════════════════════

class TestErrorContext:
    def test_creation(self):
        ctx = ErrorContext(
            timestamp='2025-03-10 12:00:00',
            function_name='scrape_profile',
            url='https://instagram.com/test/',
            error_type='TimeoutError',
            error_message='Page load timeout',
        )
        assert ctx.function_name == 'scrape_profile'
        assert ctx.retry_count == 0
        assert ctx.recovery_action is None


class TestErrorStats:
    def test_initial(self):
        stats = ErrorStats()
        assert stats.total_errors == 0
        assert stats.get_recovery_rate() == 100.0

    def test_add_recovered(self):
        stats = ErrorStats()
        ctx = ErrorContext(timestamp='now', function_name='test')
        ctx.error_type = 'ValueError'
        stats.add_error(ctx, recovered=True)
        assert stats.total_errors == 1
        assert stats.recovered_errors == 1
        assert stats.get_recovery_rate() == 100.0

    def test_add_failed(self):
        stats = ErrorStats()
        ctx = ErrorContext(timestamp='now', function_name='test')
        ctx.error_type = 'TimeoutError'
        stats.add_error(ctx, recovered=False)
        assert stats.failed_errors == 1
        assert stats.get_recovery_rate() == 0.0

    def test_mixed_rate(self):
        stats = ErrorStats()
        for i in range(3):
            ctx = ErrorContext(timestamp='now', function_name=f'func_{i}')
            ctx.error_type = 'Error'
            stats.add_error(ctx, recovered=(i < 2))
        assert stats.total_errors == 3
        assert stats.recovered_errors == 2
        assert stats.failed_errors == 1
        assert abs(stats.get_recovery_rate() - 66.7) < 0.1

    def test_error_types_tracked(self):
        stats = ErrorStats()
        for t in ['ValueError', 'ValueError', 'TimeoutError']:
            ctx = ErrorContext(timestamp='now', function_name='test')
            ctx.error_type = t
            stats.add_error(ctx, recovered=True)
        assert stats.error_types['ValueError'] == 2
        assert stats.error_types['TimeoutError'] == 1

    def test_get_report(self):
        stats = ErrorStats()
        ctx = ErrorContext(timestamp='2025-01-01', function_name='test_fn')
        ctx.error_type = 'TestError'
        ctx.error_message = 'Something went wrong'
        stats.add_error(ctx, recovered=True)
        report = stats.get_report()
        assert 'ERROR STATISTICS REPORT' in report
        assert 'TestError: 1' in report
        assert 'Recovery Rate: 100.0%' in report


# ═══════════════════════════════════════════════════════════
# ErrorHandler
# ═══════════════════════════════════════════════════════════

class TestErrorHandlerSafeExtract:
    def test_success(self):
        handler = ErrorHandler()
        result = handler.safe_extract(lambda: 42, 'test_element')
        assert result == 42

    def test_failure_returns_default(self):
        handler = ErrorHandler()
        result = handler.safe_extract(
            lambda: 1 / 0,
            'division',
            default='N/A',
        )
        assert result == 'N/A'
        assert handler.stats.total_errors == 1

    def test_custom_default(self):
        handler = ErrorHandler()
        result = handler.safe_extract(lambda: int('abc'), 'parse', default=-1)
        assert result == -1


class TestErrorHandlerWithRecovery:
    def test_primary_success(self):
        handler = ErrorHandler()
        result = handler.with_recovery(lambda: 'primary', lambda: 'fallback', 'test')
        assert result == 'primary'

    def test_fallback_used(self):
        handler = ErrorHandler()
        result = handler.with_recovery(
            lambda: 1 / 0,
            lambda: 'recovered',
            'test',
        )
        assert result == 'recovered'
        assert handler.stats.recovered_errors == 1

    def test_both_fail(self):
        handler = ErrorHandler()
        result = handler.with_recovery(
            lambda: 1 / 0,
            lambda: int('abc'),
            'test',
            default='default_val',
        )
        assert result == 'default_val'
        assert handler.stats.failed_errors == 1

    def test_no_fallback(self):
        handler = ErrorHandler()
        result = handler.with_recovery(
            lambda: int('nope'),
            element_name='no_fallback',
            default='safe',
        )
        assert result == 'safe'


class TestErrorHandlerRetry:
    def test_success_first_try(self):
        handler = ErrorHandler()
        result = handler.retry_with_backoff(lambda: 99, max_retries=2, initial_delay=0.01)
        assert result == 99

    def test_retries_then_succeeds(self):
        handler = ErrorHandler()
        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError('not yet')
            return 'ok'

        result = handler.retry_with_backoff(
            flaky, max_retries=3, initial_delay=0.01, backoff_factor=1.0
        )
        assert result == 'ok'
        assert call_count[0] == 3

    def test_all_fail(self):
        handler = ErrorHandler()
        with pytest.raises(ValueError, match='always'):
            handler.retry_with_backoff(
                lambda: (_ for _ in ()).throw(ValueError('always')),
                max_retries=1,
                initial_delay=0.01,
            )


# ═══════════════════════════════════════════════════════════
# Decorators
# ═══════════════════════════════════════════════════════════

class TestRetryOnError:
    def test_success(self):
        @retry_on_error(max_retries=2, delay=0.01)
        def good():
            return 42

        assert good() == 42

    def test_retry_then_success(self):
        counter = [0]

        @retry_on_error(max_retries=3, delay=0.01)
        def flaky():
            counter[0] += 1
            if counter[0] < 3:
                raise RuntimeError('retry')
            return 'done'

        assert flaky() == 'done'

    def test_all_retries_exhausted(self):
        @retry_on_error(max_retries=1, delay=0.01)
        def always_fails():
            raise RuntimeError('permanent')

        with pytest.raises(RuntimeError, match='permanent'):
            always_fails()


class TestLogErrors:
    def test_success(self):
        @log_errors()
        def good():
            return 10

        assert good() == 10

    def test_error_logged_and_raised(self):
        @log_errors()
        def bad():
            raise TypeError('type error')

        with pytest.raises(TypeError):
            bad()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
