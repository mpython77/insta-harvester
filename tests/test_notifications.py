"""
Unit Tests — NotificationReader Logic (mock-based, no browser)
Covers: _detect_type, _clean_text, filter/summary helpers, GROUPED_PATTERN
"""

import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock
from instaharvest.notifications import NotificationReader, NotificationItem


@pytest.fixture
def reader():
    """Create NotificationReader with mocked page/logger"""
    mock_page = MagicMock()
    mock_logger = MagicMock()
    return NotificationReader(mock_page, mock_logger)


# ═══════════════════════════════════════════════════════════
# TYPE DETECTION
# ═══════════════════════════════════════════════════════════

class TestDetectType:
    """Tests for _detect_type method"""

    def test_comment_like_english(self, reader):
        assert reader._detect_type('alice liked your comment: Great post!') == 'comment_like'

    def test_comment_like_russian(self, reader):
        assert reader._detect_type('Алексею понравился ваш комментарий') == 'comment_like'

    def test_comment_like_uzbek(self, reader):
        assert reader._detect_type('alice kommentingizni yoqtirdi') == 'comment_like'

    def test_post_like_english(self, reader):
        assert reader._detect_type('bob liked your photo') == 'post_like'

    def test_post_like_uzbek(self, reader):
        assert reader._detect_type('bob postingizni yoqtirdi') == 'post_like'

    def test_follow_english(self, reader):
        assert reader._detect_type('alice started following you') == 'follow'

    def test_follow_russian(self, reader):
        assert reader._detect_type('Иван подписался на ваши обновления') == 'follow'

    def test_follow_uzbek(self, reader):
        assert reader._detect_type('ali sizni kuzatishni boshladi') == 'follow'

    def test_follow_turkish(self, reader):
        assert reader._detect_type('ahmet seni takip etmeye başladı') == 'follow'

    def test_comment_english(self, reader):
        assert reader._detect_type('alice commented: Nice!') == 'comment'

    def test_comment_uzbek(self, reader):
        assert reader._detect_type('ali komment yozdi: Ajoyib!') == 'comment'

    def test_mention(self, reader):
        assert reader._detect_type('bob mentioned you in a comment') == 'mention'

    def test_tagged(self, reader):
        assert reader._detect_type('carol tagged you in a post') == 'mention'

    def test_follow_request(self, reader):
        # After pattern ordering fix: follow_request/follow_accepted patterns
        # are now BEFORE the generic 'follow' fallback
        assert reader._detect_type('dave requested to follow you') == 'follow_request'
        # Russian pattern also works:
        assert reader._detect_type('dave запросил подписку') == 'follow_request'

    def test_follow_accepted(self, reader):
        # After pattern ordering fix: follow_accepted correctly detected
        assert reader._detect_type('eve accepted your follow request') == 'follow_accepted'
        assert reader._detect_type('eve принял запрос на подписку') == 'follow_accepted'

    def test_thread(self, reader):
        assert reader._detect_type('frank posted a thread you might like') == 'thread'

    def test_story(self, reader):
        assert reader._detect_type('grace posted a story') == 'story'

    def test_other(self, reader):
        assert reader._detect_type('random text without patterns') == 'other'


# ═══════════════════════════════════════════════════════════
# TEXT CLEANING
# ═══════════════════════════════════════════════════════════

class TestCleanText:
    def test_basic(self, reader):
        assert reader._clean_text('hello world') == 'hello world'

    def test_newlines(self, reader):
        assert reader._clean_text('hello\nworld\nfoo') == 'hello world foo'

    def test_extra_spaces(self, reader):
        assert reader._clean_text('hello    world   bar') == 'hello world bar'

    def test_mixed(self, reader):
        assert reader._clean_text('  hello \n\n  world  \n') == 'hello world'

    def test_empty(self, reader):
        assert reader._clean_text('') == ''

    def test_none(self, reader):
        assert reader._clean_text(None) == ''


# ═══════════════════════════════════════════════════════════
# GROUPED PATTERN
# ═══════════════════════════════════════════════════════════

class TestGroupedPattern:
    def test_match_others(self):
        m = NotificationReader.GROUPED_PATTERN.search('alice and 5 others liked your post')
        assert m is not None
        assert m.group(1) == '5'

    def test_match_other_singular(self):
        m = NotificationReader.GROUPED_PATTERN.search('bob and 1 other liked your comment')
        assert m is not None
        assert m.group(1) == '1'

    def test_no_match(self):
        m = NotificationReader.GROUPED_PATTERN.search('alice liked your post')
        assert m is None


# ═══════════════════════════════════════════════════════════
# FILTER & SUMMARY HELPERS
# ═══════════════════════════════════════════════════════════

class TestFilterHelpers:
    def _make_notifs(self):
        return [
            NotificationItem(type='follow', usernames=['alice'], section='Yesterday'),
            NotificationItem(type='post_like', usernames=['bob'], section='This week'),
            NotificationItem(type='follow', usernames=['carol'], section='Yesterday'),
            NotificationItem(type='comment', usernames=['dave'], section='This week'),
            NotificationItem(type='post_like', usernames=['eve'], section='This month'),
        ]

    def test_filter_by_type(self, reader):
        notifs = self._make_notifs()
        follows = reader.filter_by_type(notifs, 'follow')
        assert len(follows) == 2

    def test_filter_by_section(self, reader):
        notifs = self._make_notifs()
        yesterday = reader.filter_by_section(notifs, 'Yesterday')
        assert len(yesterday) == 2

    def test_filter_by_username(self, reader):
        notifs = self._make_notifs()
        alice_notifs = reader.filter_by_username(notifs, 'alice')
        assert len(alice_notifs) == 1

    def test_summary(self, reader):
        notifs = self._make_notifs()
        s = reader.summary(notifs)
        assert s['total'] == 5
        assert s['by_type']['follow'] == 2
        assert s['by_type']['post_like'] == 2
        assert len(s['unique_users']) == 5

    def test_summary_follow_back(self, reader):
        notifs = [
            NotificationItem(type='follow', usernames=['alice'], action_button='Follow Back'),
            NotificationItem(type='follow', usernames=['bob'], action_button='Following'),
        ]
        s = reader.summary(notifs)
        assert s['has_follow_back'] == ['alice']
        assert s['has_following'] == ['bob']

    def test_to_dicts(self, reader):
        notifs = self._make_notifs()
        dicts = reader.to_dicts(notifs)
        assert isinstance(dicts, list)
        assert all(isinstance(d, dict) for d in dicts)
        assert len(dicts) == 5


# ═══════════════════════════════════════════════════════════
# KNOWN SECTIONS
# ═══════════════════════════════════════════════════════════

class TestKnownSections:
    def test_english_sections(self):
        s = NotificationReader.KNOWN_SECTIONS
        assert 'Yesterday' in s
        assert 'This week' in s
        assert 'This month' in s
        assert 'Earlier' in s

    def test_russian_sections(self):
        s = NotificationReader.KNOWN_SECTIONS
        assert 'Вчера' in s
        assert 'На этой неделе' in s

    def test_turkish_sections(self):
        s = NotificationReader.KNOWN_SECTIONS
        assert 'Dün' in s
        assert 'Bu hafta' in s

    def test_spanish_sections(self):
        s = NotificationReader.KNOWN_SECTIONS
        assert 'Ayer' in s
        assert 'Esta semana' in s


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
