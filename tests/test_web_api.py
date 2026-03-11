"""
Unit Tests — Instagram Web API Module (Full 16+ endpoints)
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pytest
from dataclasses import asdict


# ══════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════

class TestWebProfileData:
    def test_defaults(self):
        from instaharvest.web_api import WebProfileData
        p = WebProfileData()
        assert p.username == '' and p.follower_count == 0
        assert p.is_verified is False and p._raw == {}

    def test_full(self):
        from instaharvest.web_api import WebProfileData
        p = WebProfileData(username='test', follower_count=1000000, is_verified=True, is_business_account=True)
        assert p.is_business is True
        assert p.has_business_contact is False
        d = p.to_dict()
        assert '_raw' not in d
        json.loads(p.to_json())

    def test_business_contact(self):
        from instaharvest.web_api import WebProfileData
        assert WebProfileData(business_email='a@b.com').has_business_contact is True
        assert WebProfileData(business_phone='+1').has_business_contact is True


class TestFollowUserItem:
    def test_defaults(self):
        from instaharvest.web_api import FollowUserItem
        f = FollowUserItem()
        assert f.username == '' and f.user_id == ''
        json.dumps(f.to_dict())

    def test_full(self):
        from instaharvest.web_api import FollowUserItem
        f = FollowUserItem(username='user1', user_id='123', is_verified=True)
        assert f.is_verified is True


class TestFollowListResult:
    def test_empty(self):
        from instaharvest.web_api import FollowListResult
        r = FollowListResult()
        assert r.users == [] and r.has_more is False
        json.dumps(r.to_dict())

    def test_with_users(self):
        from instaharvest.web_api import FollowListResult, FollowUserItem
        r = FollowListResult(users=[FollowUserItem(username='a')], next_max_id='abc', has_more=True)
        assert len(r.users) == 1 and r.has_more is True


class TestFriendshipStatus:
    def test_defaults(self):
        from instaharvest.web_api import FriendshipStatus
        s = FriendshipStatus()
        assert s.following is False and s.followed_by is False
        json.dumps(s.to_dict())

    def test_full(self):
        from instaharvest.web_api import FriendshipStatus
        s = FriendshipStatus(following=True, followed_by=True, user_id='123')
        assert s.following is True


class TestFeedPost:
    def test_defaults(self):
        from instaharvest.web_api import FeedPost
        p = FeedPost()
        assert p.media_id == '' and p.like_count == 0
        json.dumps(p.to_dict())

    def test_full(self):
        from instaharvest.web_api import FeedPost
        p = FeedPost(media_id='123', shortcode='ABC', like_count=500, is_video=True)
        assert p.is_video is True


class TestMediaInfo:
    def test_defaults(self):
        from instaharvest.web_api import MediaInfo
        m = MediaInfo()
        assert m.media_id == '' and '_raw' not in m.to_dict()

    def test_full(self):
        from instaharvest.web_api import MediaInfo
        m = MediaInfo(media_id='1', like_count=100, play_count=5000, _raw={'key': 'value'})
        d = m.to_dict()
        assert '_raw' not in d


class TestCommentItem:
    def test_full(self):
        from instaharvest.web_api import CommentItem
        c = CommentItem(comment_id='1', text='Nice!', username='user', like_count=5)
        assert c.text == 'Nice!'
        json.dumps(c.to_dict())


class TestCommentsResult:
    def test_empty(self):
        from instaharvest.web_api import CommentsResult
        r = CommentsResult()
        assert r.comments == [] and r.has_more is False
        json.dumps(r.to_dict())


class TestLikersResult:
    def test_empty(self):
        from instaharvest.web_api import LikersResult, LikerItem
        r = LikersResult(likers=[LikerItem(username='a')], total_count=1)
        assert r.total_count == 1
        json.dumps(r.to_dict())


class TestStoryMediaItem:
    def test_defaults(self):
        from instaharvest.web_api import StoryMediaItem
        s = StoryMediaItem()
        assert s.story_id == '' and s.has_audio is False
        json.dumps(s.to_dict())


class TestHighlightsResult:
    def test_empty(self):
        from instaharvest.web_api import HighlightsResult, HighlightInfo
        r = HighlightsResult(highlights=[HighlightInfo(title='Summer')], total_count=1)
        assert r.highlights[0].title == 'Summer'
        json.dumps(r.to_dict())


class TestReelsResult:
    def test_empty(self):
        from instaharvest.web_api import ReelsResult, ReelItem
        r = ReelsResult(reels=[ReelItem(shortcode='ABC', play_count=10000)])
        assert r.reels[0].play_count == 10000
        json.dumps(r.to_dict())


class TestHashtagSection:
    def test_defaults(self):
        from instaharvest.web_api import HashtagSection
        h = HashtagSection(tag_name='fashion')
        assert h.tag_name == 'fashion'
        json.dumps(h.to_dict())


class TestLocationSection:
    def test_defaults(self):
        from instaharvest.web_api import LocationSection
        l = LocationSection(location_id='123', location_name='NYC')
        assert l.location_name == 'NYC'
        json.dumps(l.to_dict())


# ══════════════════════════════════════════════════════
# API CLIENT
# ══════════════════════════════════════════════════════

class TestInstagramWebAPI:
    def test_init(self):
        from instaharvest.web_api import InstagramWebAPI
        api = InstagramWebAPI()
        assert api.page is None and api.request_count == 0
        assert '❌' in repr(api)

    def test_constants(self):
        from instaharvest.web_api import InstagramWebAPI
        assert InstagramWebAPI.IG_APP_ID == '936619743392459'
        assert 'instagram.com/api/v1' in InstagramWebAPI.BASE_API

    def test_build_fetch_js(self):
        from instaharvest.web_api import InstagramWebAPI
        js = InstagramWebAPI()._build_fetch_js('https://test.com/api')
        assert 'fetch(' in js and 'X-CSRFToken' in js and '936619743392459' in js

    def test_no_page_returns_none(self):
        from instaharvest.web_api import InstagramWebAPI
        api = InstagramWebAPI()
        assert api.get_profile('x') is None
        assert api.get_user_info('1') is None
        assert api.get_media_info('1') is None
        assert api.fetch_raw('/test') is None

    def test_no_page_returns_empty(self):
        from instaharvest.web_api import InstagramWebAPI
        api = InstagramWebAPI()
        assert api.search('x').total_found == 0
        assert api.get_followers('1').users == []
        assert api.get_following('1').users == []
        assert api.get_user_feed('1').posts == []
        assert api.get_media_comments('1').comments == []
        assert api.get_media_likers('1').total_count == 0
        assert api.get_stories('1') == []
        assert api.get_highlights('1').total_count == 0
        assert api.get_reels('1').reels == []
        assert api.get_hashtag_feed('test').posts == []
        assert api.get_location_feed('1').posts == []
        assert api.get_tagged_posts('1').posts == []

    def test_friendship_no_page(self):
        from instaharvest.web_api import InstagramWebAPI
        s = InstagramWebAPI().get_friendship_status('123')
        assert s.user_id == '123' and s.following is False

    def test_parse_profile(self):
        from instaharvest.web_api import InstagramWebAPI
        api = InstagramWebAPI()
        p = api._parse_profile({
            'username': 'test', 'id': '1', 'edge_followed_by': {'count': 1000},
            'edge_follow': {'count': 50}, 'edge_owner_to_timeline_media': {'count': 100},
            'is_verified': True, 'business_address_json': '{"city_name": "NY"}'
        })
        assert p.follower_count == 1000 and p.business_address['city_name'] == 'NY'

    def test_parse_follow_list(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_follow_list({
            'users': [{'username': 'a', 'pk': 1}, {'username': 'b', 'pk': 2}],
            'next_max_id': 'xyz'
        })
        assert len(r.users) == 2 and r.has_more is True

    def test_parse_friendship(self):
        from instaharvest.web_api import InstagramWebAPI
        s = InstagramWebAPI()._parse_friendship({'following': True, 'followed_by': False}, '1')
        assert s.following is True and s.followed_by is False

    def test_parse_user_feed(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_user_feed({
            'items': [{'pk': '1', 'code': 'ABC', 'media_type': 1, 'caption': {'text': 'Hello'}, 'like_count': 50, 'image_versions2': {'candidates': [{'url': 'http://img.jpg'}]}, 'user': {'username': 'owner', 'pk': '99'}}],
            'next_max_id': 'next1', 'more_available': True
        })
        assert len(r.posts) == 1 and r.posts[0].like_count == 50 and r.has_more is True

    def test_parse_comments(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_comments({
            'comments': [{'pk': '1', 'text': 'Great!', 'user': {'username': 'u1', 'pk': '10'}, 'created_at': 1000, 'comment_like_count': 3}],
            'next_min_id': 'min1', 'has_more_comments': True
        })
        assert len(r.comments) == 1 and r.comments[0].text == 'Great!' and r.has_more is True

    def test_parse_likers(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_likers({
            'users': [{'username': 'liker1', 'pk': '5', 'is_verified': True}], 'user_count': 100
        })
        assert r.total_count == 100 and r.likers[0].is_verified is True

    def test_parse_highlights(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_highlights({
            'tray': [{'id': 'h1', 'title': 'Summer', 'media_count': 5, 'cover_media': {'cropped_image_version': {'url': 'http://cover.jpg'}}}]
        })
        assert r.total_count == 1 and r.highlights[0].title == 'Summer'

    def test_parse_reels(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_reels({
            'items': [{'media': {'pk': '1', 'code': 'R1', 'play_count': 5000, 'like_count': 100, 'video_versions': [{'url': 'http://v.mp4'}], 'image_versions2': {'candidates': [{'url': 'http://t.jpg'}]}, 'user': {'username': 'u', 'pk': '1'}}}],
            'paging_info': {'max_id': 'p1', 'more_available': True}
        })
        assert len(r.reels) == 1 and r.reels[0].play_count == 5000 and r.has_more is True

    def test_parse_hashtag(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_hashtag('fashion', {
            'sections': [{'layout_content': {'medias': [{'media': {'pk': '1', 'code': 'A', 'like_count': 10}}]}}],
            'next_max_id': 'n1'
        })
        assert r.tag_name == 'fashion' and len(r.posts) == 1

    def test_parse_location(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_location('loc1', {
            'sections': [{'layout_content': {'medias': [{'media': {'pk': '1', 'code': 'B', 'location': {'name': 'NYC'}}}]}}]
        })
        assert r.location_id == 'loc1' and r.location_name == 'NYC'

    def test_parse_search(self):
        from instaharvest.web_api import InstagramWebAPI
        r = InstagramWebAPI()._parse_search_results('q', {'users': [{'user': {'username': 'u1', 'pk': '1', 'follower_count': 500}}]}, 10)
        assert r.total_found == 1 and r.users[0].follower_count == 500


# ══════════════════════════════════════════════════════
# PROFILE DATA EXTENSIONS
# ══════════════════════════════════════════════════════

class TestProfileDataExtended:
    def test_backward_compat(self):
        from instaharvest.profile import ProfileData
        p = ProfileData(username='t', posts=1, followers=1, following=1)
        assert p.data_source == 'dom' and p.full_name is None

    def test_is_business(self):
        from instaharvest.profile import ProfileData
        p = ProfileData(username='t', posts=0, followers=0, following=0, is_business_account=True)
        assert p.is_business is True


# ══════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════

class TestWebAPIError:
    def test_hierarchy(self):
        from instaharvest.exceptions import WebAPIError, InstagramScraperError
        assert issubclass(WebAPIError, InstagramScraperError)
        with pytest.raises(InstagramScraperError): raise WebAPIError("test")


# ══════════════════════════════════════════════════════
# IMPORTS
# ══════════════════════════════════════════════════════

class TestImports:
    def test_all_importable(self):
        from instaharvest import (
            InstagramWebAPI, WebProfileData, WebSearchResult, SearchUserResult,
            WebAPIError, FollowUserItem, FollowListResult, FriendshipStatus,
            FeedPost, UserFeedResult, MediaInfo, CommentItem, CommentsResult,
            LikerItem, LikersResult, StoryMediaItem, StoriesTrayResult,
            ReelItem, ReelsResult, HashtagSection, LocationSection
        )
        # All should be non-None
        for cls in [InstagramWebAPI, WebProfileData, WebSearchResult, SearchUserResult,
                    WebAPIError, FollowUserItem, FollowListResult, FriendshipStatus,
                    FeedPost, UserFeedResult, MediaInfo, CommentItem, CommentsResult,
                    LikerItem, LikersResult, StoryMediaItem, StoriesTrayResult,
                    ReelItem, ReelsResult, HashtagSection, LocationSection]:
            assert cls is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
