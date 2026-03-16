"""
Deep Coverage Tests - Part 12
Targets:
  - story_scraper data models: StorySlideInfo, StoryItem, StoryResult (deep fields + to_dict)
  - post_data pure methods: _parse_json_for_urls, _count_visible_videos, _extract_from_dom patterns
  - highlight_scraper: _handle_view_dialog, list_highlights signature
  - orchestrator: scrape_complete_profile full mock chain, _export_results with temp dir
  - post_data: _extract_all_from_json deep
  - parallel_scraper: _extract_reel_tags no tags path, _extract_reel_likes / _extract_reel_timestamp  
"""
import pytest
import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from dataclasses import asdict


def _cfg():
    from instaharvest.config import ScraperConfig
    return ScraperConfig()

def _mock_page():
    p = MagicMock()
    p.url = 'https://instagram.com/'
    p.locator.return_value.count.return_value = 0
    p.locator.return_value.all.return_value = []
    p.locator.return_value.first = MagicMock()
    p.locator.return_value.first.count.return_value = 0
    return p


# ═══════════════════════════════════════════════════════════════
# StorySlideInfo model deep
# ═══════════════════════════════════════════════════════════════

class TestStorySlideInfoModel:
    def test_defaults(self):
        from instaharvest.story_scraper import StorySlideInfo
        s = StorySlideInfo()
        assert s.slide_index == 0
        assert s.timestamp == ''
        assert s.media_type == 'unknown'
        assert s.tagged_accounts == []
        assert s.has_tags is False

    def test_with_tags(self):
        from instaharvest.story_scraper import StorySlideInfo
        s = StorySlideInfo(
            slide_index=2,
            timestamp='2024-01-01T00:00:00Z',
            media_type='image',
            tagged_accounts=['alice', 'bob'],
            has_tags=True
        )
        assert s.has_tags is True
        assert len(s.tagged_accounts) == 2

    def test_to_dict(self):
        from instaharvest.story_scraper import StorySlideInfo
        s = StorySlideInfo(slide_index=3, media_type='video', has_tags=True)
        d = s.to_dict()
        assert d['slide_index'] == 3
        assert d['media_type'] == 'video'
        assert d['has_tags'] is True


class TestStoryItemModel:
    def test_defaults(self):
        from instaharvest.story_scraper import StoryItem
        si = StoryItem()
        assert si.media_url == ''
        assert si.media_type == 'image'
        assert si.tagged_accounts == []

    def test_video_item(self):
        from instaharvest.story_scraper import StoryItem
        si = StoryItem(
            media_url='http://vid.mp4',
            media_type='video',
            width=1080,
            height=1920,
            caption='Test caption',
            tagged_accounts=['user1']
        )
        assert si.media_type == 'video'
        assert si.width == 1080

    def test_to_dict(self):
        from instaharvest.story_scraper import StoryItem
        si = StoryItem(media_url='http://img.jpg', caption='Hello', slide_index=5)
        d = si.to_dict()
        assert d['media_url'] == 'http://img.jpg'
        assert d['caption'] == 'Hello'
        assert d['slide_index'] == 5


class TestStoryResultModel:
    def test_defaults(self):
        from instaharvest.story_scraper import StoryResult
        sr = StoryResult()
        assert sr.username == ''
        assert sr.story_count == 0
        assert sr.has_stories is False
        assert sr.items == []
        assert sr.all_tagged_accounts == []

    def test_with_stories(self):
        from instaharvest.story_scraper import StoryResult, StoryItem, StorySlideInfo
        sr = StoryResult(
            username='alice',
            story_count=3,
            has_stories=True,
            items=[StoryItem(media_url='http://1.jpg'), StoryItem(media_url='http://2.jpg')],
            slides=[StorySlideInfo(has_tags=True), StorySlideInfo(has_tags=False)],
            all_tagged_accounts=['bob', 'charlie']
        )
        assert sr.has_stories is True
        assert sr.story_count == 3
        assert len(sr.items) == 2

    def test_to_dict(self):
        from instaharvest.story_scraper import StoryResult, StoryItem, StorySlideInfo
        sr = StoryResult(
            username='alice',
            story_count=2,
            has_stories=True,
            items=[StoryItem(media_url='http://1.jpg')],
            slides=[StorySlideInfo(slide_index=0, has_tags=True, tagged_accounts=['bob'])],
            all_tagged_accounts=['bob']
        )
        d = sr.to_dict()
        assert d['username'] == 'alice'
        assert d['story_count'] == 2
        assert len(d['items']) == 1
        assert len(d['slides']) == 1
        assert 'bob' in d['all_tagged_accounts']


# ═══════════════════════════════════════════════════════════════
# PostData - _parse_json_for_urls (pure string logic)
# ═══════════════════════════════════════════════════════════════

class TestPostDataParseJsonUrls:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_cdn_url_extraction(self):
        s = self._make()
        content = '{"display_url":"https://scontent.cdninstagram.com/v/photo.jpg?_nc=1"}'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1
        assert any('cdninstagram' in u for u in urls)

    def test_video_url_extraction(self):
        s = self._make()
        content = '{"video_url":"https://scontent.cdninstagram.com/v/video.mp4?_nc=1"}'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1

    def test_no_urls(self):
        s = self._make()
        content = '{"text":"hello world"}'
        urls = s._parse_json_for_urls(content)
        assert len(urls) == 0

    def test_escaped_unicode(self):
        s = self._make()
        content = '{"display_url":"https://scontent.cdninstagram.com/v/photo.jpg?param=1\\u0026other=2"}'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1
        for u in urls:
            assert '\\u0026' not in u  # Should be unescaped

    def test_multiple_urls(self):
        s = self._make()
        content = '''
        {"display_url":"https://scontent.cdninstagram.com/v/img1.jpg", 
         "video_url":"https://scontent.fbcdn.net/v/vid.mp4"}
        '''
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 2

    def test_fbcdn_pattern(self):
        s = self._make()
        content = '{"src":"https://scontent-iad3-1.xx.fbcdn.net/v/photo.webp?_nc=1"}'
        urls = s._parse_json_for_urls(content)
        assert len(urls) >= 1


# ═══════════════════════════════════════════════════════════════
# PostData - _count_visible_videos
# ═══════════════════════════════════════════════════════════════

class TestPostDataCountVisibleVideos:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_no_videos(self):
        s = self._make()
        s.page.locator.return_value.all.return_value = []
        assert s._count_visible_videos() == 0

    def test_one_visible_video(self):
        s = self._make()
        v = MagicMock()
        v.bounding_box.return_value = {'x': 0, 'y': 200, 'width': 500, 'height': 700}
        s.page.locator.return_value.all.return_value = [v]
        assert s._count_visible_videos() == 1

    def test_video_too_small(self):
        s = self._make()
        v = MagicMock()
        v.bounding_box.return_value = {'x': 0, 'y': 200, 'width': 50, 'height': 50}
        s.page.locator.return_value.all.return_value = [v]
        assert s._count_visible_videos() == 0

    def test_video_too_far_down(self):
        s = self._make()
        v = MagicMock()
        v.bounding_box.return_value = {'x': 0, 'y': 3000, 'width': 500, 'height': 700}
        s.page.locator.return_value.all.return_value = [v]
        assert s._count_visible_videos() == 0

    def test_video_no_bounding_box(self):
        s = self._make()
        v = MagicMock()
        v.bounding_box.return_value = None
        s.page.locator.return_value.all.return_value = [v]
        assert s._count_visible_videos() == 0


# ═══════════════════════════════════════════════════════════════
# HighlightsScraper - _handle_view_dialog
# ═══════════════════════════════════════════════════════════════

class TestHighlightHandleViewDialog:
    def _make(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_view_dialog_found(self):
        s = self._make()
        btn = MagicMock()
        btn.count.return_value = 1
        btn.is_visible.return_value = True
        s.page.locator.return_value.first = btn
        s._handle_view_dialog()
        btn.click.assert_called()

    def test_view_dialog_not_found(self):
        s = self._make()
        btn = MagicMock()
        btn.count.return_value = 0
        btn.is_visible.return_value = False
        s.page.locator.return_value.first = btn
        s.page.get_by_role.return_value.count.return_value = 0
        s._handle_view_dialog()  # Should not raise


# ═══════════════════════════════════════════════════════════════
# HighlightsScraper - list_highlights signature
# ═══════════════════════════════════════════════════════════════

class TestHighlightListHighlights:
    def test_list_highlights_exists(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        assert hasattr(s, 'list_highlights')

    def test_scrape_all_exists(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        assert hasattr(s, 'scrape_all')

    def test_list_highlights_signature(self):
        import inspect
        from instaharvest.highlight_scraper import HighlightsScraper
        sig = inspect.signature(HighlightsScraper.list_highlights)
        params = list(sig.parameters.keys())
        assert 'username' in params


# ═══════════════════════════════════════════════════════════════
# Orchestrator - scrape_complete_profile full mock chain
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorCompleteProfile:
    def _make(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        o.page = _mock_page()
        o.browser = MagicMock()
        o.context = MagicMock()
        return o

    def test_scrape_complete_profile_basic(self):
        o = self._make()
        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {'followers': 1000}
        mock_profile.followers = 1000
        mock_profile.engagement_rate = None
        o._scrape_profile_stats = MagicMock(return_value=mock_profile)
        o._collect_post_links = MagicMock(return_value=[])
        result = o.scrape_complete_profile('testuser')
        assert result['username'] == 'testuser'
        assert result['profile'] == {'followers': 1000}

    def test_scrape_complete_profile_with_posts(self):
        o = self._make()
        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {'followers': 1000}
        mock_profile.followers = 1000
        mock_profile.engagement_rate = None
        o._scrape_profile_stats = MagicMock(return_value=mock_profile)
        o._collect_post_links = MagicMock(return_value=[{'url': 'http://p/1/', 'type': 'Post'}])

        mock_post = MagicMock()
        mock_post.likes = '500'
        mock_post.to_dict.return_value = {'url': 'http://p/1/', 'likes': '500'}
        o._scrape_posts_data = MagicMock(return_value=[mock_post])

        result = o.scrape_complete_profile('testuser', scrape_posts=True)
        assert len(result['posts_data']) == 1

    def test_export_results_to_json(self):
        o = self._make()
        td = tempfile.mkdtemp()
        o.config.base_output_dir = td
        results = {
            'username': 'testuser',
            'profile': {'followers': 1000},
            'post_links': [{'url': 'http://x'}],
            'posts_data': []
        }
        o._export_results(results)
        # Should write a JSON file
        files = [f for f in os.listdir(td) if f.endswith('.json')]
        assert len(files) >= 1


# ═══════════════════════════════════════════════════════════════
# parallel_scraper reel helpers deep
# ═══════════════════════════════════════════════════════════════

class TestParallelReelHelpers:
    def test_extract_reel_likes_no_element(self):
        from instaharvest.parallel_scraper import _extract_reel_likes
        from bs4 import BeautifulSoup
        page = _mock_page()
        page.locator.return_value.first.inner_text.side_effect = Exception("timeout")
        soup = BeautifulSoup('<html></html>', 'html.parser')
        result = _extract_reel_likes(soup, page, 1, _cfg())
        assert result == 0

    def test_extract_reel_timestamp_no_element(self):
        from instaharvest.parallel_scraper import _extract_reel_timestamp
        from bs4 import BeautifulSoup
        page = _mock_page()
        page.locator.return_value.first.get_attribute.side_effect = Exception("timeout")
        soup = BeautifulSoup('<html></html>', 'html.parser')
        result = _extract_reel_timestamp(soup, page, 1, _cfg())
        assert result == 'N/A'

    def test_extract_reel_tags_no_button(self):
        from instaharvest.parallel_scraper import _extract_reel_tags
        from bs4 import BeautifulSoup
        page = _mock_page()
        page.locator.return_value.first.click.side_effect = Exception("not found")
        soup = BeautifulSoup('<html></html>', 'html.parser')
        result = _extract_reel_tags(soup, page, 'http://reel/', 1, _cfg())
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════
# PostData - _extract_all_from_json deep
# ═══════════════════════════════════════════════════════════════

class TestPostDataExtractAllFromJson:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_has_extract_all_from_json(self):
        s = self._make()
        assert hasattr(s, '_extract_all_from_json')

    def test_extract_no_scripts(self):
        s = self._make()
        s.page.locator.return_value.all.return_value = []
        result = s._extract_all_from_json()
        assert result is None or isinstance(result, dict)
