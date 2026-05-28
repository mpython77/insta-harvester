"""Tests for the v3 config split."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from instaharvest import (
    BrowserConfig,
    NetworkConfig,
    OutputConfig,
    RateLimitConfig,
    Settings,
    StealthConfig,
)


class TestSettings:
    def test_default_composes_all_subconfigs(self):
        s = Settings.default()
        assert isinstance(s.browser, BrowserConfig)
        assert isinstance(s.network, NetworkConfig)
        assert isinstance(s.stealth, StealthConfig)
        assert isinstance(s.rate_limit, RateLimitConfig)
        assert isinstance(s.output, OutputConfig)

    def test_settings_is_frozen(self):
        s = Settings.default()
        with pytest.raises(FrozenInstanceError):
            s.browser = BrowserConfig(headless=False)  # type: ignore[misc]

    def test_replace_yields_new_settings(self):
        s = Settings.default()
        new_browser = replace(s.browser, headless=False)
        s2 = replace(s, browser=new_browser)
        assert s2.browser.headless is False
        assert s.browser.headless is True  # original unchanged


class TestBrowserConfig:
    def test_default_is_headless_chrome(self):
        c = BrowserConfig()
        assert c.headless is True
        assert c.channel == "chrome"

    def test_invalid_viewport_rejected(self):
        with pytest.raises(ValueError, match="viewport dimensions"):
            BrowserConfig(viewport_width=0)

    def test_invalid_channel_rejected(self):
        with pytest.raises(ValueError, match="unsupported channel"):
            BrowserConfig(channel="firefox")

    def test_negative_timeout_rejected(self):
        with pytest.raises(ValueError, match="timeouts"):
            BrowserConfig(default_timeout_ms=-1)


class TestNetworkConfig:
    def test_default_has_no_proxy(self):
        c = NetworkConfig()
        assert c.proxy_url is None
        assert c.proxy_pool == ()

    def test_negative_retries_rejected(self):
        with pytest.raises(ValueError, match="max_retries"):
            NetworkConfig(max_retries=-1)

    def test_zero_timeout_rejected(self):
        with pytest.raises(ValueError, match="timeouts"):
            NetworkConfig(connect_timeout=0)


class TestStealthConfig:
    def test_default_is_off(self):
        c = StealthConfig()
        assert c.enabled is False
        assert c.mask_webgl is False

    def test_submask_without_enabled_rejected(self):
        # Setting any submask while enabled=False is a configuration mistake.
        with pytest.raises(ValueError, match="submasks set but enabled=False"):
            StealthConfig(enabled=False, mask_webgl=True)

    def test_enabled_with_submasks_ok(self):
        c = StealthConfig(enabled=True, mask_webgl=True, humanize_typing=True)
        assert c.mask_webgl is True


class TestRateLimitConfig:
    def test_swap_min_max_rejected(self):
        with pytest.raises(ValueError, match="request_delay_max must be >="):
            RateLimitConfig(request_delay_min=5, request_delay_max=1)

    def test_negative_cooldown_rejected(self):
        with pytest.raises(ValueError, match="cooldown_seconds"):
            RateLimitConfig(cooldown_seconds=-1)


class TestOutputConfig:
    def test_empty_session_filename_rejected(self):
        with pytest.raises(ValueError, match="session_filename"):
            OutputConfig(session_filename="")

    def test_negative_indent_rejected(self):
        with pytest.raises(ValueError, match="json_indent"):
            OutputConfig(json_indent=-1)
