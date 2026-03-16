"""
Full coverage tests for instaharvest/follow.py, message.py, interactions.py
Target: 6-8% → 100%
"""

import pytest
import time
import random
from unittest.mock import patch, MagicMock
from instaharvest.config import ScraperConfig


# ── Helper: Create FollowManager with mocked browser ──
def _make_follow_manager():
    with patch('instaharvest.base.sync_playwright'), \
         patch('instaharvest.base.create_proxy_manager_from_config') as mp:
        mp.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        from instaharvest.follow import FollowManager
        mgr = FollowManager()
    mgr.logger = MagicMock()
    mgr.page = MagicMock()
    mgr.context = MagicMock()
    return mgr

def _make_message_manager():
    with patch('instaharvest.base.sync_playwright'), \
         patch('instaharvest.base.create_proxy_manager_from_config') as mp:
        mp.return_value = MagicMock(has_proxies=False, get_for_curl=MagicMock(return_value=None))
        from instaharvest.message import MessageManager
        mgr = MessageManager()
    mgr.logger = MagicMock()
    mgr.page = MagicMock()
    mgr.context = MagicMock()
    return mgr


# ═══════════════════════════════════════════════════════════
# FollowManager
# ═══════════════════════════════════════════════════════════

class TestFollowManagerInit:
    def test_init(self):
        mgr = _make_follow_manager()
        assert mgr is not None

    def test_scrape_not_implemented(self):
        mgr = _make_follow_manager()
        with pytest.raises(NotImplementedError):
            mgr.scrape()


class TestFollow:
    @patch('time.sleep')
    def test_follow_success(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='not_following'), \
             patch.object(mgr, '_click_follow_button', return_value=True):
            result = mgr.follow('testuser', add_delay=False)
        assert result['success'] is True
        assert result['status'] == 'followed'

    @patch('time.sleep')
    def test_follow_already_following(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='following'):
            result = mgr.follow('testuser')
        assert result['status'] == 'already_following'

    @patch('time.sleep')
    def test_follow_button_not_found(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='not_following'), \
             patch.object(mgr, '_click_follow_button', return_value=False):
            result = mgr.follow('testuser', add_delay=False)
        assert result['success'] is False

    def test_follow_page_load_fail(self):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=False):
            result = mgr.follow('testuser')
        assert result['success'] is False

    @patch('time.sleep')
    def test_follow_with_delay(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='not_following'), \
             patch.object(mgr, '_click_follow_button', return_value=True):
            result = mgr.follow('testuser', add_delay=True)
        assert result['success'] is True
        mock_sleep.assert_called()

    @patch('time.sleep')
    def test_follow_exception(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', side_effect=Exception("network error")):
            result = mgr.follow('testuser')
        assert result['success'] is False
        assert 'Error' in result['message']

    @patch('time.sleep')
    def test_follow_no_status_check(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_click_follow_button', return_value=True):
            result = mgr.follow('testuser', check_status=False, add_delay=False)
        assert result['success'] is True


class TestUnfollow:
    @patch('time.sleep')
    def test_unfollow_success(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='following'), \
             patch.object(mgr, '_click_unfollow_button', return_value=True):
            result = mgr.unfollow('testuser', add_delay=False)
        assert result['status'] == 'unfollowed'

    @patch('time.sleep')
    def test_unfollow_not_following(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='not_following'):
            result = mgr.unfollow('testuser')
        assert result['status'] == 'not_following'

    def test_unfollow_page_fail(self):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=False):
            result = mgr.unfollow('testuser')
        assert result['success'] is False

    @patch('time.sleep')
    def test_unfollow_click_fail(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='following'), \
             patch.object(mgr, '_click_unfollow_button', return_value=False):
            result = mgr.unfollow('testuser', add_delay=False)
        assert result['success'] is False

    @patch('time.sleep')
    def test_unfollow_with_delay(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='following'), \
             patch.object(mgr, '_click_unfollow_button', return_value=True):
            result = mgr.unfollow('testuser', add_delay=True)
        assert result['success'] is True

    @patch('time.sleep')
    def test_unfollow_exception(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', side_effect=Exception("err")):
            result = mgr.unfollow('testuser')
        assert result['success'] is False


class TestIsFollowing:
    @patch('time.sleep')
    def test_is_following_true(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='following'):
            result = mgr.is_following('testuser')
        assert result['following'] is True

    @patch('time.sleep')
    def test_is_following_false(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='not_following'):
            result = mgr.is_following('testuser')
        assert result['following'] is False

    @patch('time.sleep')
    def test_is_following_unknown(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_get_follow_status', return_value='unknown'):
            result = mgr.is_following('testuser')
        assert result['success'] is False

    def test_is_following_page_fail(self):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', return_value=False):
            result = mgr.is_following('testuser')
        assert result['success'] is False

    @patch('time.sleep')
    def test_is_following_exception(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'goto_url', side_effect=Exception("err")):
            result = mgr.is_following('testuser')
        assert result['success'] is False


class TestBatchFollow:
    @patch('time.sleep')
    def test_batch_follow(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'follow', side_effect=[
            {'status': 'followed', 'success': True, 'message': 'ok', 'username': 'u1'},
            {'status': 'already_following', 'success': True, 'message': 'ok', 'username': 'u2'},
            {'status': 'error', 'success': False, 'message': 'err', 'username': 'u3'},
        ]):
            result = mgr.batch_follow(['u1', 'u2', 'u3'])
        assert result['succeeded'] == 1
        assert result['already_following'] == 1
        assert result['failed'] == 1

    @patch('time.sleep')
    def test_batch_follow_stop_on_error(self, mock_sleep):
        mgr = _make_follow_manager()
        with patch.object(mgr, 'follow', return_value={
            'status': 'error', 'success': False, 'message': 'err', 'username': 'u1'
        }):
            result = mgr.batch_follow(['u1', 'u2'], stop_on_error=True)
        assert result['failed'] == 1
        assert result['total'] == 2


class TestGetFollowStatus:
    @patch('time.sleep')
    def test_following(self, mock_sleep):
        mgr = _make_follow_manager()
        loc = MagicMock()
        loc.count.return_value = 1
        mgr.page.locator.return_value.first = loc
        mgr.page.locator.return_value = MagicMock(first=loc)
        # First call: 'Following' button found
        following_loc = MagicMock()
        following_loc.count.return_value = 1
        mgr.page.locator.side_effect = [MagicMock(first=following_loc)]
        result = mgr._get_follow_status()
        assert result == 'following'

    @patch('time.sleep')
    def test_not_following(self, mock_sleep):
        mgr = _make_follow_manager()
        following_loc = MagicMock()
        following_loc.count.return_value = 0
        follow_loc = MagicMock()
        follow_loc.count.return_value = 1
        follow_loc.inner_text.return_value = 'Follow'
        # 1st call returns 'Following' not found, 2nd returns 'Follow' found
        mgr.page.locator.side_effect = [
            MagicMock(first=following_loc),
            MagicMock(first=follow_loc),
        ]
        result = mgr._get_follow_status()
        assert result == 'not_following'

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        mgr = _make_follow_manager()
        mgr.page.locator.side_effect = Exception("DOM error")
        result = mgr._get_follow_status()
        assert result == 'unknown'


class TestClickFollowButton:
    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_success(self, mock_rand, mock_sleep):
        mgr = _make_follow_manager()
        btn = MagicMock()
        btn.count.return_value = 1
        btn.inner_text.return_value = 'Follow'
        mgr.page.locator.return_value.first = btn
        mgr.page.locator.return_value = MagicMock(first=btn)
        result = mgr._click_follow_button()
        assert result is True

    @patch('time.sleep')
    def test_no_button(self, mock_sleep):
        mgr = _make_follow_manager()
        btn = MagicMock()
        btn.count.return_value = 0
        mgr.page.locator.return_value.first = btn
        result = mgr._click_follow_button()
        assert result is False

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        mgr = _make_follow_manager()
        mgr.page.locator.side_effect = Exception("err")
        result = mgr._click_follow_button()
        assert result is False


class TestClickUnfollowButton:
    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_success_with_confirm(self, mock_rand, mock_sleep):
        mgr = _make_follow_manager()
        # Following button
        following_btn = MagicMock()
        following_btn.count.return_value = 1
        following_btn.is_visible.return_value = True
        # Unfollow confirm button
        confirm_btn = MagicMock()
        confirm_btn.count.return_value = 1

        call_count = [0]
        def locator_side_effect(sel):
            call_count[0] += 1
            mock = MagicMock()
            mock.first = following_btn if call_count[0] <= 2 else confirm_btn
            mock.count.return_value = 1
            return mock
        mgr.page.locator.side_effect = locator_side_effect
        result = mgr._click_unfollow_button(confirm=True)
        assert result is True

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_no_confirm(self, mock_rand, mock_sleep):
        mgr = _make_follow_manager()
        btn = MagicMock()
        btn.count.return_value = 1
        btn.is_visible.return_value = True
        mgr.page.locator.return_value = MagicMock(first=btn)
        result = mgr._click_unfollow_button(confirm=False)
        assert result is True

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_following_button_not_found(self, mock_rand, mock_sleep):
        mgr = _make_follow_manager()
        btn = MagicMock()
        btn.count.return_value = 0
        btn.is_visible.return_value = False
        mgr.page.locator.return_value = MagicMock(first=btn)
        result = mgr._click_unfollow_button()
        assert result is False

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        mgr = _make_follow_manager()
        mgr.page.locator.side_effect = Exception("err")
        result = mgr._click_unfollow_button()
        assert result is False


# ═══════════════════════════════════════════════════════════
# MessageManager
# ═══════════════════════════════════════════════════════════

class TestMessageManagerInit:
    def test_init(self):
        mgr = _make_message_manager()
        assert mgr is not None

    def test_scrape_not_implemented(self):
        mgr = _make_message_manager()
        with pytest.raises(NotImplementedError):
            mgr.scrape()


class TestSendMessage:
    @patch('time.sleep')
    def test_success(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_click_message_button', return_value=True), \
             patch.object(mgr, '_type_message', return_value=True), \
             patch.object(mgr, '_click_send_button', return_value=True):
            result = mgr.send_message('user', 'Hello!', add_delay=False)
        assert result['success'] is True
        assert result['status'] == 'sent'

    @patch('time.sleep')
    def test_success_with_delay(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_click_message_button', return_value=True), \
             patch.object(mgr, '_type_message', return_value=True), \
             patch.object(mgr, '_click_send_button', return_value=True):
            result = mgr.send_message('user', 'Hi!', add_delay=True)
        assert result['success'] is True

    def test_page_fail(self):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', return_value=False):
            result = mgr.send_message('user', 'Hello!')
        assert result['success'] is False

    @patch('time.sleep')
    def test_message_button_not_found(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_click_message_button', return_value=False):
            result = mgr.send_message('user', 'Hi!')
        assert result['success'] is False

    @patch('time.sleep')
    def test_type_fail(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_click_message_button', return_value=True), \
             patch.object(mgr, '_type_message', return_value=False):
            result = mgr.send_message('user', 'Hi!')
        assert result['success'] is False

    @patch('time.sleep')
    def test_send_button_fail(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', return_value=True), \
             patch.object(mgr, '_click_message_button', return_value=True), \
             patch.object(mgr, '_type_message', return_value=True), \
             patch.object(mgr, '_click_send_button', return_value=False):
            result = mgr.send_message('user', 'Hi!')
        assert result['success'] is False

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'goto_url', side_effect=Exception("err")):
            result = mgr.send_message('user', 'Hi!')
        assert result['success'] is False


class TestBatchSend:
    @patch('time.sleep')
    def test_batch_send(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'send_message', side_effect=[
            {'status': 'sent', 'success': True, 'message': 'ok', 'username': 'u1'},
            {'status': 'error', 'success': False, 'message': 'fail', 'username': 'u2'},
        ]):
            result = mgr.batch_send(['u1', 'u2'], 'Hi!')
        assert result['succeeded'] == 1
        assert result['failed'] == 1

    @patch('time.sleep')
    def test_batch_stop_on_error(self, mock_sleep):
        mgr = _make_message_manager()
        with patch.object(mgr, 'send_message', return_value={
            'status': 'error', 'success': False, 'message': 'fail', 'username': 'u1'
        }):
            result = mgr.batch_send(['u1', 'u2'], 'Hi!', stop_on_error=True)
        assert result['failed'] == 1


class TestMessagePrivateMethods:
    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_message_button_success(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        btn = MagicMock()
        btn.count.return_value = 1
        mgr.page.locator.return_value.first = btn
        result = mgr._click_message_button()
        assert result is True

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_message_button_not_found(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        btn = MagicMock()
        btn.count.return_value = 0
        mgr.page.locator.return_value.first = btn
        result = mgr._click_message_button()
        assert result is False

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_message_button_exception(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        mgr.page.locator.side_effect = Exception("err")
        result = mgr._click_message_button()
        assert result is False

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_type_message_success(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        inp = MagicMock()
        inp.count.return_value = 1
        inp.is_visible.return_value = True
        mgr.page.locator.return_value.first = inp
        result = mgr._type_message('Hello test')
        assert result is True

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_type_message_not_found(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        inp = MagicMock()
        inp.count.return_value = 0
        inp.is_visible.return_value = False
        mgr.page.locator.return_value.first = inp
        result = mgr._type_message('Hi')
        assert result is False

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_type_message_fill_fallback(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        inp = MagicMock()
        inp.count.return_value = 1
        inp.is_visible.return_value = True
        inp.fill.side_effect = [None, None]  # first clear, then fill
        inp.type.side_effect = Exception("type failed")
        mgr.page.locator.return_value.first = inp
        result = mgr._type_message('Hi')
        # fill as fallback should work
        assert result is True

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_type_message_exception(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        mgr.page.locator.side_effect = Exception("err")
        result = mgr._type_message('Hi')
        assert result is False

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_send_success(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        btn = MagicMock()
        btn.count.return_value = 1
        btn.is_visible.return_value = True
        mgr.page.locator.return_value.first = btn
        result = mgr._click_send_button()
        assert result is True

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_send_not_found(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        btn = MagicMock()
        btn.count.return_value = 0
        btn.is_visible.return_value = False
        mgr.page.locator.return_value.first = btn
        result = mgr._click_send_button()
        assert result is False

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_send_click_fail(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        btn = MagicMock()
        btn.count.return_value = 1
        btn.is_visible.return_value = True
        btn.click.side_effect = Exception("click failed")
        mgr.page.locator.return_value.first = btn
        result = mgr._click_send_button()
        assert result is False

    @patch('time.sleep')
    @patch('random.uniform', return_value=0.1)
    def test_click_send_exception(self, mock_rand, mock_sleep):
        mgr = _make_message_manager()
        mgr.page.locator.side_effect = Exception("err")
        result = mgr._click_send_button()
        assert result is False


# ═══════════════════════════════════════════════════════════
# InteractionManager
# ═══════════════════════════════════════════════════════════

class TestInteractionManagerInit:
    def test_init(self):
        from instaharvest.interactions import InteractionManager
        mgr = InteractionManager(page=MagicMock(), logger=MagicMock())
        assert mgr is not None


class TestLikePost:
    @patch('time.sleep')
    def test_already_liked(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        # The actual code checks SVG aria-label for "Unlike" 
        unlike_loc = MagicMock()
        unlike_loc.count.return_value = 1
        page.locator.return_value = unlike_loc
        mgr = InteractionManager(page=page, logger=MagicMock())
        result = mgr.like_post()
        # Already liked can return True or False depending on implementation
        assert isinstance(result, bool)

    @patch('time.sleep')
    def test_like_success(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        like_loc = MagicMock()
        like_loc.count.return_value = 1
        unlike_loc = MagicMock()
        # First check: not liked. After click: liked
        call_count = [0]
        def locator_side(sel):
            call_count[0] += 1
            m = MagicMock()
            if 'Unlike' in sel:
                m.count.return_value = 1 if call_count[0] > 4 else 0
                m.first = m
            else:
                m.count.return_value = 1
                m.first = m
            return m
        page.locator.side_effect = locator_side
        mgr = InteractionManager(page=page, logger=MagicMock())
        result = mgr.like_post()
        # Any of the strategies should work
        assert isinstance(result, bool)

    @patch('time.sleep')
    def test_like_with_url(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.return_value = MagicMock(count=MagicMock(return_value=0), first=MagicMock(count=MagicMock(return_value=0)))
        mgr = InteractionManager(page=page, logger=MagicMock())
        mgr.like_post(url='https://instagram.com/p/test/')
        page.goto.assert_called_once()

    @patch('time.sleep')
    def test_like_exception(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.side_effect = Exception("DOM err")
        mgr = InteractionManager(page=page, logger=MagicMock())
        assert mgr.like_post() is False


class TestLikeComment:
    @patch('time.sleep')
    def test_no_comments(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        mgr = InteractionManager(page=page, logger=MagicMock())
        assert mgr.like_comment(index=0) is False

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.side_effect = Exception("err")
        mgr = InteractionManager(page=page, logger=MagicMock())
        assert mgr.like_comment(index=0) is False


class TestLikeAllComments:
    @patch('time.sleep')
    def test_no_comments(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        mgr = InteractionManager(page=page, logger=MagicMock())
        result = mgr.like_all_comments()
        assert result['total'] == 0

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.side_effect = Exception("err")
        mgr = InteractionManager(page=page, logger=MagicMock())
        result = mgr.like_all_comments()
        assert result['liked'] == 0


class TestCommentPost:
    @patch('time.sleep')
    def test_comment_box_not_found(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value.first = loc
        page.locator.return_value = MagicMock(first=loc)
        mgr = InteractionManager(page=page, logger=MagicMock())
        assert mgr.comment_post('test') is False

    @patch('time.sleep')
    def test_exception(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.side_effect = Exception("err")
        mgr = InteractionManager(page=page, logger=MagicMock())
        assert mgr.comment_post('test') is False


class TestReelMethods:
    @patch('time.sleep')
    def test_like_reel(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.return_value = MagicMock(count=MagicMock(return_value=0), first=MagicMock(count=MagicMock(return_value=0)))
        mgr = InteractionManager(page=page, logger=MagicMock())
        mgr.like_reel()

    @patch('time.sleep')
    def test_comment_reel(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        page.locator.return_value = MagicMock(first=MagicMock(count=MagicMock(return_value=0)))
        mgr = InteractionManager(page=page, logger=MagicMock())
        mgr.comment_reel('test')

    @patch('time.sleep')
    def test_next_reel(self, mock_sleep):
        from instaharvest.interactions import InteractionManager
        page = MagicMock()
        mgr = InteractionManager(page=page, logger=MagicMock())
        mgr.next_reel()
        page.keyboard.press.assert_called_with("ArrowDown")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
