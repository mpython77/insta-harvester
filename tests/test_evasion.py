"""Tests for evasion subsystem: EvasionConfig, EvasionManager, and adapters."""

from __future__ import annotations

import pytest

from instaharvest.core.exceptions import ConfigError
from instaharvest.evasion.captcha_adapter import CaptchaAdapter
from instaharvest.evasion.config import EvasionConfig
from instaharvest.evasion.facade import EvasionManager
from instaharvest.evasion.multi_session import MultiSessionAdapter
from instaharvest.evasion.stealth_adapter import StealthAdapter

from .conftest import FakeLogger


class TestEvasionConfig:
    def test_default_disabled(self):
        cfg = EvasionConfig()
        assert cfg.enabled is False

    def test_rejects_sub_without_enabled(self):
        """stealth_enabled=True without enabled=True -> ValueError."""
        with pytest.raises(ValueError, match="enabled=False"):
            EvasionConfig(stealth_enabled=True)

    def test_rejects_captcha_key_without_enabled(self):
        """captcha_api_key set without enabled -> ValueError."""
        with pytest.raises(ValueError, match="enabled=False"):
            EvasionConfig(captcha_api_key="some_key")

    def test_rejects_multi_session_without_enabled(self):
        """multi_session_enabled without enabled -> ValueError."""
        with pytest.raises(ValueError, match="enabled=False"):
            EvasionConfig(multi_session_enabled=True)

    def test_valid_when_enabled(self):
        """enabled=True + stealth_enabled=True -> no error."""
        cfg = EvasionConfig(enabled=True, stealth_enabled=True)
        assert cfg.enabled is True
        assert cfg.stealth_enabled is True


class TestEvasionManager:
    def test_enabled_property(self):
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert mgr.enabled is True

    def test_disabled_property(self):
        cfg = EvasionConfig()
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert mgr.enabled is False

    def test_lazy_stealth(self):
        """Accessing .stealth returns StealthAdapter."""
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert isinstance(mgr.stealth, StealthAdapter)

    def test_lazy_captcha(self):
        """Accessing .captcha returns CaptchaAdapter."""
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert isinstance(mgr.captcha, CaptchaAdapter)

    def test_lazy_multi_session(self):
        """Accessing .multi_session returns MultiSessionAdapter."""
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert isinstance(mgr.multi_session, MultiSessionAdapter)

    def test_stealth_cached(self):
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert mgr.stealth is mgr.stealth

    def test_captcha_cached(self):
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert mgr.captcha is mgr.captcha

    def test_multi_session_cached(self):
        cfg = EvasionConfig(enabled=True)
        mgr = EvasionManager(config=cfg, logger=FakeLogger())
        assert mgr.multi_session is mgr.multi_session


class TestAdapterGuards:
    def test_stealth_adapter_guard_raises(self):
        """stealth_enabled=False -> ConfigError on apply_to_context."""
        cfg = EvasionConfig(enabled=True, stealth_enabled=False)
        adapter = StealthAdapter(config=cfg, logger=FakeLogger())
        with pytest.raises(ConfigError):
            adapter.apply_to_context(None)

    def test_captcha_adapter_guard_raises(self):
        """captcha_api_key=None -> ConfigError on detect."""
        cfg = EvasionConfig(enabled=True)
        adapter = CaptchaAdapter(config=cfg, logger=FakeLogger())
        with pytest.raises(ConfigError):
            adapter.detect(None)

    def test_multi_session_adapter_guard_raises(self):
        """multi_session_enabled=False -> ConfigError on get_session."""
        cfg = EvasionConfig(enabled=True, multi_session_enabled=False)
        adapter = MultiSessionAdapter(config=cfg, logger=FakeLogger())
        with pytest.raises(ConfigError):
            adapter.get_session()
