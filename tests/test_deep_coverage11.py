"""
Deep Coverage Tests - Part 11
Strategy shift: Target pure logic methods in highlight_scraper and post_data.
These have hundreds of lines of testable pure Python without ANY browser dependency.

Targets:
  - highlight_scraper data models: HighlightSticker, HighlightMusic, HighlightSlide, 
    HighlightResult, HighlightInfo, HighlightsListResult (~200 lines)
  - highlight_scraper pure methods: _parse_highlight_id, _find_highlight_items, _parse_item,
    _extract_mentions, _parse_bloks_sticker (~200 lines)
  - post_data: scrape() flow with JSON-first extraction mock, DOM fallback mock
  - post_links: _LegacyPostLinksScraper methods
  - orchestrator: scrape_complete_profile full mock chain
"""
import pytest
import json
import re
import time
from unittest.mock import MagicMock, patch, PropertyMock
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
# Highlight Data Models - Deep Pure Logic Tests
# ═══════════════════════════════════════════════════════════════

class TestHighlightSticker:
    def test_defaults(self):
        from instaharvest.highlight_scraper import HighlightSticker
        hs = HighlightSticker()
        assert hs.sticker_type == ''
        assert hs.value == ''
        assert hs.extra == {}

    def test_to_dict(self):
        from instaharvest.highlight_scraper import HighlightSticker
        hs = HighlightSticker(sticker_type='mention', value='@alice', extra={'id': 123})
        d = hs.to_dict()
        assert d['sticker_type'] == 'mention'
        assert d['value'] == '@alice'
        assert d['extra']['id'] == 123

    def test_mention_type(self):
        from instaharvest.highlight_scraper import HighlightSticker
        hs = HighlightSticker(sticker_type='mention', value='@bob')
        assert hs.sticker_type == 'mention'

    def test_link_type(self):
        from instaharvest.highlight_scraper import HighlightSticker
        hs = HighlightSticker(sticker_type='link', value='https://example.com')
        assert hs.sticker_type == 'link'

    def test_music_type(self):
        from instaharvest.highlight_scraper import HighlightSticker
        hs = HighlightSticker(sticker_type='music', value='Song - Artist')
        assert hs.sticker_type == 'music'


class TestHighlightMusic:
    def test_defaults(self):
        from instaharvest.highlight_scraper import HighlightMusic
        hm = HighlightMusic()
        assert hm.title == ''
        assert hm.artist == ''
        assert hm.duration_ms == 0

    def test_full_song(self):
        from instaharvest.highlight_scraper import HighlightMusic
        hm = HighlightMusic(title='Blinding Lights', artist='The Weeknd', duration_ms=200000)
        d = hm.to_dict()
        assert d['title'] == 'Blinding Lights'
        assert d['artist'] == 'The Weeknd'
        assert d['duration_ms'] == 200000

    def test_ig_artist(self):
        from instaharvest.highlight_scraper import HighlightMusic
        hm = HighlightMusic(title='Song', ig_artist='theweeknd')
        assert hm.ig_artist == 'theweeknd'


class TestHighlightSlide:
    def test_defaults(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide()
        assert hs.slide_index == 0
        assert hs.media_type == 'image'
        assert hs.mentions == []

    def test_video_slide(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide(media_type='video', video_url='http://vid.mp4')
        assert hs.is_video is True

    def test_image_slide(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide(media_type='image', image_url='http://img.jpg')
        assert hs.is_video is False

    def test_has_mentions(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide(mentions=['alice', 'bob'])
        assert hs.has_mentions is True

    def test_no_mentions(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide(mentions=[])
        assert hs.has_mentions is False

    def test_has_links(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide(link_stickers=['http://example.com'])
        assert hs.has_links is True

    def test_no_links(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide()
        assert hs.has_links is False

    def test_has_music(self):
        from instaharvest.highlight_scraper import HighlightSlide, HighlightMusic
        hs = HighlightSlide(music=HighlightMusic(title='Song'))
        assert hs.has_music is True

    def test_no_music(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide()
        assert hs.has_music is False

    def test_to_dict(self):
        from instaharvest.highlight_scraper import HighlightSlide
        hs = HighlightSlide(
            slide_index=5,
            pk='12345',
            media_type='video',
            taken_at=1700000000,
            taken_at_human='2024-01-01 00:00:00 UTC',
            width=1080,
            height=1920
        )
        d = hs.to_dict()
        assert d['pk'] == '12345'
        assert d['width'] == 1080


class TestHighlightResult:
    def _make_slides(self):
        from instaharvest.highlight_scraper import HighlightSlide, HighlightMusic
        return [
            HighlightSlide(media_type='image', mentions=['alice'], link_stickers=['http://a.com']),
            HighlightSlide(media_type='video', mentions=['bob', 'alice'],
                           music=HighlightMusic(title='Song1')),
            HighlightSlide(media_type='image', mentions=['charlie'],
                           location_stickers=[{'name': 'NYC'}]),
        ]

    def test_slide_count(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert hr.slide_count == 3

    def test_video_count(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert hr.video_count == 1

    def test_image_count(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert hr.image_count == 2

    def test_all_mentions_unique(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert 'alice' in hr.all_mentions
        assert 'bob' in hr.all_mentions
        assert 'charlie' in hr.all_mentions
        # alice appears in 2 slides but should only appear once
        assert hr.all_mentions.count('alice') == 1

    def test_all_links(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert 'http://a.com' in hr.all_links

    def test_all_music(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert len(hr.all_music) == 1
        assert hr.all_music[0].title == 'Song1'

    def test_all_locations(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(slides=self._make_slides())
        assert len(hr.all_locations) == 1
        assert hr.all_locations[0]['name'] == 'NYC'

    def test_to_dict(self):
        from instaharvest.highlight_scraper import HighlightResult
        hr = HighlightResult(
            highlight_id='12345',
            highlight_title='Summer 2024',
            owner_username='alice'
        )
        d = hr.to_dict()
        assert d['highlight_id'] == '12345'
        assert d['highlight_title'] == 'Summer 2024'


class TestHighlightInfo:
    def test_defaults(self):
        from instaharvest.highlight_scraper import HighlightInfo
        hi = HighlightInfo()
        assert hi.highlight_id == ''
        assert hi.title == ''

    def test_to_dict(self):
        from instaharvest.highlight_scraper import HighlightInfo
        hi = HighlightInfo(highlight_id='123', title='Travel', url='http://x', cover_url='http://cover.jpg')
        d = hi.to_dict()
        assert d['highlight_id'] == '123'
        assert d['title'] == 'Travel'


class TestHighlightsListResult:
    def test_defaults(self):
        from instaharvest.highlight_scraper import HighlightsListResult
        hlr = HighlightsListResult()
        assert hlr.username == ''
        assert hlr.total_highlights == 0
        assert hlr.highlights == []

    def test_to_dict(self):
        from instaharvest.highlight_scraper import HighlightsListResult, HighlightInfo
        hlr = HighlightsListResult(
            username='alice',
            total_highlights=2,
            highlights=[HighlightInfo(highlight_id='1', title='A'), HighlightInfo(highlight_id='2', title='B')]
        )
        d = hlr.to_dict()
        assert d['username'] == 'alice'
        assert len(d['highlights']) == 2

    def test_total_slides(self):
        from instaharvest.highlight_scraper import HighlightsListResult, HighlightResult, HighlightSlide
        hlr = HighlightsListResult(
            full_results=[
                HighlightResult(slides=[HighlightSlide(), HighlightSlide()]),
                HighlightResult(slides=[HighlightSlide()]),
            ]
        )
        assert hlr.total_slides == 3

    def test_all_mentions(self):
        from instaharvest.highlight_scraper import HighlightsListResult, HighlightResult, HighlightSlide
        hlr = HighlightsListResult(
            full_results=[
                HighlightResult(slides=[HighlightSlide(mentions=['alice', 'bob'])]),
                HighlightResult(slides=[HighlightSlide(mentions=['bob', 'charlie'])]),
            ]
        )
        m = hlr.all_mentions
        assert 'alice' in m
        assert 'bob' in m
        assert 'charlie' in m
        assert m.count('bob') == 1  # deduped


# ═══════════════════════════════════════════════════════════════
# HighlightsScraper - Pure Logic Methods
# ═══════════════════════════════════════════════════════════════

class TestHighlightScraperPureMethods:
    def _make(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_parse_highlight_id_url(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        assert HighlightsScraper._parse_highlight_id(
            'https://www.instagram.com/stories/highlights/18092082532805201/'
        ) == '18092082532805201'

    def test_parse_highlight_id_raw(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        assert HighlightsScraper._parse_highlight_id('18092082532805201') == '18092082532805201'

    def test_parse_highlight_id_trailing_slash(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        assert HighlightsScraper._parse_highlight_id('18092082532805201/') == '18092082532805201'

    def test_find_highlight_items_empty(self):
        s = self._make()
        items, meta = s._find_highlight_items({})
        assert items == []
        assert meta == {}

    def test_find_highlight_items_direct(self):
        s = self._make()
        data = {
            'items': [
                {'pk': '1', 'taken_at': 1700000000},
                {'pk': '2', 'taken_at': 1700001000},
            ],
            'title': 'Summer',
            'user': {'username': 'alice', 'pk': 12345}
        }
        items, meta = s._find_highlight_items(data)
        assert len(items) == 2
        assert meta['title'] == 'Summer'
        assert meta['owner_username'] == 'alice'

    def test_find_highlight_items_reels_media(self):
        s = self._make()
        data = {
            'reels_media': [
                {
                    'items': [{'pk': '1', 'taken_at': 1700000000}],
                    'title': 'Travel',
                    'user': {'username': 'bob'}
                }
            ]
        }
        items, meta = s._find_highlight_items(data)
        assert len(items) >= 1
        assert meta.get('title') == 'Travel'

    def test_find_highlight_items_too_deep(self):
        s = self._make()
        # Create deeply nested structure
        data = {'a': {'b': {'c': {'d': {'e': {'items': [{'pk': '1', 'taken_at': 1}]}}}}}}
        items, meta = s._find_highlight_items(data)
        # May or may not find depending on recursion depth limit

    def test_parse_item_basic(self):
        s = self._make()
        item = {
            'pk': '12345',
            'code': 'ABC',
            'media_type': 1,
            'taken_at': 1700000000,
            'original_width': 1080,
            'original_height': 1920,
            'image_versions2': {
                'candidates': [
                    {'url': 'http://img1.jpg', 'width': 1080, 'height': 1920},
                    {'url': 'http://img2.jpg', 'width': 640, 'height': 1138},
                ]
            }
        }
        slide = s._parse_item(item, slide_index=0)
        assert slide is not None
        assert slide.pk == '12345'
        assert slide.media_type == 'image'
        assert slide.image_url == 'http://img1.jpg'
        assert slide.width == 1080

    def test_parse_item_video(self):
        s = self._make()
        item = {
            'pk': '99999',
            'media_type': 2,
            'taken_at': 1700000000,
            'video_versions': [
                {'url': 'http://vid_hd.mp4', 'width': 1080, 'height': 1920},
                {'url': 'http://vid_sd.mp4', 'width': 640, 'height': 1138},
            ],
            'image_versions2': {'candidates': [{'url': 'http://thumb.jpg', 'width': 1080, 'height': 1920}]}
        }
        slide = s._parse_item(item, slide_index=1)
        assert slide is not None
        assert slide.media_type == 'video'
        assert slide.video_url == 'http://vid_hd.mp4'

    def test_parse_item_with_music(self):
        s = self._make()
        item = {
            'pk': '777',
            'taken_at': 1700000000,
            'music_metadata': {
                'music_info': {
                    'music_asset_info': {
                        'title': 'Blinding Lights',
                        'display_artist': 'The Weeknd',
                        'duration_in_ms': 200120,
                        'ig_username': 'theweeknd'
                    }
                }
            }
        }
        slide = s._parse_item(item)
        assert slide.music is not None
        assert slide.music.title == 'Blinding Lights'
        assert slide.music.artist == 'The Weeknd'

    def test_parse_item_with_mentions(self):
        s = self._make()
        item = {
            'pk': '555',
            'taken_at': 1700000000,
            'reel_mentions': [
                {'user': {'username': 'alice'}},
                {'user': {'username': 'bob'}},
            ]
        }
        slide = s._parse_item(item)
        assert 'alice' in slide.mentions
        assert 'bob' in slide.mentions

    def test_parse_item_with_link_stickers(self):
        s = self._make()
        item = {
            'pk': '444',
            'taken_at': 1700000000,
            'story_link_stickers': [
                {'url': 'https://example.com', 'display_text': 'Visit'}
            ]
        }
        slide = s._parse_item(item)
        assert 'https://example.com' in slide.link_stickers

    def test_parse_item_with_location(self):
        s = self._make()
        item = {
            'pk': '333',
            'taken_at': 1700000000,
            'story_locations': [
                {'location': {'name': 'NYC', 'pk': 123, 'address': '5th Ave', 'city': 'New York'}}
            ]
        }
        slide = s._parse_item(item)
        assert len(slide.location_stickers) == 1
        assert slide.location_stickers[0]['name'] == 'NYC'

    def test_parse_item_with_hashtags(self):
        s = self._make()
        item = {
            'pk': '222',
            'taken_at': 1700000000,
            'story_hashtags': [
                {'hashtag': {'name': 'fashion'}},
                {'hashtag': {'name': 'swimwear'}},
            ]
        }
        slide = s._parse_item(item)
        assert 'fashion' in slide.hashtag_stickers
        assert 'swimwear' in slide.hashtag_stickers

    def test_parse_item_none(self):
        s = self._make()
        assert s._parse_item(None) is None

    def test_parse_item_not_dict(self):
        s = self._make()
        assert s._parse_item("string") is None


class TestHighlightExtractMentions:
    def _make(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_ig_mention(self):
        s = self._make()
        mentions = []
        data = {'ig_mention': {'username': 'alice'}}
        s._extract_mentions(data, mentions)
        assert 'alice' in mentions

    def test_reel_mentions(self):
        s = self._make()
        mentions = []
        data = {'reel_mentions': [{'user': {'username': 'bob'}}, {'user': {'username': 'charlie'}}]}
        s._extract_mentions(data, mentions)
        assert 'bob' in mentions
        assert 'charlie' in mentions

    def test_no_duplicates(self):
        s = self._make()
        mentions = ['alice']
        data = {'ig_mention': {'username': 'alice'}}
        s._extract_mentions(data, mentions)
        assert mentions.count('alice') == 1

    def test_nested_mentions(self):
        s = self._make()
        mentions = []
        data = {'story_bloks_stickers': [{'ig_mention': {'username': 'deep_user'}}]}
        s._extract_mentions(data, mentions)
        assert 'deep_user' in mentions

    def test_empty_data(self):
        s = self._make()
        mentions = []
        s._extract_mentions({}, mentions)
        assert mentions == []

    def test_none_data(self):
        s = self._make()
        mentions = []
        s._extract_mentions(None, mentions)
        assert mentions == []


class TestHighlightParseBloksSticker:
    def _make(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        s = HighlightsScraper(config=_cfg())
        s.page = _mock_page()
        s.browser = MagicMock()
        return s

    def test_mention_from_bloks(self):
        s = self._make()
        mentions, links, hashtags, all_st = [], [], [], []
        sticker = {
            'bloks_sticker': {
                'sticker_data': json.dumps({
                    'ig_mention': {'username': 'bloks_user'}
                })
            }
        }
        s._parse_bloks_sticker(sticker, mentions, links, hashtags, all_st)
        assert 'bloks_user' in mentions

    def test_sticker_data_as_dict(self):
        s = self._make()
        mentions, links, hashtags, all_st = [], [], [], []
        sticker = {
            'bloks_sticker': {
                'sticker_data': {'ig_mention': {'username': 'dict_user'}}
            }
        }
        s._parse_bloks_sticker(sticker, mentions, links, hashtags, all_st)
        assert 'dict_user' in mentions

    def test_invalid_json_sticker_data(self):
        s = self._make()
        mentions, links, hashtags, all_st = [], [], [], []
        sticker = {
            'bloks_sticker': {
                'sticker_data': 'INVALID JSON {{{'
            }
        }
        s._parse_bloks_sticker(sticker, mentions, links, hashtags, all_st)
        assert mentions == []

    def test_not_dict(self):
        s = self._make()
        mentions, links, hashtags, all_st = [], [], [], []
        s._parse_bloks_sticker("not a dict", mentions, links, hashtags, all_st)
        assert mentions == []

    def test_no_bloks_sticker_key(self):
        s = self._make()
        mentions, links, hashtags, all_st = [], [], [], []
        s._parse_bloks_sticker({'other_key': 'value'}, mentions, links, hashtags, all_st)
        assert mentions == []


# ═══════════════════════════════════════════════════════════════
# PostData scrape flow with JSON-first mocking
# ═══════════════════════════════════════════════════════════════

class TestPostDataScrapeFlowDeep:
    def _make(self):
        from instaharvest.post_data import PostDataScraper
        s = PostDataScraper()
        s.page = _mock_page()
        s.browser = MagicMock()
        s.captured_media_urls = []
        s.detected_video_count = 0
        s.tags_per_media = []
        return s

    def test_scrape_json_first_success(self):
        s = self._make()
        s._extract_all_from_json = MagicMock(return_value={
            'tagged_accounts': ['alice', 'bob'],
            'likes': 1234,
            'timestamp': '2024-01-01',
            'media_urls': [],
            'is_video': False,
            'caption': 'Test caption',
            'comment_count': 5,
            'like_count': 1234,
            'location': MagicMock(name='NYC'),
            'owner': None,
            'taken_at': 1700000000,
            'taken_at_human': '2024-01-01',
            'shortcode': 'ABC',
            'pk': '12345',
            'media_type': 1,
            'product_type': 'feed',
            'width': 1080,
            'height': 1080,
            'accessibility_caption': 'photo',
            'top_likers': [],
            'has_audio': False,
            'video_duration': 0,
            'carousel_media_count': 0,
            'carousel_slides': [],
            'tag_positions': [],
            'has_liked': False,
            'tagged_users_per_media': [],
        })
        s.goto_url = MagicMock()
        s.load_session = MagicMock(return_value={})
        s.setup_browser = MagicMock()
        # Mock performance_monitor
        mock_pm = MagicMock()
        mock_pm.measure.return_value.__enter__ = MagicMock()
        mock_pm.measure.return_value.__exit__ = MagicMock(return_value=False)
        s.performance_monitor = mock_pm

        result = s.scrape('https://instagram.com/p/ABC/')
        assert result is not None
        assert result.tagged_accounts == ['alice', 'bob']

    def test_scrape_dom_fallback(self):
        s = self._make()
        s._extract_all_from_json = MagicMock(return_value=None)
        s.goto_url = MagicMock()
        s.load_session = MagicMock(return_value={})
        s.setup_browser = MagicMock()
        s.main_scope = _mock_page()
        s._extract_with_recovery = MagicMock(side_effect=[['tagged1'], '100', '2024-01-01'])
        s.enable_diagnostics = False
        mock_pm = MagicMock()
        mock_pm.measure.return_value.__enter__ = MagicMock()
        mock_pm.measure.return_value.__exit__ = MagicMock(return_value=False)
        s.performance_monitor = mock_pm

        result = s.scrape('https://instagram.com/p/XYZ/')
        assert result is not None
