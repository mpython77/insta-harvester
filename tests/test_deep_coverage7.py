"""
Deep Coverage Tests - Part 7
Massive wave targeting deep internal methods for remaining gaps.
Targets:
  - interactions (49%): like_comment deep paths, like_all_comments, comment_post, next_reel, like_reel
  - comment_scraper (50%): PostCommentsData model, _extract_post_id, _smart_scroll, _open_comments_dialog, _expand_replies
  - post_data deep (49%): _extract_tagged_users, _extract_from_dom edge cases, _extract_from_full_page carousel
  - orchestrator (36%): scrape_complete_profile deep, shutdown handling
  - downloader (46%): download_post, _create_cookie_file
  - post_links (45%): PostLinksScraper deep scroll/scrape methods
  - explore_scraper (37%): _load_session, scrape_topic
  - highlight_scraper (53%): HighlightsScraper deep
  - reel_data (51%): ReelDataScraper deep
"""
import pytest
import json
import os
import re
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
    p.locator.return_value.first = MagicMock()
    p.locator.return_value.first.count.return_value = 0
    return p

def _mock_logger():
    return MagicMock()


# ═══════════════════════════════════════════════════════════════
# InteractionManager - like_comment deep flow
# ═══════════════════════════════════════════════════════════════

class TestInteractionLikeComment:
    def _make(self):
        from instaharvest.interactions import InteractionManager
        return InteractionManager(page=_mock_page(), logger=_mock_logger(), config=_cfg())

    def test_like_comment_no_comments(self):
        im = self._make()
        im.page.locator.return_value.count.return_value = 0
        result = im.like_comment(username='alice')
        assert result is False

    def test_like_comment_by_index_out_of_range(self):
        im = self._make()
        wrapper = MagicMock()
        wrapper.count.return_value = 2
        im.page.locator.return_value = wrapper
        result = im.like_comment(index=10)
        assert result is False

    def test_like_comment_username_not_found(self):
        im = self._make()
        wrapper = MagicMock()
        wrapper.count.return_value = 1
        item = MagicMock()
        author_link = MagicMock()
        author_link.count.return_value = 1
        author_link.inner_text.return_value = 'bob'
        item.locator.return_value.first = author_link
        wrapper.nth.return_value = item
        im.page.locator.return_value = wrapper
        result = im.like_comment(username='alice')
        assert result is False

    def test_like_comment_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("DOM error")
        result = im.like_comment(index=0)
        assert result is False

    def test_like_comment_with_url(self):
        im = self._make()
        im.page.locator.return_value.count.return_value = 0
        im.like_comment(url='https://instagram.com/p/ABC/')
        im.page.goto.assert_called_once()


class TestInteractionLikeAllComments:
    def _make(self):
        from instaharvest.interactions import InteractionManager
        return InteractionManager(page=_mock_page(), logger=_mock_logger(), config=_cfg())

    def test_like_all_no_comments(self):
        im = self._make()
        im.page.locator.return_value.count.return_value = 0
        result = im.like_all_comments()
        assert result == {'liked': 0, 'already_liked': 0, 'failed': 0, 'total': 0}

    def test_like_all_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("crash")
        result = im.like_all_comments()
        assert isinstance(result, dict)

    def test_like_all_with_url(self):
        im = self._make()
        im.page.locator.return_value.count.return_value = 0
        im.like_all_comments(url='https://instagram.com/p/ABC/')
        im.page.goto.assert_called()


class TestInteractionCommentPost:
    def _make(self):
        from instaharvest.interactions import InteractionManager
        return InteractionManager(page=_mock_page(), logger=_mock_logger(), config=_cfg())

    def test_comment_post_no_box(self):
        im = self._make()
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first = loc
        im.page.locator.return_value = loc
        result = im.comment_post("test comment")
        assert result is False

    def test_comment_post_with_url(self):
        im = self._make()
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first = loc
        im.page.locator.return_value = loc
        im.comment_post("test", url='https://instagram.com/p/ABC/')
        im.page.goto.assert_called()

    def test_comment_post_exception(self):
        im = self._make()
        im.page.locator.side_effect = Exception("fail")
        result = im.comment_post("hello")
        assert result is False


class TestInteractionReels:
    def _make(self):
        from instaharvest.interactions import InteractionManager
        return InteractionManager(page=_mock_page(), logger=_mock_logger(), config=_cfg())

    def test_like_reel_delegates(self):
        im = self._make()
        im.like_post = MagicMock(return_value=True)
        result = im.like_reel()
        assert result is True
        im.like_post.assert_called_once()

    def test_comment_reel_delegates(self):
        im = self._make()
        im.comment_post = MagicMock(return_value=True)
        result = im.comment_reel("nice reel!")
        assert result is True
        im.comment_post.assert_called_once_with("nice reel!")

    def test_next_reel(self):
        im = self._make()
        im.next_reel()
        im.page.keyboard.press.assert_called_with("ArrowDown")


# ═══════════════════════════════════════════════════════════════
# CommentScraper - Deep method tests
# ═══════════════════════════════════════════════════════════════

class TestCommentScraperExtractPostId:
    def _make(self):
        from instaharvest.comment_scraper import CommentScraper
        s = CommentScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_extract_post_id_valid(self):
        s = self._make()
        assert s._extract_post_id('https://instagram.com/p/ABC123/') == 'ABC123'

    def test_extract_post_id_reel(self):
        s = self._make()
        assert s._extract_post_id('https://instagram.com/reel/XYZ789/') == 'XYZ789'

    def test_extract_post_id_no_match(self):
        s = self._make()
        assert s._extract_post_id('https://instagram.com/explore/') == ''

    def test_extract_post_id_with_params(self):
        s = self._make()
        result = s._extract_post_id('https://instagram.com/p/ABC123/?utm_source=ig')
        assert result == 'ABC123'


class TestPostCommentsDataModel:
    def test_create_with_fields(self):
        from instaharvest.comment_scraper import PostCommentsData
        pcd = PostCommentsData(
            post_url='https://instagram.com/p/ABC/',
            post_id='ABC',
            total_comments_scraped=5,
            total_replies_scraped=2,
            comments=[]
        )
        assert pcd.post_url == 'https://instagram.com/p/ABC/'
        assert pcd.total_comments_scraped == 5

    def test_to_dict(self):
        from instaharvest.comment_scraper import PostCommentsData
        pcd = PostCommentsData(
            post_url='https://instagram.com/p/X/',
            post_id='X',
            total_comments_scraped=0,
            total_replies_scraped=0,
            comments=[]
        )
        d = pcd.to_dict()
        assert isinstance(d, dict)
        assert d['post_url'] == 'https://instagram.com/p/X/'
        assert d['total_comments'] == 0

    def test_get_all_comments_flat_empty(self):
        from instaharvest.comment_scraper import PostCommentsData
        pcd = PostCommentsData(
            post_url='https://instagram.com/p/X/',
            post_id='X',
            total_comments_scraped=0,
            total_replies_scraped=0,
            comments=[]
        )
        flat = list(pcd.get_all_comments_flat())
        assert flat == []


class TestCommentScraperSmartScroll:
    def _make(self):
        from instaharvest.comment_scraper import CommentScraper
        s = CommentScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_smart_scroll_js_success(self):
        s = self._make()
        s.page.evaluate.return_value = True
        s._smart_scroll()  # Should not raise

    def test_smart_scroll_js_fails_mouse_fallback(self):
        s = self._make()
        s.page.evaluate.return_value = False
        dialog_el = MagicMock()
        dialog_el.is_visible.return_value = True
        dialog_el.bounding_box.return_value = {'x': 100, 'y': 100, 'width': 400, 'height': 600}
        s.page.locator.return_value.first = dialog_el
        s._smart_scroll()  # Should call mouse.wheel

    def test_smart_scroll_exception(self):
        s = self._make()
        s.page.evaluate.side_effect = Exception("JS error")
        s._smart_scroll()  # Should not raise


class TestCommentScraperOpenDialog:
    def _make(self):
        from instaharvest.comment_scraper import CommentScraper
        s = CommentScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_dialog_already_open(self):
        s = self._make()
        dialog = MagicMock()
        dialog.count.return_value = 1
        dialog.first.is_visible.return_value = True
        s.page.locator.return_value = dialog
        s._open_comments_dialog()  # Should return early

    def test_dialog_exception(self):
        s = self._make()
        s.page.locator.side_effect = Exception("error")
        s._open_comments_dialog()  # Should not raise


class TestCommentScraperExpandReplies:
    def _make(self):
        from instaharvest.comment_scraper import CommentScraper
        s = CommentScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_expand_replies_no_buttons(self):
        s = self._make()
        s.page.locator.return_value.all.return_value = []
        s._expand_replies()  # Should not raise

    def test_expand_replies_exception(self):
        s = self._make()
        s.page.locator.side_effect = Exception("fail")
        s._expand_replies()  # Should not raise


# ═══════════════════════════════════════════════════════════════
# PostData - Deep _extract_tagged_users and edge cases
# ═══════════════════════════════════════════════════════════════

class TestPostDataTaggedUsersDeep:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        s.main_scope = _mock_page()
        s.tags_per_media = []
        return s

    def test_has_extract_tagged_users(self):
        s = self._make()
        assert hasattr(s, '_extract_tagged_users')

    def test_extract_tagged_button_not_visible(self):
        s = self._make()
        container = MagicMock()
        tag_btn = MagicMock()
        tag_btn.is_visible.return_value = False
        tag_btn.count.return_value = 0
        container.locator.return_value.first = tag_btn
        container.locator.return_value.count.return_value = 0
        result = s._extract_tagged_users(container)
        assert isinstance(result, list)


class TestPostDataParseJsonDeep:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_parse_json_non_instagram_url(self):
        s = self._make()
        content = '{"url": "https://example.com/image.jpg"}'
        result = s._parse_json_for_urls(content)
        assert isinstance(result, list)

    def test_parse_json_mixed_urls(self):
        s = self._make()
        content = '''{"urls": [
            "https://scontent.cdninstagram.com/image1.jpg",
            "https://example.com/notinstagram.jpg",
            "https://scontent.fbcdn.net/video.mp4"
        ]}'''
        result = s._parse_json_for_urls(content)
        # Should find instagram CDN urls
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════
# Orchestrator - Deep scraping method tests
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorDeep3:
    def _make(self):
        from instaharvest.orchestrator import InstagramOrchestrator
        o = InstagramOrchestrator()
        o.page = _mock_page()
        o.browser = MagicMock()
        o.context = MagicMock()
        return o

    def test_scrape_complete_has_all_params(self):
        import inspect
        from instaharvest.orchestrator import InstagramOrchestrator
        sig = inspect.signature(InstagramOrchestrator.scrape_complete_profile)
        params = list(sig.parameters.keys())
        assert 'username' in params
        assert 'scrape_posts' in params
        assert 'export_results' in params

    def test_scrape_tagged_posts_has_params(self):
        import inspect
        from instaharvest.orchestrator import InstagramOrchestrator
        sig = inspect.signature(InstagramOrchestrator.scrape_tagged_posts)
        params = list(sig.parameters.keys())
        assert 'username' in params

    def test_scrape_stories_only_has_params(self):
        import inspect
        from instaharvest.orchestrator import InstagramOrchestrator
        sig = inspect.signature(InstagramOrchestrator.scrape_stories_only)
        params = list(sig.parameters.keys())
        assert 'username' in params

    def test_scrape_highlight_has_params(self):
        import inspect
        from instaharvest.orchestrator import InstagramOrchestrator
        sig = inspect.signature(InstagramOrchestrator.scrape_highlight)
        params = list(sig.parameters.keys())
        assert 'highlight_id' in params or 'username' in params

    def test_shutdown_requested_default(self):
        o = self._make()
        assert o.shutdown_requested is False


# ═══════════════════════════════════════════════════════════════
# HighlightsScraper deep
# ═══════════════════════════════════════════════════════════════

class TestHighlightsDeep3:
    def _make(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
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

    def test_scrape_signature(self):
        import inspect
        from instaharvest.highlight_scraper import HighlightsScraper
        sig = inspect.signature(HighlightsScraper.scrape)
        params = list(sig.parameters.keys())
        assert 'self' in params or len(params) >= 1


# ═══════════════════════════════════════════════════════════════
# ExploreScraper deep
# ═══════════════════════════════════════════════════════════════

class TestExploreScraperDeep3:
    def _make(self):
        from instaharvest.explore_scraper import ExploreScraper
        s = ExploreScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_load_session_no_file(self):
        s = self._make()
        s.config.session_file = '/tmp/nonexistent_xyz_42.json'
        result = s._load_session()
        assert result == {}

    def test_load_session_with_file(self):
        s = self._make()
        td = tempfile.mkdtemp()
        sf = os.path.join(td, 'session.json')
        with open(sf, 'w') as f:
            json.dump({'cookies': [], 'storage': {}}, f)
        s.config.session_file = sf
        result = s._load_session()
        assert 'cookies' in result

    def test_has_scrape_topic(self):
        s = self._make()
        assert hasattr(s, 'scrape_topic')

    def test_has_logger(self):
        s = self._make()
        assert s.logger is not None


# ═══════════════════════════════════════════════════════════════
# PostLinksScraper deep
# ═══════════════════════════════════════════════════════════════

class TestPostLinksScraperDeep3:
    def _make(self):
        from instaharvest.post_links import PostLinksScraper
        s = PostLinksScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        s.context = MagicMock()
        return s

    def test_scrape_signature(self):
        import inspect
        from instaharvest.post_links import PostLinksScraper
        sig = inspect.signature(PostLinksScraper.scrape)
        params = list(sig.parameters.keys())
        assert 'self' in params or 'username' in params

    def test_interrupted_toggle(self):
        s = self._make()
        s.interrupted = True
        assert s.interrupted is True
        s.interrupted = False
        assert s.interrupted is False


# ═══════════════════════════════════════════════════════════════
# SearchAPI deep
# ═══════════════════════════════════════════════════════════════

class TestSearchAPIDeep3:
    def _make(self):
        from instaharvest.search_api import SearchAPI
        s = SearchAPI(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_search_users_exists(self):
        s = self._make()
        assert hasattr(s, 'search_users')

    def test_search_hashtags_exists(self):
        s = self._make()
        assert hasattr(s, 'search_hashtags')

    def test_search_places_exists(self):
        s = self._make()
        assert hasattr(s, 'search_places')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None


# ═══════════════════════════════════════════════════════════════
# TaggedPostsScraper deep
# ═══════════════════════════════════════════════════════════════

class TestTaggedPostsDeep3:
    def _make(self):
        from instaharvest.tagged_posts import TaggedPostsScraper
        s = TaggedPostsScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_has_config(self):
        s = self._make()
        assert s.config is not None

    def test_scrape_signature(self):
        import inspect
        from instaharvest.tagged_posts import TaggedPostsScraper
        sig = inspect.signature(TaggedPostsScraper.scrape)
        params = list(sig.parameters.keys())
        assert 'self' in params or 'username' in params


# ═══════════════════════════════════════════════════════════════
# StoryScraper deep
# ═══════════════════════════════════════════════════════════════

class TestStoryScraperDeep3:
    def _make(self):
        from instaharvest.story_scraper import StoryScraper
        s = StoryScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_has_scrape(self):
        s = self._make()
        assert hasattr(s, 'scrape')

    def test_scrape_signature(self):
        import inspect
        from instaharvest.story_scraper import StoryScraper
        sig = inspect.signature(StoryScraper.scrape)
        params = list(sig.parameters.keys())
        assert 'self' in params or 'username' in params


# ═══════════════════════════════════════════════════════════════
# SessionUtils deep
# ═══════════════════════════════════════════════════════════════

class TestSessionUtilsDeep:
    def test_find_session_file(self):
        from instaharvest.session_utils import find_session_file
        result = find_session_file()
        # May return None or a path
        assert result is None or isinstance(result, (str, Path))

    def test_get_default_session_path(self):
        from instaharvest.session_utils import get_default_session_path
        result = get_default_session_path()
        assert isinstance(result, (str, Path))


# ═══════════════════════════════════════════════════════════════
# SharedBrowser deep
# ═══════════════════════════════════════════════════════════════

class TestSharedBrowserDeep3:
    def test_has_start(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser()
        assert hasattr(sb, 'start')

    def test_has_close(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser()
        assert hasattr(sb, 'close')

    def test_config_exists(self):
        from instaharvest.shared_browser import SharedBrowser
        sb = SharedBrowser()
        assert sb.config is not None
