"""
Unit Tests — Core Data Models
Covers: PostLocation, PostOwner, CarouselSlide, PostData, ProfileData, 
        ReelData, StoryItem, StorySlideInfo, StoryResult, 
        NotificationItem, DownloadTask, DownloadResult, BatchResult
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from pathlib import Path
from dataclasses import asdict


# ═══════════════════════════════════════════════════════════
# POST DATA
# ═══════════════════════════════════════════════════════════

class TestPostLocation:
    def test_defaults(self):
        from instaharvest.post_data import PostLocation
        loc = PostLocation()
        assert loc.name == ''
        assert loc.latitude == 0.0
        assert loc.longitude == 0.0

    def test_full(self):
        from instaharvest.post_data import PostLocation
        loc = PostLocation(name='Istanbul', pk='12345', latitude=41.0, longitude=29.0)
        assert loc.name == 'Istanbul'
        d = loc.to_dict()
        assert d['latitude'] == 41.0

    def test_json_serializable(self):
        from instaharvest.post_data import PostLocation
        loc = PostLocation(name='Bali', address='80361')
        json.dumps(loc.to_dict())


class TestPostOwner:
    def test_defaults(self):
        from instaharvest.post_data import PostOwner
        owner = PostOwner()
        assert owner.username == ''
        assert owner.is_verified is False

    def test_full(self):
        from instaharvest.post_data import PostOwner
        owner = PostOwner(
            username='johndoe', full_name='John Doe',
            pk='999', is_verified=True,
            profile_pic_url='https://example.com/pic.jpg'
        )
        assert owner.is_verified is True
        d = owner.to_dict()
        assert d['username'] == 'johndoe'


class TestCarouselSlide:
    def test_defaults(self):
        from instaharvest.post_data import CarouselSlide
        slide = CarouselSlide()
        assert slide.tagged_accounts == []
        assert slide.tag_positions == []
        assert slide.has_tags is False

    def test_with_tags(self):
        from instaharvest.post_data import CarouselSlide
        slide = CarouselSlide(tagged_accounts=['alice', 'bob'])
        assert slide.has_tags is True

    def test_to_dict(self):
        from instaharvest.post_data import CarouselSlide
        slide = CarouselSlide(slide_index=2, media_type='video', width=1080)
        d = slide.to_dict()
        assert d['slide_index'] == 2
        json.dumps(d)


class TestPostData:
    def test_creation(self):
        from instaharvest.post_data import PostData
        post = PostData(url='https://instagram.com/p/ABC/', tagged_accounts=[], likes='100', timestamp='2025-03-10')
        assert post.url.endswith('ABC/')
        assert post.content_type == 'Post'
        assert post.is_video is False

    def test_post_init_defaults(self):
        from instaharvest.post_data import PostData
        post = PostData(url='', tagged_accounts=[], likes='0', timestamp='')
        assert post.media_urls == []
        assert post.tagged_users_per_media == []
        assert post.top_likers == []
        assert post.carousel_slides == []
        assert post.tag_positions == []

    def test_to_dict_json(self):
        from instaharvest.post_data import PostData, PostOwner, PostLocation
        post = PostData(
            url='https://instagram.com/p/XYZ/',
            tagged_accounts=['user1', 'user2'],
            likes='1500',
            timestamp='2025-03-10 15:30:00',
            owner=PostOwner(username='photographer'),
            location=PostLocation(name='Paris'),
            caption='Amazing shot!',
        )
        d = post.to_dict()
        json_str = json.dumps(d)
        assert 'photographer' in json_str
        assert 'Paris' in json_str


# ═══════════════════════════════════════════════════════════
# PROFILE DATA
# ═══════════════════════════════════════════════════════════

class TestProfileData:
    def test_creation(self):
        from instaharvest.profile import ProfileData
        p = ProfileData(username='testuser', posts=100, followers=5000, following=200)
        assert p.username == 'testuser'
        assert p.is_verified is False
        assert p.is_private is False

    def test_engagement_rate(self):
        from instaharvest.profile import ProfileData
        p = ProfileData(username='test', posts=10, followers=1000, following=100)
        rate = p.calculate_engagement_rate(avg_likes=50, avg_comments=5)
        assert rate == 5.5  # (50+5)/1000 * 100
        assert p.engagement_rate == 5.5

    def test_engagement_rate_zero_followers(self):
        from instaharvest.profile import ProfileData
        p = ProfileData(username='test', posts=10, followers=0, following=0)
        rate = p.calculate_engagement_rate(avg_likes=50)
        assert rate == 0.0

    def test_to_dict(self):
        from instaharvest.profile import ProfileData
        p = ProfileData(
            username='test', posts=10, followers=1000,
            following=100, is_verified=True, bio='Hello world',
            external_links=['https://example.com']
        )
        d = p.to_dict()
        assert d['is_verified'] is True
        assert d['bio'] == 'Hello world'
        assert len(d['external_links']) == 1
        json.dumps(d)


# ═══════════════════════════════════════════════════════════
# REEL DATA
# ═══════════════════════════════════════════════════════════

class TestReelData:
    def test_creation(self):
        from instaharvest.reel_data import ReelData
        reel = ReelData(url='https://instagram.com/reel/ABC123/')
        assert reel.content_type == 'Reel'
        assert reel.has_tags is False
        assert reel.has_location is False

    def test_with_tags(self):
        from instaharvest.reel_data import ReelData
        reel = ReelData(url='https://instagram.com/reel/X/', tagged_accounts=['user1'])
        assert reel.has_tags is True

    def test_with_location(self):
        from instaharvest.reel_data import ReelData
        from instaharvest.post_data import PostLocation
        reel = ReelData(url='x', location=PostLocation(name='Tokyo'))
        assert reel.has_location is True

    def test_to_dict_json(self):
        from instaharvest.reel_data import ReelData
        from instaharvest.post_data import PostOwner
        reel = ReelData(
            url='https://instagram.com/reel/X/',
            caption='Check this out!',
            like_count=5000,
            owner=PostOwner(username='creator'),
        )
        d = reel.to_dict()
        json_str = json.dumps(d)
        assert 'creator' in json_str


# ═══════════════════════════════════════════════════════════
# STORY DATA
# ═══════════════════════════════════════════════════════════

class TestStorySlideInfo:
    def test_defaults(self):
        from instaharvest.story_scraper import StorySlideInfo
        s = StorySlideInfo()
        assert s.slide_index == 0
        assert s.media_type == 'unknown'
        assert s.tagged_accounts == []
        assert s.has_tags is False

    def test_with_data(self):
        from instaharvest.story_scraper import StorySlideInfo
        s = StorySlideInfo(slide_index=3, media_type='video', tagged_accounts=['brand'], has_tags=True)
        assert s.has_tags is True
        d = s.to_dict()
        assert d['slide_index'] == 3


class TestStoryItem:
    def test_defaults(self):
        from instaharvest.story_scraper import StoryItem
        item = StoryItem()
        assert item.media_url == ''
        assert item.media_type == 'image'
        assert item.tagged_accounts == []

    def test_full(self):
        from instaharvest.story_scraper import StoryItem
        item = StoryItem(
            media_url='https://cdn.ig/story.jpg',
            media_type='image',
            width=1080, height=1920,
            caption='Story caption',
            tagged_accounts=['friend1', 'friend2']
        )
        d = item.to_dict()
        assert len(d['tagged_accounts']) == 2
        json.dumps(d)


class TestStoryResult:
    def test_empty(self):
        from instaharvest.story_scraper import StoryResult
        r = StoryResult(username='testuser')
        assert r.story_count == 0
        assert r.has_stories is False
        assert r.items == []

    def test_with_items(self):
        from instaharvest.story_scraper import StoryResult, StoryItem
        r = StoryResult(
            username='testuser',
            story_count=2,
            has_stories=True,
            items=[
                StoryItem(media_type='image'),
                StoryItem(media_type='video'),
            ],
            all_tagged_accounts=['alice', 'bob']
        )
        d = r.to_dict()
        assert len(d['items']) == 2
        assert d['has_stories'] is True
        json.dumps(d)


# ═══════════════════════════════════════════════════════════
# NOTIFICATION DATA
# ═══════════════════════════════════════════════════════════

class TestNotificationItem:
    def test_defaults(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem()
        assert n.type == 'other'
        assert n.usernames == []
        assert n.text == ''
        assert n.is_grouped is False

    def test_follow(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(
            type='follow',
            usernames=['alice'],
            text='alice started following you',
            time_text='1d',
            section='Yesterday',
            action_button='Follow Back',
        )
        assert n.type == 'follow'
        assert n.action_button == 'Follow Back'

    def test_grouped(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(
            type='post_like',
            usernames=['alice', 'bob'],
            is_grouped=True,
            extra_count=5,
        )
        assert n.is_grouped is True
        assert n.extra_count == 5

    def test_to_dict(self):
        from instaharvest.notifications import NotificationItem
        n = NotificationItem(
            type='comment_like',
            usernames=['user1'],
            comment_text='Great post! 🔥',
            post_url='/p/ABC123/',
        )
        d = n.to_dict()
        assert d['type'] == 'comment_like'
        assert d['comment_text'] == 'Great post! 🔥'
        json.dumps(d)

    def test_list_isolation(self):
        """Ensure lists are not shared between instances"""
        from instaharvest.notifications import NotificationItem
        n1 = NotificationItem()
        n2 = NotificationItem()
        n1.usernames.append('alice')
        assert 'alice' not in n2.usernames


# ═══════════════════════════════════════════════════════════
# BATCH DOWNLOADER DATA
# ═══════════════════════════════════════════════════════════

class TestDownloadTask:
    def test_creation(self):
        from instaharvest.batch_downloader import DownloadTask
        task = DownloadTask(
            url='https://cdn.ig/image.jpg',
            save_path=Path('/tmp/test.jpg'),
            shortcode='ABC123',
        )
        assert task.url.endswith('image.jpg')
        assert task.media_type == 'image'
        assert 'ABC123' in repr(task)


class TestDownloadResult:
    def test_success(self):
        from instaharvest.batch_downloader import DownloadResult, DownloadTask
        task = DownloadTask(url='x', save_path=Path('/tmp/x.jpg'))
        result = DownloadResult(task=task, success=True, file_size=1024, duration=1.5)
        assert result.success is True
        assert '✅' in repr(result)

    def test_failure(self):
        from instaharvest.batch_downloader import DownloadResult, DownloadTask
        task = DownloadTask(url='x', save_path=Path('/tmp/x.jpg'))
        result = DownloadResult(task=task, success=False, error='Timeout')
        assert '❌' in repr(result)

    def test_format_size(self):
        from instaharvest.batch_downloader import DownloadResult
        assert DownloadResult._format_size(500) == '500B'
        assert DownloadResult._format_size(2048) == '2.0KB'
        assert DownloadResult._format_size(5 * 1024 * 1024) == '5.0MB'


class TestBatchResult:
    def test_empty(self):
        from instaharvest.batch_downloader import BatchResult
        b = BatchResult()
        assert b.success_count == 0
        assert b.failed_count == 0
        assert b.total_bytes == 0
        assert b.duration == 0.0

    def test_counts(self):
        from instaharvest.batch_downloader import BatchResult, DownloadResult, DownloadTask
        task = DownloadTask(url='x', save_path=Path('/tmp/x.jpg'))
        b = BatchResult(
            results=[
                DownloadResult(task=task, success=True, file_size=1000),
                DownloadResult(task=task, success=True, file_size=2000),
                DownloadResult(task=task, success=False, error='err'),
            ],
            total=3,
            start_time=100.0,
            end_time=110.0,
        )
        assert b.success_count == 2
        assert b.failed_count == 1
        assert b.total_bytes == 3000
        assert b.duration == 10.0
        assert b.speed == 300.0

    def test_summary(self):
        from instaharvest.batch_downloader import BatchResult, DownloadResult, DownloadTask
        task = DownloadTask(url='x', save_path=Path('/tmp/x.jpg'))
        b = BatchResult(
            results=[
                DownloadResult(task=task, success=True, file_size=5000),
            ],
            total=1,
            start_time=0.0,
            end_time=2.0,
        )
        s = b.summary()
        assert s['total'] == 1
        assert s['success'] == 1
        assert s['failed'] == 0
        assert isinstance(s['total_size'], str)
        assert len(s['failed_files']) == 0


# ═══════════════════════════════════════════════════════════
# PYDANTIC MODELS (models.py)
# ═══════════════════════════════════════════════════════════

class TestCommentAuthor:
    def test_creation(self):
        from instaharvest.models import CommentAuthor
        a = CommentAuthor(username='testuser')
        assert a.username == 'testuser'
        assert a.is_verified is False
        assert a.profile_url == ''


class TestComment:
    def test_creation(self):
        from instaharvest.models import Comment, CommentAuthor
        c = Comment(
            id='123',
            text='Great post!',
            author=CommentAuthor(username='alice'),
            timestamp='1w',
            timestamp_iso='2025-03-03T12:00:00Z',
        )
        assert c.id == '123'
        assert c.likes_count == 0
        assert c.replies == []
        assert c.is_reply is False

    def test_validate_counts_string(self):
        from instaharvest.models import Comment, CommentAuthor
        c = Comment(
            id='1', text='x',
            author=CommentAuthor(username='x'),
            timestamp='1d', timestamp_iso='2025-01-01',
            likes_count='1,234',
            reply_count='56',
        )
        assert c.likes_count == 1234
        assert c.reply_count == 56

    def test_validate_counts_invalid(self):
        from instaharvest.models import Comment, CommentAuthor
        c = Comment(
            id='1', text='x',
            author=CommentAuthor(username='x'),
            timestamp='1d', timestamp_iso='2025-01-01',
            likes_count='abc',
        )
        assert c.likes_count == 0

    def test_with_replies(self):
        from instaharvest.models import Comment, CommentAuthor
        reply = Comment(
            id='2', text='Thanks!',
            author=CommentAuthor(username='bob'),
            timestamp='5h', timestamp_iso='2025-03-10',
            is_reply=True, parent_id='1',
        )
        parent = Comment(
            id='1', text='Nice shot',
            author=CommentAuthor(username='alice'),
            timestamp='1d', timestamp_iso='2025-03-09',
            replies=[reply],
        )
        assert len(parent.replies) == 1
        assert parent.replies[0].parent_id == '1'

    def test_backward_compat(self):
        from instaharvest.models import Comment, CommentData
        assert Comment is CommentData


class TestCollaborator:
    def test_creation(self):
        from instaharvest.models import Collaborator
        c = Collaborator(username='collab1')
        assert c.username == 'collab1'
        assert c.is_verified is False
        assert c.profile_url == ''


# ═══════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception(self):
        from instaharvest.exceptions import InstagramScraperError
        with pytest.raises(InstagramScraperError):
            raise InstagramScraperError("test error")

    def test_session_not_found(self):
        from instaharvest.exceptions import SessionNotFoundError, InstagramScraperError
        with pytest.raises(InstagramScraperError):
            raise SessionNotFoundError("session missing")

    def test_profile_not_found(self):
        from instaharvest.exceptions import ProfileNotFoundError
        with pytest.raises(ProfileNotFoundError):
            raise ProfileNotFoundError("@nobody not found")

    def test_html_structure_changed(self):
        from instaharvest.exceptions import HTMLStructureChangedError
        e = HTMLStructureChangedError('likes', 'span.likes')
        assert 'likes' in str(e)
        assert e.element_name == 'likes'
        assert e.selector == 'span.likes'

    def test_page_load_error(self):
        from instaharvest.exceptions import PageLoadError
        with pytest.raises(PageLoadError):
            raise PageLoadError("timeout")

    def test_rate_limit_error(self):
        from instaharvest.exceptions import RateLimitError
        with pytest.raises(RateLimitError):
            raise RateLimitError("rate limited")

    def test_login_required_error(self):
        from instaharvest.exceptions import LoginRequiredError
        with pytest.raises(LoginRequiredError):
            raise LoginRequiredError("session expired")

    def test_exception_hierarchy(self):
        """All custom exceptions inherit from InstagramScraperError"""
        from instaharvest.exceptions import (
            InstagramScraperError, SessionNotFoundError,
            ProfileNotFoundError, PageLoadError,
            RateLimitError, LoginRequiredError
        )
        assert issubclass(SessionNotFoundError, InstagramScraperError)
        assert issubclass(ProfileNotFoundError, InstagramScraperError)
        assert issubclass(PageLoadError, InstagramScraperError)
        assert issubclass(RateLimitError, InstagramScraperError)
        assert issubclass(LoginRequiredError, InstagramScraperError)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
