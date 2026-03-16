"""
Full coverage tests for instaharvest/network_client.py — NetworkClient
Target: 26% → 100% (32 missing stmts)
"""

import pytest
from unittest.mock import patch, MagicMock


class TestNetworkClientInit:
    """Test NetworkClient initialization"""

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent/1.0')
    @patch('instaharvest.network_client.requests.Session')
    def test_init_no_proxy(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        client = NetworkClient()
        assert client.proxy is None
        mock_session_cls.assert_called_once_with(impersonate="chrome120")

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent/1.0')
    @patch('instaharvest.network_client.requests.Session')
    def test_init_with_proxy(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        client = NetworkClient(proxy='http://proxy:8080')
        assert client.proxy == 'http://proxy:8080'
        assert mock_session.proxies == {"http": "http://proxy:8080", "https": "http://proxy:8080"}


class TestNetworkClientHeaders:
    """Test _setup_headers"""

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='Custom/UA')
    @patch('instaharvest.network_client.requests.Session')
    def test_headers_set(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        # headers should be set with User-Agent from SecurityManager
        assert 'User-Agent' in mock_session.headers
        assert mock_session.headers['User-Agent'] == 'Custom/UA'


class TestSetCookies:
    """Test set_cookies method"""

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_set_cookies(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        cookies = [
            {'name': 'sessionid', 'value': 'abc123', 'domain': '.instagram.com', 'path': '/'},
            {'name': 'csrftoken', 'value': 'xyz789', 'domain': '.instagram.com', 'path': '/'},
        ]
        client.set_cookies(cookies)
        assert mock_session.cookies.set.call_count == 2

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_set_empty_cookies(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        client.set_cookies([])
        mock_session.cookies.set.assert_not_called()


class TestGetRequest:
    """Test get method"""

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_get_success(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_response = MagicMock(status_code=200)
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        result = client.get('https://example.com')
        assert result == mock_response

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_get_failure_raises(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection refused")
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        with pytest.raises(Exception, match="Connection refused"):
            client.get('https://example.com')


class TestPostRequest:
    """Test post method"""

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_post_with_json(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_response = MagicMock(status_code=200)
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        result = client.post('https://api.example.com', json={'key': 'val'})
        assert result == mock_response

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_post_with_data(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_response = MagicMock(status_code=200)
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        result = client.post('https://api.example.com', data='raw_data')
        assert result == mock_response

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_post_failure_raises(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session.post.side_effect = Exception("Server error")
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        with pytest.raises(Exception, match="Server error"):
            client.post('https://api.example.com')


class TestDownloadMedia:
    """Test download_media method"""

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    @patch('builtins.open', create=True)
    def test_download_success(self, mock_open, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        result = client.download_media('https://cdn.example.com/img.jpg', '/tmp/img.jpg')
        assert result is True

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestAgent')
    @patch('instaharvest.network_client.requests.Session')
    def test_download_failure(self, mock_session_cls, mock_ua):
        from instaharvest.network_client import NetworkClient
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Download error")
        mock_session_cls.return_value = mock_session
        client = NetworkClient()
        result = client.download_media('https://cdn.example.com/img.jpg', '/tmp/img.jpg')
        assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
