"""Tests for FileSessionStore — including the /tmp cookie-leak fix."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from instaharvest.config.output import OutputConfig
from instaharvest.core.exceptions import SessionNotFoundError
from instaharvest.infrastructure.session import FileSessionStore

from .conftest import FakeLogger


@pytest.fixture
def store(tmp_path: Path) -> FileSessionStore:
    cfg = OutputConfig(session_dir=tmp_path, session_filename="session.json")
    return FileSessionStore(cfg, FakeLogger())


class TestExistsLoadSave:
    def test_does_not_exist_initially(self, store: FileSessionStore):
        assert store.exists() is False

    def test_load_missing_raises(self, store: FileSessionStore):
        with pytest.raises(SessionNotFoundError) as exc_info:
            store.load()
        assert exc_info.value.path == str(store.path)

    def test_round_trip(self, store: FileSessionStore):
        payload = {"cookies": [{"name": "a", "value": "b"}], "origins": []}
        store.save(payload)
        assert store.exists()
        assert store.load() == payload

    def test_save_creates_directory(self, tmp_path: Path):
        cfg = OutputConfig(
            session_dir=tmp_path / "deep" / "nested",
            session_filename="s.json",
        )
        s = FileSessionStore(cfg, FakeLogger())
        s.save({"cookies": []})
        assert s.exists()


class TestAtomicWrite:
    def test_no_partial_file_on_serializer_failure(self, tmp_path: Path, monkeypatch):
        """If serialization explodes, the destination file must NOT be touched."""
        cfg = OutputConfig(session_dir=tmp_path, session_filename="s.json")
        store = FileSessionStore(cfg, FakeLogger())

        # Pre-write a valid file
        store.save({"version": "v1", "cookies": []})
        original_bytes = store.path.read_bytes()

        # Now make the serializer raise mid-write
        def boom(_self, _data):
            raise RuntimeError("serializer failed")

        monkeypatch.setattr(FileSessionStore, "_serialize", boom)

        with pytest.raises(RuntimeError):
            store.save({"version": "v2", "cookies": []})

        # Original file is intact (atomic write means partial state never replaces it)
        assert store.path.read_bytes() == original_bytes

    def test_no_tmp_leftovers_on_success(self, store: FileSessionStore):
        store.save({"cookies": []})
        # No ``.tmp`` siblings should remain
        siblings = list(store.path.parent.glob("*.tmp"))
        assert siblings == []


class TestTempCookieFile:
    """The bug being prevented: legacy left these in /tmp forever."""

    def _save_session_with_cookies(self, store: FileSessionStore) -> None:
        store.save({
            "cookies": [
                {"name": "sessionid", "value": "abc", "domain": ".instagram.com",
                 "path": "/", "secure": True, "expires": 1700000000},
                {"name": "csrftoken", "value": "def", "domain": ".instagram.com",
                 "path": "/", "secure": True, "expires": 1700000000},
            ]
        })

    def test_path_exists_inside_with(self, store: FileSessionStore):
        self._save_session_with_cookies(store)
        with store.temp_cookie_file() as cf:
            assert os.path.exists(cf.path)
            content = open(cf.path).read()
            # Netscape format markers
            assert "Netscape HTTP Cookie File" in content
            assert "sessionid" in content
            assert "abc" in content

    def test_path_unlinked_after_with(self, store: FileSessionStore):
        self._save_session_with_cookies(store)
        cf = store.temp_cookie_file()
        with cf:
            path = cf.path
            assert os.path.exists(path)
        # FIX VERIFICATION: after exit, the file must be gone.
        assert not os.path.exists(path)

    def test_path_unlinked_even_on_exception(self, store: FileSessionStore):
        """Regression test for the legacy /tmp cookie leak.

        If the caller's body raises, the cookie file must still be removed.
        """
        self._save_session_with_cookies(store)
        cf = store.temp_cookie_file()
        recorded_path = None
        with pytest.raises(RuntimeError):
            with cf:
                recorded_path = cf.path
                assert os.path.exists(recorded_path)
                raise RuntimeError("caller blew up")
        assert recorded_path is not None
        assert not os.path.exists(recorded_path)

    def test_cookies_without_name_skipped(self, store: FileSessionStore):
        store.save({
            "cookies": [
                {"name": "", "value": "garbage"},
                {"name": "real", "value": "v", "domain": ".x.com",
                 "path": "/", "secure": False, "expires": 0},
            ]
        })
        with store.temp_cookie_file() as cf:
            content = open(cf.path).read()
            assert "garbage" not in content
            assert "real" in content
