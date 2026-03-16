"""
Full coverage tests for instaharvest/core.py — InstaHarvest hub
Target: 50% → 100% (16 missing stmts)
"""

import pytest
from unittest.mock import patch, MagicMock


class TestInstaHarvestInit:
    """Test InstaHarvest.__init__"""

    @patch('instaharvest.core.ProxyManager.from_config')
    @patch('instaharvest.core.SmartLogger.from_config')
    def test_default_config(self, mock_smart_logger, mock_proxy_from_config):
        mock_smart_logger.return_value = MagicMock()
        mock_proxy_from_config.return_value = MagicMock(_proxy_pool=[])
        from instaharvest.core import InstaHarvest
        hub = InstaHarvest()
        assert hub.config is not None
        mock_smart_logger.assert_called_once()
        mock_proxy_from_config.assert_called_once()

    @patch('instaharvest.core.ProxyManager.from_config')
    @patch('instaharvest.core.SmartLogger.from_config')
    def test_custom_config(self, mock_smart_logger, mock_proxy_from_config):
        mock_smart_logger.return_value = MagicMock()
        mock_proxy_from_config.return_value = MagicMock(_proxy_pool=['p1'])
        from instaharvest.core import InstaHarvest
        from instaharvest.config import ScraperConfig
        cfg = ScraperConfig(enable_stealth=False)
        hub = InstaHarvest(config=cfg)
        assert hub.config is cfg
        assert hub.config.enable_stealth is False


class TestInstaHarvestProxyMethods:
    """Test proxy-related methods"""

    def _make_hub(self):
        with patch('instaharvest.core.ProxyManager.from_config') as mock_pm, \
             patch('instaharvest.core.SmartLogger.from_config') as mock_sl:
            mock_sl.return_value = MagicMock()
            pm = MagicMock()
            pm._proxy_pool = []
            mock_pm.return_value = pm
            from instaharvest.core import InstaHarvest
            hub = InstaHarvest()
        return hub

    def test_get_proxy(self):
        hub = self._make_hub()
        hub.proxy_manager.get_for_playwright.return_value = {'server': 'http://proxy:8080'}
        result = hub.get_proxy()
        assert result == {'server': 'http://proxy:8080'}

    def test_get_curl_proxy(self):
        hub = self._make_hub()
        hub.proxy_manager.get_for_curl.return_value = 'http://user:pass@proxy:8080'
        result = hub.get_curl_proxy()
        assert result == 'http://user:pass@proxy:8080'

    def test_check_proxies(self):
        hub = self._make_hub()
        hub.proxy_manager.check_all_proxies.return_value = {'proxy1': {'is_healthy': True}}
        result = hub.check_proxies(verbose=False)
        assert 'proxy1' in result
        hub.proxy_manager.check_all_proxies.assert_called_once_with(verbose=False)

    def test_proxy_stats(self):
        hub = self._make_hub()
        hub.proxy_manager.get_stats.return_value = {'total_proxies': 2}
        result = hub.proxy_stats()
        assert result['total_proxies'] == 2


class TestInstaHarvestConfig:
    """Test config access methods"""

    def _make_hub(self):
        with patch('instaharvest.core.ProxyManager.from_config') as mock_pm, \
             patch('instaharvest.core.SmartLogger.from_config') as mock_sl:
            mock_sl.return_value = MagicMock()
            mock_pm.return_value = MagicMock(_proxy_pool=[])
            from instaharvest.core import InstaHarvest
            hub = InstaHarvest()
        return hub

    def test_update_config_valid_key(self):
        hub = self._make_hub()
        hub.update_config(headless=True)
        assert hub.config.headless is True

    def test_update_config_invalid_key(self):
        hub = self._make_hub()
        hub.update_config(nonexistent_key='value')
        hub.logger.warning.assert_called()

    def test_update_config_multiple(self):
        hub = self._make_hub()
        hub.update_config(headless=False, enable_stealth=False)
        assert hub.config.headless is False
        assert hub.config.enable_stealth is False


class TestInstaHarvestProperties:
    """Test properties"""

    def _make_hub(self):
        with patch('instaharvest.core.ProxyManager.from_config') as mock_pm, \
             patch('instaharvest.core.SmartLogger.from_config') as mock_sl:
            mock_sl.return_value = MagicMock()
            mock_pm.return_value = MagicMock(_proxy_pool=[], has_proxies=False, healthy_count=0)
            from instaharvest.core import InstaHarvest
            hub = InstaHarvest()
        return hub

    def test_has_proxies_false(self):
        hub = self._make_hub()
        hub.proxy_manager.has_proxies = False
        assert hub.has_proxies is False

    def test_has_proxies_true(self):
        hub = self._make_hub()
        hub.proxy_manager.has_proxies = True
        assert hub.has_proxies is True

    def test_healthy_proxy_count(self):
        hub = self._make_hub()
        hub.proxy_manager.healthy_count = 3
        assert hub.healthy_proxy_count == 3

    def test_repr(self):
        hub = self._make_hub()
        hub.proxy_manager.healthy_count = 0
        hub.config.enable_stealth = True
        r = repr(hub)
        assert 'InstaHarvest' in r
        assert 'stealth=True' in r


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
