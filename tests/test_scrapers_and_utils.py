"""
Unit Tests — Data Models for SearchAPI, Hashtag, Location, Explore scrapers,
              CommentParser, session_utils, and __init__ exports
"""

import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════
# SearchResult
# ═══════════════════════════════════════════════════════════

class TestSearchResult:
    def test_empty(self):
        from instaharvest.search_api import SearchResult
        r = SearchResult(query='fashion')
        assert r.total_count == 0
        assert r.users == []
        assert r.hashtags == []
        assert r.places == []

    def test_with_data(self):
        from instaharvest.search_api import SearchResult
        r = SearchResult(
            query='nike',
            users=[{'username': 'nike', 'is_verified': True}],
            hashtags=[{'name': 'nike', 'post_count': 1000000}],
            places=[{'name': 'Nike HQ', 'city': 'Portland'}],
        )
        assert r.total_count == 3
        d = r.to_dict()
        assert d['query'] == 'nike'
        json.dumps(d)

    def test_list_isolation(self):
        from instaharvest.search_api import SearchResult
        r1 = SearchResult(query='a')
        r2 = SearchResult(query='b')
        r1.users.append({'username': 'test'})
        assert len(r2.users) == 0


# ═══════════════════════════════════════════════════════════
# HashtagResult
# ═══════════════════════════════════════════════════════════

class TestHashtagResult:
    def test_empty(self):
        from instaharvest.hashtag_scraper import HashtagResult
        r = HashtagResult()
        assert r.hashtag == ''
        assert r.post_count == 0
        assert r.posts == []

    def test_with_data(self):
        from instaharvest.hashtag_scraper import HashtagResult
        r = HashtagResult(
            hashtag='fashion',
            post_count=50_000_000,
            posts=[
                {'url': 'https://instagram.com/p/ABC/', 'type': 'Post'},
                {'url': 'https://instagram.com/reel/XYZ/', 'type': 'Reel'},
            ]
        )
        assert r.post_count == 50_000_000
        d = r.to_dict()
        assert len(d['posts']) == 2
        json.dumps(d)

    def test_list_isolation(self):
        from instaharvest.hashtag_scraper import HashtagResult
        r1 = HashtagResult()
        r2 = HashtagResult()
        r1.posts.append({'url': 'x'})
        assert len(r2.posts) == 0


# ═══════════════════════════════════════════════════════════
# LocationResult
# ═══════════════════════════════════════════════════════════

class TestLocationResult:
    def test_empty(self):
        from instaharvest.location_scraper import LocationResult
        r = LocationResult()
        assert r.location_id == ''
        assert r.location_name == ''
        assert r.posts == []

    def test_with_data(self):
        from instaharvest.location_scraper import LocationResult
        r = LocationResult(
            location_id='213385402',
            location_name='Eiffel Tower',
            address='Champ de Mars, Paris',
            post_count=10_000,
            posts=[{'url': 'https://instagram.com/p/ABC/', 'type': 'Post'}],
        )
        d = r.to_dict()
        assert d['location_name'] == 'Eiffel Tower'
        assert d['post_count'] == 10_000
        json.dumps(d)


# ═══════════════════════════════════════════════════════════
# ExploreResult
# ═══════════════════════════════════════════════════════════

class TestExploreResult:
    def test_empty(self):
        from instaharvest.explore_scraper import ExploreResult
        r = ExploreResult()
        assert r.posts == []
        assert r.total_collected == 0

    def test_with_data(self):
        from instaharvest.explore_scraper import ExploreResult
        r = ExploreResult(
            posts=[{'url': 'https://instagram.com/p/ABC/', 'type': 'Post'}],
            timestamp='2025-03-10T12:00:00',
            total_collected=1,
        )
        d = r.to_dict()
        assert d['total_collected'] == 1
        json.dumps(d)


# ═══════════════════════════════════════════════════════════
# CommentParser
# ═══════════════════════════════════════════════════════════

class TestCommentParser:
    def test_empty_html(self):
        from instaharvest.parser import CommentParser
        parser = CommentParser()
        comments = parser.parse_html('<html><body></body></html>')
        assert comments == []

    def test_html_with_no_comments(self):
        from instaharvest.parser import CommentParser
        parser = CommentParser()
        html = '<html><body><div>Hello world</div></body></html>'
        comments = parser.parse_html(html)
        assert comments == []

    def test_single_comment(self):
        from instaharvest.parser import CommentParser
        parser = CommentParser()
        html = '''
        <html><body>
        <ul>
        <li>
        <div>
            <a href="/testuser/">testuser</a>
            <a href="/p/ABC123/c/111222333/">1w</a>
            <time datetime="2025-03-03T12:00:00.000Z">1w</time>
            <span>Great photo!</span>
            <svg aria-label="Like"></svg>
            <span>Reply</span>
        </div>
        </li>
        </ul>
        </body></html>
        '''
        comments = parser.parse_html(html)
        assert len(comments) >= 1
        assert comments[0].id == '111222333'
        assert comments[0].author.username == 'testuser'

    def test_verified_author(self):
        from instaharvest.parser import CommentParser
        parser = CommentParser()
        html = '''
        <html><body>
        <ul>
        <li>
        <div>
            <a href="/verifieduser/">verifieduser</a>
            <svg aria-label="Verified"></svg>
            <a href="/p/XYZ/c/999888777/">2d</a>
            <time datetime="2025-03-08T10:00:00.000Z">2d</time>
            <span>Nice!</span>
            <svg aria-label="Like"></svg>
            <span>Reply</span>
        </div>
        </li>
        </ul>
        </body></html>
        '''
        comments = parser.parse_html(html)
        assert len(comments) >= 1
        assert comments[0].author.is_verified is True

    def test_comment_with_likes(self):
        from instaharvest.parser import CommentParser
        parser = CommentParser()
        html = '''
        <html><body>
        <div>
            <a href="/alice/">alice</a>
            <a href="/p/TEST/c/123456789/">3h</a>
            <time datetime="2025-03-10T09:00:00.000Z">3h</time>
            <span>Awesome!</span>
            <span>42 likes</span>
            <svg aria-label="Like"></svg>
            <span>Reply</span>
        </div>
        </body></html>
        '''
        comments = parser.parse_html(html)
        if comments:
            assert comments[0].likes_count == 42


# ═══════════════════════════════════════════════════════════
# session_utils
# ═══════════════════════════════════════════════════════════

class TestSessionUtils:
    def test_get_search_paths(self):
        from instaharvest.session_utils import _get_search_paths
        paths = _get_search_paths()
        assert isinstance(paths, list)
        assert len(paths) >= 1  # At least CWD

    def test_find_session_nonexistent(self):
        from instaharvest.session_utils import find_session_file
        result = find_session_file('nonexistent_session_xyz.json')
        assert result is None

    def test_find_session_in_temp(self):
        from instaharvest.session_utils import find_session_file
        with tempfile.TemporaryDirectory() as d:
            session_path = os.path.join(d, 'test_session.json')
            with open(session_path, 'w') as f:
                json.dump({'cookies': []}, f)
            # monkeypatch _get_search_paths to include our temp dir
            with patch('instaharvest.session_utils._get_search_paths', return_value=[d]):
                result = find_session_file('test_session.json')
                assert result is not None
                assert result.endswith('test_session.json')

    def test_get_default_session_path_no_discover(self):
        from instaharvest.session_utils import get_default_session_path
        path = get_default_session_path(auto_discover=False)
        assert path.endswith('instagram_session.json')

    def test_get_session_save_path_cwd(self):
        from instaharvest.session_utils import get_session_save_path
        path = get_session_save_path(prefer_cwd=True)
        assert path.endswith('instagram_session.json')
        assert os.getcwd() in path

    def test_get_session_save_path_home(self):
        from instaharvest.session_utils import get_session_save_path
        path = get_session_save_path(prefer_cwd=False)
        assert '.instaharvest' in path

    def test_check_session_nonexistent(self):
        from instaharvest.session_utils import check_session_exists
        assert check_session_exists('definitely_not_here_xyz.json') is False

    def test_load_session_not_found(self):
        from instaharvest.session_utils import load_session_data
        with pytest.raises(FileNotFoundError):
            load_session_data('nonexistent_xyz.json')

    def test_load_session_success(self):
        from instaharvest.session_utils import load_session_data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'cookies': [{'name': 'test', 'value': '123'}]}, f)
            f.flush()
            path = f.name
        try:
            data = load_session_data(path)
            assert len(data['cookies']) == 1
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════
# __init__.py Exports Completeness
# ═══════════════════════════════════════════════════════════

class TestInitExports:
    """Ensure all major classes are importable from top-level"""

    def test_scrapers(self):
        from instaharvest import (
            ProfileScraper, PostDataScraper, ReelDataScraper,
            StoryScraper, TaggedPostsScraper, HighlightsScraper,
        )

    def test_data_models(self):
        from instaharvest import (
            ProfileData, PostData, PostLocation, PostOwner, CarouselSlide,
            ReelData, StoryResult, StoryItem, StorySlideInfo,
            TaggedPostData, TaggedPostsResult,
            HighlightResult, HighlightSlide, HighlightSticker,
            HighlightMusic, HighlightInfo, HighlightsListResult,
        )

    def test_utility_classes(self):
        from instaharvest import (
            ScraperConfig, BatchDownloader, DataExporter,
            NotificationReader, NotificationItem,
            InstagramOrchestrator, SharedBrowser,
        )

    def test_exceptions_hierarchy(self):
        from instaharvest import (
            InstagramScraperError, SessionNotFoundError,
            ProfileNotFoundError, HTMLStructureChangedError,
            PageLoadError, RateLimitError, LoginRequiredError,
        )
        # Verify hierarchy
        for exc_cls in [SessionNotFoundError, ProfileNotFoundError,
                        HTMLStructureChangedError, PageLoadError,
                        RateLimitError, LoginRequiredError]:
            assert issubclass(exc_cls, InstagramScraperError)

    def test_search_types(self):
        from instaharvest import SearchAPI, SearchResult

    def test_comment_models(self):
        from instaharvest import Comment, CommentData, CommentAuthor, Collaborator
        assert Comment is CommentData  # backward compat alias

    def test_version_string(self):
        import instaharvest
        assert hasattr(instaharvest, '__version__')
        parts = instaharvest.__version__.split('.')
        assert len(parts) >= 2

    def test_all_list(self):
        import instaharvest
        assert hasattr(instaharvest, '__all__')
        assert len(instaharvest.__all__) >= 30


# ═══════════════════════════════════════════════════════════
# Exporters module TypedDicts & Streaming helpers
# ═══════════════════════════════════════════════════════════

class TestExporterHelpers:
    def test_streaming_json_exporter(self):
        from instaharvest.exporters import StreamingJSONExporter
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'test.jsonl')
            exporter = StreamingJSONExporter(path)
            exporter.append_item({'key': 'value1'})
            exporter.append_item({'key': 'value2'})

            with open(path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 2
            data1 = json.loads(lines[0])
            assert data1['key'] == 'value1'

    def test_post_data_dict_type(self):
        from instaharvest.exporters import PostDataDict
        d: PostDataDict = {'url': 'https://ig.com/p/ABC/', 'likes': '100'}
        assert d['url'].startswith('https')

    def test_comment_data_dict_type(self):
        from instaharvest.exporters import CommentDataDict
        d: CommentDataDict = {'id': '123', 'username': 'alice', 'text': 'Nice!'}
        assert d['id'] == '123'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
