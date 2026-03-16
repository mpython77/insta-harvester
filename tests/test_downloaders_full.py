"""
Tests for MediaDownloader, BatchDownloader, CaptchaSolver — correct APIs
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from instaharvest.config import ScraperConfig


class TestMediaDownloaderInit:
    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestUA')
    @patch('instaharvest.network_client.requests.Session')
    def test_init_default(self, mock_sess, mock_ua):
        from instaharvest.downloader import MediaDownloader
        with tempfile.TemporaryDirectory() as d:
            cfg = ScraperConfig()
            cfg.base_output_dir = d
            dl = MediaDownloader(config=cfg)
            assert dl.output_dir.exists()

    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestUA')
    @patch('instaharvest.network_client.requests.Session')
    def test_init_custom_dir(self, mock_sess, mock_ua):
        from instaharvest.downloader import MediaDownloader
        with tempfile.TemporaryDirectory() as d:
            dl = MediaDownloader(output_dir=d)
            assert str(dl.output_dir) == d


class TestDownloadWithYtdlp:
    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestUA')
    @patch('instaharvest.network_client.requests.Session')
    def test_ytdlp_exception(self, mock_sess, mock_ua):
        from instaharvest.downloader import MediaDownloader
        with tempfile.TemporaryDirectory() as d:
            dl = MediaDownloader(output_dir=d)
            mock_ytdlp = MagicMock()
            mock_ytdlp.YoutubeDL.side_effect = Exception("yt-dlp error")
            with patch.dict('sys.modules', {'yt_dlp': mock_ytdlp}):
                result = dl._download_with_ytdlp('https://ig.com/p/ABC/', Path(d), 'ABC', '2025-01-01')
            assert result is None


class TestDownloadPost:
    @patch('instaharvest.network_client.SecurityManager.get_random_user_agent', return_value='TestUA')
    @patch('instaharvest.network_client.requests.Session')
    @patch('time.sleep')
    def test_no_media_urls(self, mock_sleep, mock_sess, mock_ua):
        from instaharvest.downloader import MediaDownloader
        from instaharvest.post_data import PostData
        with tempfile.TemporaryDirectory() as d:
            dl = MediaDownloader(output_dir=d)
            post = PostData(
                url='https://instagram.com/p/ABC/',
                tagged_accounts=[],
                likes='0',
                timestamp='2025-01-01'
            )
            post.media_urls = []
            result = dl.download_post(post)
            assert result == []


class TestBatchDownloaderImport:
    def test_import(self):
        from instaharvest.batch_downloader import BatchDownloader, DownloadTask, BatchResult
        assert BatchDownloader is not None

    def test_batch_result_defaults(self):
        from instaharvest.batch_downloader import BatchResult
        r = BatchResult()
        assert r.total == 0

    def test_download_task_creation(self):
        from instaharvest.batch_downloader import DownloadTask
        task = DownloadTask(url='https://ig.com/p/ABC/', save_path=Path('/tmp/test'))
        assert task.url == 'https://ig.com/p/ABC/'


class TestCaptchaSolverImport:
    def test_import(self):
        from instaharvest.captcha_solver import CaptchaSolver
        assert CaptchaSolver is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
