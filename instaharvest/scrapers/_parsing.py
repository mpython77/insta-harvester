"""
Pure parsing helpers used by media/comments scrapers.

Everything here is framework-free, side-effect-free, and unit-testable
without touching the network or the filesystem. The leading underscore
on the module name signals "internal" — these helpers are not part of
the public API.

Contents:

    * :func:`extract_shortcode`     — pull the shortcode out of a URL
    * :func:`is_valid_shortcode`    — Instagram shortcode shape check
    * :func:`build_media_url`       — shortcode -> canonical URL
    * :func:`extract_mentions`      — ``@user`` mentions in caption text
    * :func:`extract_hashtags`      — ``#tag`` mentions in caption text
    * :func:`parse_count`           — ``"1.2K"`` / ``"12,345"`` -> int
    * :func:`infer_media_kind`      — Instagram's ``media_type`` /
                                      ``product_type`` -> ``MediaKind``
"""

from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

from instaharvest.core.models import MediaKind


# ---------------------------------------------------------------------------
# Shortcodes
# ---------------------------------------------------------------------------

# Shortcodes are url-safe base64. Instagram has used 11-character codes for
# years, but reels/posts/igtv have at times used different lengths, so we
# accept anything in the 5..16 range to avoid false negatives.
_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_\-]{5,16}$")

# Recognises ``/p/<code>/``, ``/reel/<code>/``, ``/tv/<code>/`` (legacy IGTV).
_URL_SHORTCODE_RE = re.compile(r"/(?:p|reel|tv)/([A-Za-z0-9_\-]{5,16})/?")


def is_valid_shortcode(value: str) -> bool:
    """Return ``True`` if ``value`` looks like a valid Instagram shortcode."""
    return isinstance(value, str) and bool(_SHORTCODE_RE.match(value))


def extract_shortcode(url_or_shortcode: str) -> str:
    """Accept either a full URL or a bare shortcode; return the shortcode.

    Raises:
        ValueError: ``url_or_shortcode`` is neither a recognised URL nor
            a valid shortcode.
    """
    if not isinstance(url_or_shortcode, str):
        raise ValueError(f"expected str, got {type(url_or_shortcode).__name__}")

    candidate = url_or_shortcode.strip()
    if not candidate:
        raise ValueError("empty url_or_shortcode")

    # Bare shortcode?
    if is_valid_shortcode(candidate):
        return candidate

    # Otherwise parse as URL.
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"not a recognised URL or shortcode: {url_or_shortcode!r}")

    match = _URL_SHORTCODE_RE.search(parsed.path)
    if not match:
        raise ValueError(f"no /p/, /reel/, or /tv/ segment in {url_or_shortcode!r}")
    return match.group(1)


def build_media_url(shortcode: str, *, kind: Optional[MediaKind] = None) -> str:
    """Return the canonical instagram.com URL for a shortcode.

    ``kind`` only affects which path segment we use:

      * :attr:`MediaKind.REEL` -> ``/reel/<code>/``
      * everything else        -> ``/p/<code>/``

    (Both URLs resolve on Instagram, but using the right one keeps logs
    and bug reports honest.)
    """
    if not is_valid_shortcode(shortcode):
        raise ValueError(f"invalid shortcode: {shortcode!r}")
    segment = "reel" if kind == MediaKind.REEL else "p"
    return f"https://www.instagram.com/{segment}/{shortcode}/"


# ---------------------------------------------------------------------------
# Caption text
# ---------------------------------------------------------------------------


_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_.])@([A-Za-z0-9_.]{1,30})")
_HASHTAG_RE = re.compile(r"(?<![A-Za-z0-9_])#([A-Za-z0-9_]{1,100})")


def extract_mentions(text: Optional[str]) -> List[str]:
    """Return every ``@username`` mentioned in ``text``, deduplicated, in order."""
    if not text:
        return []
    seen: set = set()
    out: List[str] = []
    for match in _MENTION_RE.finditer(text):
        username = match.group(1).lower()
        if username not in seen:
            seen.add(username)
            out.append(username)
    return out


def extract_hashtags(text: Optional[str]) -> List[str]:
    """Return every ``#hashtag`` in ``text``, deduplicated, in order, lowercased."""
    if not text:
        return []
    seen: set = set()
    out: List[str] = []
    for match in _HASHTAG_RE.finditer(text):
        tag = match.group(1).lower()
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------

_NUMBER_SUFFIXES = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
_COUNT_RE = re.compile(r"^\s*([0-9][0-9,. ]*)\s*([a-zA-Z]?)\s*$")


def parse_count(raw: Optional[str]) -> int:
    """Parse Instagram's rendered counts (``"12,345"``, ``"1.2k"``, ``"3M"``).

    Returns ``0`` for unparseable input. Strict callers should validate
    before calling — this function is a recovery helper, not a guard.
    """
    if raw is None:
        return 0
    match = _COUNT_RE.match(raw)
    if not match:
        return 0
    digits, suffix = match.groups()
    digits = digits.replace(",", "").replace(" ", "")
    try:
        if suffix:
            return int(float(digits) * _NUMBER_SUFFIXES.get(suffix.lower(), 1))
        if "." in digits:
            return int(float(digits))
        return int(digits)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# MediaKind inference
# ---------------------------------------------------------------------------


def infer_media_kind(
    *,
    media_type: Optional[int],
    product_type: Optional[str] = None,
) -> MediaKind:
    """Map Instagram's ``media_type`` + ``product_type`` to :class:`MediaKind`.

    Rules (precedence top to bottom):

      1. ``product_type == "clips"`` -> :attr:`MediaKind.REEL`
         (regardless of ``media_type``, because reels are always videos
         and we always prefer the more specific kind).
      2. ``media_type == 8``         -> :attr:`MediaKind.CAROUSEL`
      3. ``media_type == 2``         -> :attr:`MediaKind.VIDEO`
      4. ``media_type == 1``         -> :attr:`MediaKind.IMAGE`
      5. otherwise                   -> :attr:`MediaKind.IMAGE` (safest default)
    """
    if product_type and product_type.lower() == "clips":
        return MediaKind.REEL
    if media_type == 8:
        return MediaKind.CAROUSEL
    if media_type == 2:
        return MediaKind.VIDEO
    return MediaKind.IMAGE
