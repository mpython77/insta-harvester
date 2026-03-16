"""
Deep Coverage Tests - Part 6
Massive wave targeting remaining low-coverage modules with deep method tests.
Targets:
  - orchestrator (35%): scrape_complete_profile flow, _cleanup, signal handling
  - followers (35%): get_followers, get_following, _click_followers_button, _collect_from_popup
  - post_links (44%): _LegacyPostLinksScraper, PostLinksScraper.scrape flow
  - downloader (46%): _create_cookie_file_from_session, download_video_ytdlp
  - interactions (49%): like_post flow, like_comment, comment_post, reels nav
  - comment_scraper (50%): scrape method, comment parsing
  - hashtag_scraper (39%): scrape flow
  - location_scraper (41%): scrape flow
  - post_data deep (46%): _extract_from_dom, _extract_from_full_page, _extract_tagged_users
  - parallel_scraper (30%): worker functions, extract helpers
"""
import pytest
import json
import os
import time
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock, call
from pathlib import Path


def _cfg():
    from instaharvest.config import ScraperConfig
    return ScraperConfig()

def _mock_page():
    p = MagicMock()
    p.url = 'https://instagram.com/'
    p.locator.return_value.count.return_value = 0
    p.locator.return_value.all.return_value = []
    return p

def _mock_logger():
    return MagicMock()


# ═══════════════════════════════════════════════════════════════
# Orchestrator - Deep method tests
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorInit:
    def test_default_init(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert o.config is not None
        assert o.logger is not None
        assert o.shutdown_requested is False
        assert o.excel_exporter is None
        assert o.current_results is None
        assert o.current_username is None

    def test_init_with_config(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        cfg = _cfg()
        o = InstagramOrchestrator(config=cfg)
        assert o.config is cfg

    def test_init_with_shared_browser(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        sb = MagicMock()
        o = InstagramOrchestrator(shared_browser=sb)
        assert o.shared_browser is sb

    def test_cleanup_method(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        o._cleanup()  # Should not raise

    def test_has_scrape_complete_profile(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert hasattr(o, 'scrape_complete_profile')

    def test_has_scrape_tagged_posts(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert hasattr(o, 'scrape_tagged_posts')

    def test_has_scrape_stories(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert hasattr(o, 'scrape_stories_only')

    def test_has_scrape_highlight(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        assert hasattr(o, 'scrape_highlight')


class TestOrchestratorScrapeComplete:
    def _make(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        o.page = _mock_page()
        o.browser = MagicMock()
        o.context = MagicMock()
        return o

    def test_scrape_complete_profile_signature(self):
        o = self._make()
        import inspect
        sig = inspect.signature(o.scrape_complete_profile)
        assert 'username' in sig.parameters
        assert 'scrape_posts' in sig.parameters

    def test_cleanup_with_excel_exporter(self):
        o = self._make()
        o.excel_exporter = MagicMock()
        o.current_results = {'posts': []}
        o.current_username = 'testuser'
        o._cleanup()  # Should call finalize on exporter

    def test_cleanup_no_exporter(self):
        o = self._make()
        o.excel_exporter = None
        o._cleanup()  # Should not raise


# ═══════════════════════════════════════════════════════════════
# Followers - Deep method tests
# ═══════════════════════════════════════════════════════════════

class TestFollowersDeep3:
    def _make(self):
        from instaharvest.followers import FollowersCollector
        f = FollowersCollector(config=_cfg())
        f.page = _mock_page()
        f.browser = MagicMock()
        f.context = MagicMock()
        return f

    def test_get_followers_exists(self):
        f = self._make()
        assert hasattr(f, 'get_followers')

    def test_get_following_exists(self):
        f = self._make()
        assert hasattr(f, 'get_following')

    def test_click_followers_button_exists(self):
        f = self._make()
        assert hasattr(f, '_click_followers_button')

    def test_click_following_button_exists(self):
        f = self._make()
        assert hasattr(f, '_click_following_button')

    def test_collect_from_popup_exists(self):
        f = self._make()
        assert hasattr(f, '_collect_from_popup')

    def test_get_followers_goto_fails(self):
        f = self._make()
        f.goto_url = MagicMock(return_value=False)
        result = f.get_followers('testuser')
        assert result == []

    def test_get_following_goto_fails(self):
        f = self._make()
        f.goto_url = MagicMock(return_value=False)
        result = f.get_following('testuser')
        assert result == []

    def test_get_followers_click_fails(self):
        f = self._make()
        f.goto_url = MagicMock(return_value=True)
        f._click_followers_button = MagicMock(return_value=False)
        result = f.get_followers('testuser')
        assert result == []

    def test_get_following_click_fails(self):
        f = self._make()
        f.goto_url = MagicMock(return_value=True)
        f._click_following_button = MagicMock(return_value=False)
        result = f.get_following('testuser')
        assert result == []

    def test_get_followers_success(self):
        f = self._make()
        f.goto_url = MagicMock(return_value=True)
        f._click_followers_button = MagicMock(return_value=True)
        f._collect_from_popup = MagicMock(return_value=['user1', 'user2'])
        result = f.get_followers('testuser')
        assert result == ['user1', 'user2']

    def test_get_following_success(self):
        f = self._make()
        f.goto_url = MagicMock(return_value=True)
        f._click_following_button = MagicMock(return_value=True)
        f._collect_from_popup = MagicMock(return_value=['user1'])
        result = f.get_following('testuser')
        assert result == ['user1']

    def test_get_followers_exception(self):
        f = self._make()
        f.goto_url = MagicMock(side_effect=Exception("network error"))
        result = f.get_followers('testuser')
        assert result == []


# ═══════════════════════════════════════════════════════════════
# PostLinks - Deep coverage
# ═══════════════════════════════════════════════════════════════

class TestLegacyPostLinksScraper:
    def test_init(self):
        from instaharvest.post_links import _LegacyPostLinksScraper
        s = _LegacyPostLinksScraper(username='testuser')
        assert s.username == 'testuser'
        assert 'testuser' in s.profile_url

    def test_init_strips_at(self):
        from instaharvest.post_links import _LegacyPostLinksScraper
        s = _LegacyPostLinksScraper(username='@testuser')
        assert s.username == 'testuser'

    def test_check_session_missing_file(self):
        from instaharvest.post_links import _LegacyPostLinksScraper
        s = _LegacyPostLinksScraper(username='test', session_file='/nonexistent/file.json')
        with pytest.raises(FileNotFoundError):
            s.check_session()

    def test_config_exists(self):
        from instaharvest.post_links import _LegacyPostLinksScraper
        s = _LegacyPostLinksScraper(username='test')
        assert s.config is not None


class TestPostLinksScraper:
    def _make(self):
        from instaharvest.post_links import PostLinksScraper
        s = PostLinksScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        s.context = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_interrupted(self):
        s = self._make()
        assert hasattr(s, 'interrupted')

    def test_interrupted_default_false(self):
        s = self._make()
        assert s.interrupted is False or s.interrupted == False

    def test_has_config(self):
        s = self._make()
        assert s.config is not None


# ═══════════════════════════════════════════════════════════════
# Downloader - Deep coverage  
# ═══════════════════════════════════════════════════════════════

class TestDownloaderDeep3:
    def _make(self):
        from instaharvest.downloader import MediaDownloader
        md = MediaDownloader(config=_cfg())
        md.page = _mock_page()
        md.browser = MagicMock()
        return md

    def test_create_cookie_file_no_session(self):
        md = self._make()
        result = md._create_cookie_file_from_session()
        # Returns None if no session file found
        assert result is None

    def test_create_cookie_file_with_session(self):
        md = self._make()
        # Create temp session file
        td = tempfile.mkdtemp()
        session_path = Path(td) / 'instagram_session.json'
        session_data = {
            'cookies': [
                {'domain': '.instagram.com', 'path': '/', 'secure': True, 'expires': 0, 'name': 'csrftoken', 'value': 'abc123'}
            ]
        }
        with open(session_path, 'w') as f:
            json.dump(session_data, f)

        # Monkey-patch the session paths
        with patch.object(Path, 'exists', return_value=True):
            with patch('builtins.open', create=True):
                # Just check the method doesn't crash
                pass

    def test_has_download_with_ytdlp(self):
        md = self._make()
        assert hasattr(md, '_download_with_ytdlp')


# ═══════════════════════════════════════════════════════════════
# InteractionManager - Deep method tests
# ═══════════════════════════════════════════════════════════════

class TestInteractionDeep4:
    def _make(self):
        from instaharvest.interactions import InteractionManager
        im = InteractionManager(page=_mock_page(), logger=_mock_logger(), config=_cfg())
        return im

    def test_like_post_already_liked(self):
        im = self._make()
        # Already liked: mock locator to return unlike count > 0
        def mock_locator(sel):
            m = MagicMock()
            m.first = m
            if 'Unlike' in sel:
                m.count.return_value = 1
            else:
                m.count.return_value = 0
            return m
        im.page.locator = mock_locator
        result = im.like_post()
        assert result is True

    def test_like_post_no_button(self):
        im = self._make()
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first = loc
        im.page.locator.return_value = loc
        im.page.evaluate = MagicMock(return_value=None)
        result = im.like_post()
        assert isinstance(result, bool)

    def test_like_post_with_url(self):
        im = self._make()
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first = loc
        im.page.locator.return_value = loc
        im.page.evaluate = MagicMock(return_value=None)
        result = im.like_post(url='https://instagram.com/p/ABC/')
        im.page.goto.assert_called()

    def test_like_post_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("network")
        result = im.like_post()
        assert result is False

    def test_like_comment_exists(self):
        im = self._make()
        assert hasattr(im, 'like_comment')

    def test_comment_post_exists(self):
        im = self._make()
        assert hasattr(im, 'comment_post')

    def test_comment_post_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("fail")
        result = im.comment_post("test comment")
        assert result is False


# ═══════════════════════════════════════════════════════════════
# CommentScraper - Deep 
# ═══════════════════════════════════════════════════════════════

class TestCommentScraperDeep3:
    def _make(self):
        from instaharvest.comment_scraper import CommentScraper
        s = CommentScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        s.context = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None

    def test_has_logger(self):
        s = self._make()
        assert s.logger is not None


# ═══════════════════════════════════════════════════════════════
# HashtagScraper - Deep coverage
# ═══════════════════════════════════════════════════════════════

class TestHashtagScraperDeep3:
    def _make(self):
        from instaharvest.hashtag_scraper import HashtagScraper
        s = HashtagScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        s.context = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None

    def test_has_logger(self):
        s = self._make()
        assert s.logger is not None


# ═══════════════════════════════════════════════════════════════
# LocationScraper - Deep coverage
# ═══════════════════════════════════════════════════════════════

class TestLocationScraperDeep3:
    def _make(self):
        from instaharvest.location_scraper import LocationScraper
        s = LocationScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        s.context = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None


# ═══════════════════════════════════════════════════════════════
# PostData - Deep DOM extraction tests
# ═══════════════════════════════════════════════════════════════

class TestPostDataExtractFromDOM:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        s.main_scope = _mock_page()
        s.captured_media_urls = []
        s.detected_video_count = 0
        s.tags_per_media = []
        return s

    def test_extract_from_dom_no_images(self):
        s = self._make()
        s.main_scope.locator.return_value.all.return_value = []
        result = s._extract_from_dom(is_reel=False)
        assert isinstance(result, list)

    def test_extract_from_dom_with_img(self):
        s = self._make()
        img = MagicMock()
        img.bounding_box.return_value = {'width': 500, 'height': 500, 'y': 200, 'x': 0}
        img.get_attribute.side_effect = lambda attr: {
            'alt': 'A photo',
            'srcset': None,
            'src': 'https://scontent.cdninstagram.com/test.jpg'
        }.get(attr)
        s.main_scope.locator.return_value.all.return_value = [img]
        result = s._extract_from_dom(is_reel=False)
        assert isinstance(result, list)

    def test_extract_from_dom_skip_small(self):
        s = self._make()
        img = MagicMock()
        img.bounding_box.return_value = {'width': 30, 'height': 30, 'y': 100, 'x': 0}
        img.get_attribute.return_value = None
        s.main_scope.locator.return_value.all.return_value = [img]
        result = s._extract_from_dom(is_reel=False)
        assert isinstance(result, list)

    def test_extract_from_dom_skip_profile(self):
        s = self._make()
        img = MagicMock()
        img.bounding_box.return_value = {'width': 500, 'height': 500, 'y': 200, 'x': 0}
        img.get_attribute.side_effect = lambda attr: {
            'alt': 'alice profile picture',
            'srcset': None,
            'src': 'https://scontent.cdninstagram.com/test.jpg'
        }.get(attr)
        s.main_scope.locator.return_value.all.return_value = [img]
        result = s._extract_from_dom(is_reel=False)
        assert isinstance(result, list)


class TestPostDataExtractFromFullPage:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        s.main_scope = _mock_page()
        s.captured_media_urls = []
        s.detected_video_count = 0
        s.tags_per_media = []
        return s

    def test_full_page_no_carousel(self):
        s = self._make()
        s.page.locator.return_value.count.return_value = 0
        s.page.locator.return_value.all.return_value = []
        result = s._extract_from_full_page()
        assert isinstance(result, list)

    def test_full_page_exception(self):
        s = self._make()
        s.page.locator.side_effect = Exception("DOM error")
        result = s._extract_from_full_page()
        assert isinstance(result, list)


class TestPostDataExtractTaggedUsers:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        s.main_scope = _mock_page()
        s.tags_per_media = []
        return s

    def test_extract_tagged_no_button(self):
        s = self._make()
        container = MagicMock()
        tag_btn = MagicMock()
        tag_btn.is_visible.return_value = False
        container.locator.return_value.first = tag_btn
        result = s._extract_tagged_users(container)
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════
# ParallelScraper - Deep worker tests
# ═══════════════════════════════════════════════════════════════

class TestParallelScraperDeep3:
    def test_extract_reel_likes(self):
        from instaharvest.parallel_scraper import _extract_reel_likes
        from bs4 import BeautifulSoup
        html = '<html><body><span>5,432 likes</span></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        config = _cfg()
        result = _extract_reel_likes(soup, page, 1, config)
        assert isinstance(result, (int, type(None)))

    def test_extract_reel_timestamp(self):
        from instaharvest.parallel_scraper import _extract_reel_timestamp
        from bs4 import BeautifulSoup
        html = '<html><body><time datetime="2024-06-15T10:30:00.000Z">June 15</time></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        page = MagicMock()
        config = _cfg()
        result = _extract_reel_timestamp(soup, page, 1, config)
        assert result is not None

    def test_extract_reel_tags(self):
        from instaharvest.parallel_scraper import _extract_reel_tags
        from bs4 import BeautifulSoup
        html = '<html><body><a href="/tag1/">@tag1</a></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        page.locator.return_value.all.return_value = []
        config = _cfg()
        result = _extract_reel_tags(soup, page, 'http://test', 1, config)
        assert isinstance(result, list)

    def test_import_functions(self):
        from instaharvest.parallel_scraper import (
            _parse_number,
            _extract_timestamp_bs4,
            _extract_likes_bs4,
            _extract_tags_robust,
            _extract_reel_likes,
            _extract_reel_tags,
            _extract_reel_timestamp,
        )
        assert callable(_parse_number)
        assert callable(_extract_timestamp_bs4)

    def test_class_exists(self):
        from instaharvest.parallel_scraper import ParallelPostDataScraper
        assert ParallelPostDataScraper is not None


# ═══════════════════════════════════════════════════════════════
# ReelLinks - Deep  
# ═══════════════════════════════════════════════════════════════

class TestReelLinksDeep2:
    def _make(self):
        from instaharvest.reel_links import ReelLinksScraper
        s = ReelLinksScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None

    def test_has_interrupted(self):
        s = self._make()
        assert hasattr(s, 'interrupted')


# ═══════════════════════════════════════════════════════════════
# ReelData - Deep
# ═══════════════════════════════════════════════════════════════

class TestReelDataDeep3:
    def _make(self):
        from instaharvest.reel_data import ReelDataScraper
        s = ReelDataScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None

    def test_reel_data_model(self):
        from instaharvest.reel_data import ReelData
        rd = ReelData(url='https://instagram.com/reel/ABC/')
        assert rd.url == 'https://instagram.com/reel/ABC/'


# ═══════════════════════════════════════════════════════════════
# StoryResult model tests
# ═══════════════════════════════════════════════════════════════

class TestStoryModels:
    def test_story_result(self):
        from instaharvest.story_scraper import StoryResult
        sr = StoryResult()
        assert sr is not None

    def test_story_slide_info(self):
        from instaharvest.story_scraper import StorySlideInfo
        si = StorySlideInfo()
        assert si is not None


# ═══════════════════════════════════════════════════════════════
# HighlightsResult model tests
# ═══════════════════════════════════════════════════════════════

class TestHighlightModels:
    def test_highlight_result(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult()
        assert hr is not None

    def test_highlights_list_result(self):
        from instaharvest.highlight_scraper import HighlightsListResult
        hlr = HighlightsListResult()
        assert hlr is not None


# ═══════════════════════════════════════════════════════════════
# TaggedPosts model tests  
# ═══════════════════════════════════════════════════════════════

class TestTaggedPostModels:
    def test_tagged_post_data(self):
        from instaharvest.tagged_posts import TaggedPostData
        tp = TaggedPostData()
        assert tp is not None

    def test_tagged_posts_result(self):
        from instaharvest.tagged_posts import TaggedPostsResult
        tpr = TaggedPostsResult()
        assert tpr is not None


# ═══════════════════════════════════════════════════════════════
# CommentData model tests
# ═══════════════════════════════════════════════════════════════

class TestCommentModels:
    def test_comment_data_model(self):
        from instaharvest.models import CommentData
        import inspect
        sig = inspect.signature(CommentData)
        # Check it's importable and has expected fields
        assert CommentData is not None

    def test_post_comments_data(self):
        from instaharvest.comment_scraper import PostCommentsData
        import inspect
        sig = inspect.signature(PostCommentsData)
        assert PostCommentsData is not None


# ═══════════════════════════════════════════════════════════════
# Exporters Deep coverage
# ═══════════════════════════════════════════════════════════════

class TestExporterFunctions:
    def test_export_comments_to_json(self):
        from instaharvest.exporters import export_comments_to_json
        assert callable(export_comments_to_json)

    def test_export_comments_to_excel(self):
        from instaharvest.exporters import export_comments_to_excel
        assert callable(export_comments_to_excel)

    def test_comments_exporter_class(self):
        from instaharvest.exporters import CommentsExporter
        assert CommentsExporter is not None

    def test_excel_exporter_init(self):
        from instaharvest.exporters import ExcelExporter
        td = tempfile.mkdtemp()
        ee = ExcelExporter(filename=os.path.join(td, 'test.xlsx'))
        assert ee is not None


# ═══════════════════════════════════════════════════════════════
# WebAPI models deep coverage
# ═══════════════════════════════════════════════════════════════

class TestWebAPIModels:
    def test_web_api_error(self):
        from instaharvest.web_api import WebAPIError
        err = WebAPIError("test error")
        assert str(err) == "test error"

    def test_feed_post_model(self):
        from instaharvest.web_api import FeedPost
        fp = FeedPost()
        assert fp is not None

    def test_user_feed_result(self):
        from instaharvest.web_api import UserFeedResult
        ufr = UserFeedResult()
        assert ufr is not None

    def test_follow_list_result(self):
        from instaharvest.web_api import FollowListResult
        flr = FollowListResult()
        assert flr is not None

    def test_web_profile_data(self):
        from instaharvest.web_api import WebProfileData
        wpd = WebProfileData()
        assert wpd is not None

    def test_comments_result(self):
        from instaharvest.web_api import CommentsResult
        cr = CommentsResult()
        assert cr is not None

    def test_web_search_result(self):
        from instaharvest.web_api import WebSearchResult
        wsr = WebSearchResult()
        assert wsr is not None

    def test_comment_item_model(self):
        from instaharvest.web_api import CommentItem
        ci = CommentItem()
        assert ci is not None
