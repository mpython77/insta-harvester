"""
InstaHarvest — Comprehensive Unit Test Suite
Tests for: Data models, TaggedPosts, Highlights, Integration points

Architecture:
  - Mock-based: No real browser or Instagram connection needed
  - Grouped by module: dataclasses, scrapers, integration
  - Covers: properties, parsing, edge cases, serialization
  - Run: pytest tests/ -v
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import asdict

# Add library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from instaharvest.config import ScraperConfig
from instaharvest.post_data import PostLocation, PostOwner


# ═══════════════════════════════════════════════════════════
# TAGGED POSTS — Data Model Tests
# ═══════════════════════════════════════════════════════════

class TestTaggedPostData:
    """Tests for TaggedPostData dataclass"""
    
    def setup_method(self):
        from instaharvest.tagged_posts import TaggedPostData
        self.TaggedPostData = TaggedPostData
    
    def test_default_values(self):
        """Default creation with no args"""
        post = self.TaggedPostData()
        assert post.url == ''
        assert post.shortcode == ''
        assert post.pk == ''
        assert post.media_type == 0
        assert post.like_count == 0
        assert post.comment_count == 0
        assert post.tagged_accounts == []
        assert post.owner is None
        assert post.location is None
    
    def test_full_creation(self):
        """Full creation with all fields"""
        owner = PostOwner(username='photographer1', full_name='John Photo')
        location = PostLocation(name='Istanbul', pk='12345')
        
        post = self.TaggedPostData(
            url='https://www.instagram.com/p/ABC123/',
            shortcode='ABC123',
            pk='9999888877776666',
            media_type=1,
            product_type='feed',
            owner=owner,
            like_count=500,
            comment_count=20,
            caption='Beautiful shot!',
            taken_at=1741617000,
            taken_at_human='2025-03-10 15:30:00 UTC',
            location=location,
            tagged_accounts=['brand_a', 'model_b'],
            thumbnail_url='https://example.com/thumb.jpg',
            width=1080,
            height=1350,
        )
        
        assert post.shortcode == 'ABC123'
        assert post.owner.username == 'photographer1'
        assert post.like_count == 500
        assert len(post.tagged_accounts) == 2
        assert post.location.name == 'Istanbul'
    
    def test_is_reel_by_product_type(self):
        """is_reel property — clips type"""
        post = self.TaggedPostData(product_type='clips')
        assert post.is_reel is True
    
    def test_is_reel_by_media_type(self):
        """is_reel property — media_type 2"""
        post = self.TaggedPostData(media_type=2)
        assert post.is_reel is True
    
    def test_is_not_reel(self):
        """is_reel property — regular post"""
        post = self.TaggedPostData(media_type=1, product_type='feed')
        assert post.is_reel is False
    
    def test_is_carousel(self):
        """is_carousel property — media_type 8"""
        post = self.TaggedPostData(media_type=8)
        assert post.is_carousel is True
    
    def test_is_not_carousel(self):
        """is_carousel property — not carousel"""
        post = self.TaggedPostData(media_type=1)
        assert post.is_carousel is False
    
    def test_has_location(self):
        """has_location property — with location"""
        post = self.TaggedPostData(location=PostLocation(name='Paris'))
        assert post.has_location is True
    
    def test_has_no_location(self):
        """has_location property — no location"""
        post = self.TaggedPostData()
        assert post.has_location is False
    
    def test_to_dict(self):
        """Serialization to dict"""
        post = self.TaggedPostData(shortcode='ABC', like_count=42)
        d = post.to_dict()
        assert isinstance(d, dict)
        assert d['shortcode'] == 'ABC'
        assert d['like_count'] == 42
    
    def test_to_dict_json_serializable(self):
        """Dict output must be JSON-serializable"""
        post = self.TaggedPostData(
            shortcode='ABC',
            owner=PostOwner(username='test'),
            tagged_accounts=['a', 'b'],
        )
        json_str = json.dumps(post.to_dict())
        assert 'ABC' in json_str


class TestTaggedPostsResult:
    """Tests for TaggedPostsResult dataclass"""
    
    def setup_method(self):
        from instaharvest.tagged_posts import TaggedPostData, TaggedPostsResult
        self.TaggedPostData = TaggedPostData
        self.TaggedPostsResult = TaggedPostsResult
    
    def test_empty_result(self):
        """Empty result creation"""
        result = self.TaggedPostsResult(username='testuser')
        assert result.username == 'testuser'
        assert result.post_count == 0
        assert result.reel_count == 0
        assert result.unique_taggers == []
    
    def test_post_count(self):
        """post_count property"""
        result = self.TaggedPostsResult(
            tagged_posts=[
                self.TaggedPostData(shortcode='A'),
                self.TaggedPostData(shortcode='B'),
                self.TaggedPostData(shortcode='C'),
            ]
        )
        assert result.post_count == 3
    
    def test_reel_count(self):
        """reel_count — mixed content"""
        result = self.TaggedPostsResult(
            tagged_posts=[
                self.TaggedPostData(product_type='feed'),
                self.TaggedPostData(product_type='clips'),
                self.TaggedPostData(media_type=2),
                self.TaggedPostData(product_type='feed'),
            ]
        )
        assert result.reel_count == 2
    
    def test_unique_taggers(self):
        """unique_taggers — no duplicates"""
        result = self.TaggedPostsResult(
            tagged_posts=[
                self.TaggedPostData(owner=PostOwner(username='alice')),
                self.TaggedPostData(owner=PostOwner(username='bob')),
                self.TaggedPostData(owner=PostOwner(username='alice')),  # dup
                self.TaggedPostData(owner=PostOwner(username='carol')),
            ]
        )
        assert result.unique_taggers == ['alice', 'bob', 'carol']
    
    def test_unique_taggers_with_none_owner(self):
        """unique_taggers handles None owner"""
        result = self.TaggedPostsResult(
            tagged_posts=[
                self.TaggedPostData(owner=PostOwner(username='alice')),
                self.TaggedPostData(owner=None),
                self.TaggedPostData(owner=PostOwner(username='bob')),
            ]
        )
        assert result.unique_taggers == ['alice', 'bob']
    
    def test_to_dict(self):
        """Serialization to dict"""
        result = self.TaggedPostsResult(
            username='testuser',
            total_found=5,
            scrape_time=12.3,
        )
        d = result.to_dict()
        assert d['username'] == 'testuser'
        assert d['total_found'] == 5


# ═══════════════════════════════════════════════════════════
# HIGHLIGHTS — Data Model Tests
# ═══════════════════════════════════════════════════════════

class TestHighlightSticker:
    """Tests for HighlightSticker dataclass"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightSticker
        self.HighlightSticker = HighlightSticker
    
    def test_default(self):
        sticker = self.HighlightSticker()
        assert sticker.sticker_type == ''
        assert sticker.value == ''
        assert sticker.extra == {}
    
    def test_mention_sticker(self):
        sticker = self.HighlightSticker(
            sticker_type='mention',
            value='@tashoakley'
        )
        assert sticker.sticker_type == 'mention'
        assert sticker.value == '@tashoakley'
    
    def test_to_dict(self):
        sticker = self.HighlightSticker(
            sticker_type='link',
            value='https://example.com',
            extra={'display_text': 'Shop Now'}
        )
        d = sticker.to_dict()
        assert d['sticker_type'] == 'link'
        assert d['extra']['display_text'] == 'Shop Now'


class TestHighlightMusic:
    """Tests for HighlightMusic dataclass"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightMusic
        self.HighlightMusic = HighlightMusic
    
    def test_default(self):
        music = self.HighlightMusic()
        assert music.title == ''
        assert music.artist == ''
        assert music.duration_ms == 0
    
    def test_full_music(self):
        music = self.HighlightMusic(
            title='summer vibes',
            artist='DJ Sun',
            album='Beach Collection',
            duration_ms=180000,
            ig_artist='djsun_official'
        )
        assert music.duration_ms == 180000
        assert music.ig_artist == 'djsun_official'
    
    def test_to_dict(self):
        music = self.HighlightMusic(title='test', artist='artist1')
        d = music.to_dict()
        assert d['title'] == 'test'
        assert d['artist'] == 'artist1'


class TestHighlightSlide:
    """Tests for HighlightSlide dataclass"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightSlide, HighlightMusic
        self.HighlightSlide = HighlightSlide
        self.HighlightMusic = HighlightMusic
    
    def test_default(self):
        slide = self.HighlightSlide()
        assert slide.slide_index == 0
        assert slide.media_type == 'image'
        assert slide.mentions == []
        assert slide.link_stickers == []
        assert slide.music is None
    
    def test_image_slide(self):
        slide = self.HighlightSlide(
            slide_index=0,
            pk='123456',
            media_type='image',
            image_url='https://cdn.instagram.com/img.jpg',
            width=1080,
            height=1920,
            taken_at=1741617000,
            taken_at_human='2025-03-10 15:30:00 UTC',
        )
        assert slide.is_video is False
        assert slide.has_music is False
        assert slide.has_mentions is False
        assert slide.has_links is False
    
    def test_video_slide_with_stickers(self):
        slide = self.HighlightSlide(
            slide_index=5,
            media_type='video',
            video_url='https://cdn.instagram.com/vid.mp4',
            mentions=['brand_a', 'model_b'],
            link_stickers=['https://shop.example.com'],
            music=self.HighlightMusic(title='Beat', artist='DJ'),
            hashtag_stickers=['swimwear', 'summer'],
            location_stickers=[{'name': 'Bali', 'pk': '999'}],
        )
        assert slide.is_video is True
        assert slide.has_music is True
        assert slide.has_mentions is True
        assert slide.has_links is True
        assert len(slide.mentions) == 2
        assert len(slide.hashtag_stickers) == 2
    
    def test_to_dict_json_serializable(self):
        """Full slide must be JSON-serializable"""
        slide = self.HighlightSlide(
            pk='123',
            mentions=['a', 'b'],
            music=self.HighlightMusic(title='Song', artist='Art'),
        )
        json_str = json.dumps(slide.to_dict())
        assert '123' in json_str
        assert 'Song' in json_str


class TestHighlightResult:
    """Tests for HighlightResult dataclass"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import (
            HighlightResult, HighlightSlide, HighlightMusic
        )
        self.HighlightResult = HighlightResult
        self.HighlightSlide = HighlightSlide
        self.HighlightMusic = HighlightMusic
    
    def test_empty_result(self):
        result = self.HighlightResult(highlight_id='123')
        assert result.highlight_id == '123'
        assert result.slide_count == 0
        assert result.video_count == 0
        assert result.image_count == 0
        assert result.all_mentions == []
        assert result.all_links == []
        assert result.all_music == []
        assert result.all_locations == []
    
    def test_slide_counts(self):
        """Correctly counts images vs videos"""
        result = self.HighlightResult(
            slides=[
                self.HighlightSlide(media_type='image'),
                self.HighlightSlide(media_type='video'),
                self.HighlightSlide(media_type='image'),
                self.HighlightSlide(media_type='video'),
                self.HighlightSlide(media_type='video'),
            ]
        )
        assert result.slide_count == 5
        assert result.image_count == 2
        assert result.video_count == 3
    
    def test_all_mentions_unique(self):
        """all_mentions returns unique list"""
        result = self.HighlightResult(
            slides=[
                self.HighlightSlide(mentions=['alice', 'bob']),
                self.HighlightSlide(mentions=['bob', 'carol']),
                self.HighlightSlide(mentions=['alice']),
            ]
        )
        assert result.all_mentions == ['alice', 'bob', 'carol']
    
    def test_all_links_unique(self):
        """all_links returns unique list"""
        result = self.HighlightResult(
            slides=[
                self.HighlightSlide(link_stickers=['https://a.com']),
                self.HighlightSlide(link_stickers=['https://a.com', 'https://b.com']),
            ]
        )
        assert result.all_links == ['https://a.com', 'https://b.com']
    
    def test_all_music(self):
        """all_music collects from slides"""
        music1 = self.HighlightMusic(title='Song1')
        music2 = self.HighlightMusic(title='Song2')
        result = self.HighlightResult(
            slides=[
                self.HighlightSlide(music=music1),
                self.HighlightSlide(music=None),
                self.HighlightSlide(music=music2),
            ]
        )
        assert len(result.all_music) == 2
        assert result.all_music[0].title == 'Song1'
        assert result.all_music[1].title == 'Song2'
    
    def test_all_locations(self):
        """all_locations collects across slides"""
        result = self.HighlightResult(
            slides=[
                self.HighlightSlide(location_stickers=[{'name': 'Paris'}]),
                self.HighlightSlide(location_stickers=[]),
                self.HighlightSlide(location_stickers=[{'name': 'London'}]),
            ]
        )
        assert len(result.all_locations) == 2
        assert result.all_locations[0]['name'] == 'Paris'
    
    def test_to_dict(self):
        """Full result to_dict"""
        result = self.HighlightResult(
            highlight_id='999',
            highlight_title='Summer',
            owner_username='testuser',
        )
        d = result.to_dict()
        assert d['highlight_id'] == '999'
        assert d['highlight_title'] == 'Summer'


class TestHighlightInfo:
    """Tests for HighlightInfo dataclass"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightInfo
        self.HighlightInfo = HighlightInfo
    
    def test_default(self):
        info = self.HighlightInfo()
        assert info.highlight_id == ''
        assert info.title == ''
        assert info.url == ''
    
    def test_full_info(self):
        info = self.HighlightInfo(
            highlight_id='18092082532805201',
            title='St Barths',
            url='https://www.instagram.com/stories/highlights/18092082532805201/',
            cover_url='https://cdn.instagram.com/cover.jpg',
        )
        assert info.highlight_id == '18092082532805201'
        assert 'St Barths' == info.title
    
    def test_to_dict(self):
        info = self.HighlightInfo(highlight_id='123', title='Test')
        d = info.to_dict()
        assert d['highlight_id'] == '123'


class TestHighlightsListResult:
    """Tests for HighlightsListResult dataclass"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import (
            HighlightsListResult, HighlightInfo, HighlightResult, HighlightSlide
        )
        self.HighlightsListResult = HighlightsListResult
        self.HighlightInfo = HighlightInfo
        self.HighlightResult = HighlightResult
        self.HighlightSlide = HighlightSlide
    
    def test_empty(self):
        result = self.HighlightsListResult(username='test')
        assert result.username == 'test'
        assert result.total_highlights == 0
        assert result.total_slides == 0
        assert result.all_mentions == []
    
    def test_total_slides_sum(self):
        """total_slides sums across all highlights"""
        result = self.HighlightsListResult(
            username='test',
            full_results=[
                self.HighlightResult(slides=[
                    self.HighlightSlide() for _ in range(10)
                ]),
                self.HighlightResult(slides=[
                    self.HighlightSlide() for _ in range(25)
                ]),
                self.HighlightResult(slides=[
                    self.HighlightSlide() for _ in range(5)
                ]),
            ]
        )
        assert result.total_slides == 40
    
    def test_all_mentions_across_highlights(self):
        """all_mentions unique across all highlights"""
        result = self.HighlightsListResult(
            full_results=[
                self.HighlightResult(slides=[
                    self.HighlightSlide(mentions=['alice', 'bob']),
                ]),
                self.HighlightResult(slides=[
                    self.HighlightSlide(mentions=['bob', 'carol']),
                ]),
            ]
        )
        assert result.all_mentions == ['alice', 'bob', 'carol']
    
    def test_to_dict(self):
        result = self.HighlightsListResult(
            username='test',
            total_highlights=3,
            highlights=[self.HighlightInfo(highlight_id='1')],
        )
        d = result.to_dict()
        assert d['username'] == 'test'
        assert d['total_highlights'] == 3
        assert len(d['highlights']) == 1


# ═══════════════════════════════════════════════════════════
# HIGHLIGHTS SCRAPER — Logic Tests (with mocks)
# ═══════════════════════════════════════════════════════════

class TestHighlightsScraperHelpers:
    """Tests for HighlightsScraper helper methods"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        self.HighlightsScraper = HighlightsScraper
    
    def test_parse_highlight_id_from_url(self):
        """_parse_highlight_id extracts ID from full URL"""
        assert self.HighlightsScraper._parse_highlight_id(
            'https://www.instagram.com/stories/highlights/18092082532805201/'
        ) == '18092082532805201'
    
    def test_parse_highlight_id_plain(self):
        """_parse_highlight_id returns plain ID"""
        assert self.HighlightsScraper._parse_highlight_id('18092082532805201') == '18092082532805201'
    
    def test_parse_highlight_id_trailing_slash(self):
        """_parse_highlight_id strips trailing slash"""
        assert self.HighlightsScraper._parse_highlight_id('18092082532805201/') == '18092082532805201'
    
    def test_parse_highlight_id_with_whitespace(self):
        """_parse_highlight_id strips whitespace"""
        assert self.HighlightsScraper._parse_highlight_id('  18092082532805201  ') == '18092082532805201'


class TestHighlightsScraperItemParser:
    """Tests for _parse_item with real-world-like JSON"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        # Create scraper with mocked dependencies
        with patch.object(HighlightsScraper, '__init__', lambda self, *a, **kw: None):
            self.scraper = HighlightsScraper()
            self.scraper.logger = MagicMock()
            self.scraper.config = ScraperConfig()
    
    def _make_item(self, **overrides):
        """Create a realistic highlight item dict"""
        item = {
            'pk': '3811626841677108001',
            'id': '3811626841677108001_123',
            'code': 'ABC123',
            'media_type': 1,
            'taken_at': 1737064147,
            'original_width': 1080,
            'original_height': 1920,
            'image_versions2': {
                'candidates': [
                    {'url': 'https://cdn.instagram.com/large.jpg', 'width': 1080, 'height': 1920},
                    {'url': 'https://cdn.instagram.com/small.jpg', 'width': 320, 'height': 568},
                ]
            },
            'accessibility_caption': 'Photo of beach',
        }
        item.update(overrides)
        return item
    
    def test_parse_basic_image(self):
        """Parse a basic image item"""
        item = self._make_item()
        slide = self.scraper._parse_item(item, slide_index=0)
        
        assert slide is not None
        assert slide.pk == '3811626841677108001'
        assert slide.media_type == 'image'
        assert slide.width == 1080
        assert slide.height == 1920
        assert 'large.jpg' in slide.image_url
        assert slide.video_url == ''
        assert slide.slide_index == 0
    
    def test_parse_video_item(self):
        """Parse a video item"""
        item = self._make_item(
            media_type=2,
            video_versions=[
                {'url': 'https://cdn.instagram.com/hd.mp4', 'width': 1080, 'height': 1920},
                {'url': 'https://cdn.instagram.com/sd.mp4', 'width': 480, 'height': 852},
            ]
        )
        slide = self.scraper._parse_item(item, slide_index=3)
        
        assert slide.media_type == 'video'
        assert slide.is_video is True
        assert 'hd.mp4' in slide.video_url
        assert slide.slide_index == 3
    
    def test_parse_item_with_mentions(self):
        """Parse item with reel_mentions"""
        item = self._make_item(
            reel_mentions=[
                {'user': {'username': 'alice', 'pk': '111'}},
                {'user': {'username': 'bob', 'pk': '222'}},
            ]
        )
        slide = self.scraper._parse_item(item)
        assert 'alice' in slide.mentions
        assert 'bob' in slide.mentions
    
    def test_parse_item_with_link_stickers(self):
        """Parse item with story_link_stickers"""
        item = self._make_item(
            story_link_stickers=[
                {'url': 'https://shop.example.com', 'display_text': 'Shop'},
            ]
        )
        slide = self.scraper._parse_item(item)
        assert 'https://shop.example.com' in slide.link_stickers
    
    def test_parse_item_with_location(self):
        """Parse item with story_locations"""
        item = self._make_item(
            story_locations=[
                {'location': {
                    'name': 'St Barths Beach',
                    'pk': '216662981',
                    'address': '97133',
                    'city': 'Gustavia',
                    'lat': 17.896,
                    'lng': -62.849,
                }}
            ]
        )
        slide = self.scraper._parse_item(item)
        assert len(slide.location_stickers) == 1
        assert slide.location_stickers[0]['name'] == 'St Barths Beach'
        assert slide.location_stickers[0]['lat'] == 17.896
    
    def test_parse_item_with_music(self):
        """Parse item with music_metadata"""
        item = self._make_item(
            music_metadata={
                'music_info': {
                    'music_asset_info': {
                        'title': 'Summer Breeze',
                        'display_artist': 'DJ Sunset',
                        'sanitized_title': 'summer-breeze',
                        'duration_in_ms': 210000,
                        'ig_username': 'djsunset',
                    }
                }
            }
        )
        slide = self.scraper._parse_item(item)
        assert slide.music is not None
        assert slide.music.title == 'Summer Breeze'
        assert slide.music.artist == 'DJ Sunset'
        assert slide.music.duration_ms == 210000
    
    def test_parse_item_with_hashtags(self):
        """Parse item with story_hashtags"""
        item = self._make_item(
            story_hashtags=[
                {'hashtag': {'name': 'swimwear'}},
                {'hashtag': {'name': 'summer'}},
            ]
        )
        slide = self.scraper._parse_item(item)
        assert 'swimwear' in slide.hashtag_stickers
        assert 'summer' in slide.hashtag_stickers
    
    def test_parse_item_timestamp(self):
        """Parse item timestamp formatting"""
        item = self._make_item(taken_at=1737064147)
        slide = self.scraper._parse_item(item)
        assert slide.taken_at == 1737064147
        assert 'UTC' in slide.taken_at_human
        assert '2025' in slide.taken_at_human
    
    def test_parse_picks_best_image(self):
        """Picks highest resolution image"""
        item = self._make_item(
            image_versions2={
                'candidates': [
                    {'url': 'https://cdn/small.jpg', 'width': 320, 'height': 568},
                    {'url': 'https://cdn/hd.jpg', 'width': 1080, 'height': 1920},
                    {'url': 'https://cdn/med.jpg', 'width': 640, 'height': 1136},
                ]
            }
        )
        slide = self.scraper._parse_item(item)
        assert 'hd.jpg' in slide.image_url
    
    def test_parse_none_input(self):
        """_parse_item handles None"""
        result = self.scraper._parse_item(None)
        assert result is None
    
    def test_parse_invalid_input(self):
        """_parse_item handles non-dict"""
        result = self.scraper._parse_item("not a dict")
        assert result is None
    
    def test_parse_dedup_mentions(self):
        """Mentions are deduplicated within a single item"""
        item = self._make_item(
            reel_mentions=[
                {'user': {'username': 'alice', 'pk': '111'}},
                {'user': {'username': 'alice', 'pk': '111'}},  # dup
            ]
        )
        slide = self.scraper._parse_item(item)
        assert slide.mentions.count('alice') == 1


class TestHighlightsScraperFindItems:
    """Tests for _find_highlight_items JSON parsing"""
    
    def setup_method(self):
        from instaharvest.highlight_scraper import HighlightsScraper
        with patch.object(HighlightsScraper, '__init__', lambda self, *a, **kw: None):
            self.scraper = HighlightsScraper()
            self.scraper.logger = MagicMock()
            self.scraper.config = ScraperConfig()
    
    def test_find_items_direct(self):
        """Find items from direct {items: [...]} structure"""
        data = {
            'title': 'St Barths',
            'user': {'username': 'mondayswimwear', 'pk': '12345'},
            'items': [
                {'pk': '111', 'taken_at': 1737064147},
                {'pk': '222', 'taken_at': 1737064200},
            ]
        }
        items, meta = self.scraper._find_highlight_items(data)
        assert len(items) == 2
        assert meta['title'] == 'St Barths'
        assert meta['owner_username'] == 'mondayswimwear'
    
    def test_find_items_nested_in_reels_media(self):
        """Find items from reels_media[].items[]"""
        data = {
            'reels_media': [
                {
                    'title': 'Greece',
                    'user': {'username': 'user1', 'pk': '999'},
                    'items': [
                        {'pk': '333', 'taken_at': 1},
                    ]
                }
            ]
        }
        items, meta = self.scraper._find_highlight_items(data)
        assert len(items) == 1
        assert meta['title'] == 'Greece'
    
    def test_find_items_deeply_nested(self):
        """Find items buried deep in relay structure"""
        data = {
            'require': [
                [None, None, None, {
                    '__bbox': {
                        'result': {
                            'data': {
                                'some_relay_key': {
                                    'title': 'Nested',
                                    'user': {'username': 'deep', 'pk': '1'},
                                    'items': [
                                        {'pk': '444', 'taken_at': 1},
                                    ]
                                }
                            }
                        }
                    }
                }]
            ]
        }
        items, meta = self.scraper._find_highlight_items(data)
        assert len(items) == 1
        assert meta.get('title') == 'Nested'
    
    def test_find_items_empty(self):
        """Empty JSON returns empty"""
        items, meta = self.scraper._find_highlight_items({})
        assert items == []
        assert meta == {}
    
    def test_find_items_none(self):
        """None input returns empty"""
        items, meta = self.scraper._find_highlight_items(None)
        assert items == []
        assert meta == {}
    
    def test_find_items_ignores_non_story_items(self):
        """Ignores items[] that don't look like story items"""
        data = {
            'items': [
                {'name': 'not a story'},  # no pk or taken_at
            ]
        }
        items, meta = self.scraper._find_highlight_items(data)
        assert len(items) == 0


# ═══════════════════════════════════════════════════════════
# INTEGRATION — Import & Method Tests
# ═══════════════════════════════════════════════════════════

class TestImports:
    """Verify all public imports work"""
    
    def test_tagged_imports(self):
        from instaharvest import TaggedPostsScraper, TaggedPostData, TaggedPostsResult
        assert TaggedPostsScraper is not None
        assert TaggedPostData is not None
        assert TaggedPostsResult is not None
    
    def test_highlight_imports(self):
        from instaharvest import (
            HighlightsScraper, HighlightResult, HighlightSlide,
            HighlightSticker, HighlightMusic, HighlightInfo, HighlightsListResult
        )
        assert HighlightsScraper is not None
        assert HighlightResult is not None
        assert HighlightSlide is not None
        assert HighlightSticker is not None
        assert HighlightMusic is not None
        assert HighlightInfo is not None
        assert HighlightsListResult is not None
    
    def test_all_in_package_all(self):
        """All new classes are in __all__"""
        import instaharvest
        all_list = instaharvest.__all__
        
        expected = [
            'TaggedPostsScraper', 'TaggedPostData', 'TaggedPostsResult',
            'HighlightsScraper', 'HighlightResult', 'HighlightSlide',
            'HighlightSticker', 'HighlightMusic', 'HighlightInfo', 'HighlightsListResult',
        ]
        for name in expected:
            assert name in all_list, f"{name} missing from __all__"


class TestOrchestratorIntegration:
    """Verify orchestrator has all new methods"""
    
    def test_has_scrape_tagged_posts(self):
        from instaharvest import InstagramOrchestrator
        assert hasattr(InstagramOrchestrator, 'scrape_tagged_posts')
    
    def test_has_scrape_highlight(self):
        from instaharvest import InstagramOrchestrator
        assert hasattr(InstagramOrchestrator, 'scrape_highlight')
    
    def test_has_scrape_all_highlights(self):
        from instaharvest import InstagramOrchestrator
        assert hasattr(InstagramOrchestrator, 'scrape_all_highlights')


class TestSharedBrowserIntegration:
    """Verify SharedBrowser has all new methods"""
    
    def test_has_scrape_tagged_posts(self):
        from instaharvest import SharedBrowser
        assert hasattr(SharedBrowser, 'scrape_tagged_posts')
    
    def test_has_scrape_highlight(self):
        from instaharvest import SharedBrowser
        assert hasattr(SharedBrowser, 'scrape_highlight')
    
    def test_has_list_highlights(self):
        from instaharvest import SharedBrowser
        assert hasattr(SharedBrowser, 'list_highlights')
    
    def test_has_scrape_all_highlights(self):
        from instaharvest import SharedBrowser
        assert hasattr(SharedBrowser, 'scrape_all_highlights')


class TestVersionInfo:
    """Verify package metadata"""
    
    def test_version_updated(self):
        import instaharvest
        assert instaharvest.__version__ == '2.15.1'


# ═══════════════════════════════════════════════════════════
# EDGE CASES & ROBUSTNESS
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case scenarios"""
    
    def test_empty_mention_list(self):
        """HighlightResult with slides but no mentions"""
        from instaharvest.highlight_scraper import HighlightResult, HighlightSlide
        result = HighlightResult(slides=[
            HighlightSlide(mentions=[]),
            HighlightSlide(mentions=[]),
        ])
        assert result.all_mentions == []
    
    def test_very_large_slide_count(self):
        """Stress: 500 slides"""
        from instaharvest.highlight_scraper import HighlightResult, HighlightSlide
        slides = [HighlightSlide(pk=str(i), media_type='video' if i % 3 == 0 else 'image')
                  for i in range(500)]
        result = HighlightResult(slides=slides)
        assert result.slide_count == 500
        assert result.video_count == 167
        assert result.image_count == 333
    
    def test_tagged_result_zero_posts(self):
        """Empty tagged result"""
        from instaharvest.tagged_posts import TaggedPostsResult
        result = TaggedPostsResult(username='nobody')
        assert result.post_count == 0
        assert result.reel_count == 0
        assert result.unique_taggers == []
    
    def test_highlight_info_special_chars_in_title(self):
        """Title with emoji and special characters"""
        from instaharvest.highlight_scraper import HighlightInfo
        info = HighlightInfo(
            highlight_id='123',
            title='🏖️ Summer ☀️ Vibes!',
        )
        d = info.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert '🏖️' in json_str
    
    def test_highlights_list_result_json_serializable(self):
        """HighlightsListResult.to_dict() is fully JSON-serializable"""
        from instaharvest.highlight_scraper import (
            HighlightsListResult, HighlightInfo, HighlightResult, HighlightSlide,
            HighlightMusic
        )
        result = HighlightsListResult(
            username='test',
            total_highlights=2,
            highlights=[
                HighlightInfo(highlight_id='1', title='A'),
                HighlightInfo(highlight_id='2', title='B'),
            ],
            full_results=[
                HighlightResult(
                    highlight_id='1',
                    slides=[
                        HighlightSlide(
                            pk='111',
                            mentions=['alice'],
                            music=HighlightMusic(title='Song', artist='Art'),
                            location_stickers=[{'name': 'Paris'}],
                        )
                    ]
                ),
            ]
        )
        d = result.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed['username'] == 'test'
        assert len(parsed['full_results']) == 1
        assert parsed['full_results'][0]['slides'][0]['mentions'] == ['alice']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
