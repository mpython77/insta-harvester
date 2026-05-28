# InstaHarvest — Target Architecture (v3)

> **Status:** Migration in progress (Strangler Fig pattern).
> Legacy modules at `instaharvest/*.py` continue to work.
> New code lives under `instaharvest/_v3/` and is the supported path going forward.

---

## 1. Why a refactor?

The legacy codebase (v2.x) accumulated a number of structural problems that a
new feature can no longer paper over:

| Smell | Where | Why it matters |
|---|---|---|
| God-config | `config.py` (296 fields) | Trial-and-error tuning leaked into the public API. Every scraper touches the same mutable bag. |
| God-classes | `shared_browser.py` (70 methods), `orchestrator.py` (`scrape_complete_profile_advanced` with 9+ flags) | Cohesion is gone; behavior is impossible to test in isolation. |
| Multiple HTTP stacks | Playwright + `curl_cffi` + `requests` + `yt-dlp` internal | Cookie sync bugs, four sources of truth for "what is a session". |
| Async = copy-paste | `async_engine.py` duplicates ~80% of `BaseScraper` | Divergence between sync/async is guaranteed. |
| Silent excepts | 148 `except Exception:`, 59 bare `except:` | Bugs are swallowed in production. |
| `/tmp` cookie leak | `downloader._create_cookie_file_from_session` | Live Instagram cookies left readable in `/tmp` after every video download. |
| Aspirational dead code | `core.InstaHarvest` | Documented as the central hub; no scraper ever calls it. |
| Test padding | `tests/test_deep_coverage*.py` (16 files, ~10K LOC) | High coverage number, near-zero behavioral signal. |

Rather than continue piling features onto this, we are building a clean
foundation in `instaharvest/_v3/` and migrating one component at a time.

---

## 2. Design principles

1. **Small focused configs over one god-config.** Each subsystem owns its own
   dataclass. There is a top-level `Settings` that composes them, but no
   subsystem reaches across boundaries.
2. **One HTTP stack.** All non-browser HTTP goes through a single
   `HttpClient` (curl_cffi). Browser work goes through a single
   `BrowserSession`. There is no third option.
3. **Adapters at the edges, pure logic in the middle.** Scrapers depend on
   *protocols* (`HttpClient`, `BrowserSession`, `SessionStore`,
   `Logger`), not on Playwright or curl directly. Tests inject fakes
   instead of mocking module internals.
4. **Sync and async share a core.** Parsing, URL building, validation,
   data models — all sync, all framework-free. Only the I/O shell differs
   between sync and async scrapers.
5. **No silent excepts.** Every `except` either re-raises a domain
   exception or logs at `WARNING` with structured context.
6. **Sessions are sensitive.** Session data is owned by `SessionStore`,
   which is responsible for path resolution, atomic writes, optional
   encryption, and *cleanup of any temp files*. Callers never write
   cookies to disk directly.
7. **No emoji in production logs.** Logs are structured (`key=value`)
   so they can be grepped, filtered, and shipped to log aggregators.
8. **Honest documentation.** Versions, dates, and supported features
   match `setup.py`, `__init__.py`, and `git log`. No fabricated
   changelog entries.

---

## 3. Layered architecture

```
+-------------------------------------------------------------+
|                     instaharvest._v3.facade                 |
|       InstaHarvest — single user-facing entry point         |
+-------------------------------------------------------------+
                           |
+-------------------------------------------------------------+
|                  instaharvest._v3.scrapers                  |
|   ProfileScraper, PostScraper, ...  (one job per class)     |
+-------------------------------------------------------------+
                           |
+-------------------------------------------------------------+
|                   instaharvest._v3.core                     |
|   exceptions, models, protocols  (no I/O, no frameworks)    |
+-------------------------------------------------------------+
                           |
+-------------------------------------------------------------+
|              instaharvest._v3.infrastructure                |
|   HttpClient, BrowserSession, SessionStore, Logger          |
|   (the only modules allowed to import Playwright/curl_cffi) |
+-------------------------------------------------------------+
                           |
+-------------------------------------------------------------+
|                 instaharvest._v3.config                     |
|  BrowserConfig, NetworkConfig, StealthConfig, ..., Settings |
+-------------------------------------------------------------+
```

Imports may go **down only**. `core` may not import `infrastructure`.
`config` may not import anything from the package.

---

## 4. Package layout

```
instaharvest/
├── _v3/
│   ├── __init__.py                  # Public re-exports for v3
│   ├── facade.py                    # InstaHarvest (real central hub)
│   │
│   ├── config/
│   │   ├── __init__.py              # Settings.default(), composition
│   │   ├── browser.py               # BrowserConfig
│   │   ├── network.py               # NetworkConfig (proxy, timeouts, retries)
│   │   ├── stealth.py               # StealthConfig
│   │   ├── rate_limit.py            # RateLimitConfig
│   │   ├── output.py                # OutputConfig (export paths)
│   │   ├── selectors.py             # SelectorConfig (Instagram-specific CSS)
│   │   └── settings.py              # Settings (composes all above)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py            # InstaHarvestError + typed subclasses
│   │   ├── models.py                # Pydantic data models
│   │   └── protocols.py             # HttpClient, BrowserSession, SessionStore, Logger
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── http.py                  # CurlHttpClient (the single HTTP stack)
│   │   ├── browser.py               # PlaywrightBrowserSession
│   │   ├── session.py               # FileSessionStore (atomic writes, optional encryption)
│   │   └── logger.py                # StructuredLogger (no emoji, key=value)
│   │
│   └── scrapers/
│       ├── __init__.py
│       ├── base.py                  # AbstractScraper (uses protocols only)
│       └── profile.py               # ProfileScraper (reference implementation)
│
│   ├── evasion/
│   │   ├── __init__.py              # Opt-in re-exports
│   │   ├── config.py                # EvasionConfig (frozen dataclass)
│   │   ├── facade.py                # EvasionManager
│   │   ├── stealth_adapter.py       # StealthAdapter wraps legacy stealth.py
│   │   ├── captcha_adapter.py       # CaptchaAdapter wraps legacy captcha_solver.py
│   │   └── multi_session.py         # MultiSessionAdapter wraps legacy session_manager.py
│
├── (legacy modules — kept until migrated)
└── __init__.py                      # Exports both v3 and legacy
```

---

## 5. Migration plan

| Phase | What moves to v3 | What stays in legacy |
|---|---|---|
| **1 (shipped)** | Foundation: config, core, infrastructure, ProfileScraper, facade | Everything else |
| **2 (shipped)** | MediaScraper (posts + reels — Instagram models them with the same JSON shape, so they share one scraper), CommentScraper | Followers, follow, message, etc. |
| **3 (shipped)** | FollowersScraper (read-only), Actions namespace (opt-in follow/unfollow/DM with dry-run on by default) | Hashtag, location, search, explore |
| **4 (shipped)** | HashtagScraper, LocationScraper, SearchScraper, ExploreScraper — all API-only, all reusing the shared `paginate_feed` helper | Highlights, stories |
| **5 (shipped)** | StoryScraper, HighlightScraper, NotificationsScraper, opt-in evasion package (stealth + CAPTCHA + multi-session) | Web API |
| **6** | Web API (single source for JSON-first reads) | — |
| **Cleanup** | Delete legacy modules, remove `_v3` namespace prefix | — |

Each phase ships independently. `instaharvest.__init__` always re-exports
both, with a one-line deprecation note for legacy paths. The public API
in `instaharvest._v3` is stable from phase 1 onward — only the *internal*
implementation grows.

---

## 6. What this refactor does NOT change

- **The library is still scoped to Instagram automation.** This refactor
  improves engineering quality; it does not turn it into a different
  product.
- **Legal/ethical posture.** Stealth, captcha-bypass, and multi-account
  rotation are still in the legacy tree. They are *not* migrated to v3
  by default — using them remains the operator's choice and risk.
  Phase 5 will move them into an opt-in `instaharvest._v3.evasion`
  subpackage so they can be excluded from a build.
- **Backwards compatibility for one major version.** v2.x imports keep
  working until v4.0.0.

---

## 7. How to use v3 (preview)

```python
from dataclasses import replace
from instaharvest._v3 import InstaHarvest, Settings

settings = Settings.default()
settings = replace(settings, browser=replace(settings.browser, headless=True))

with InstaHarvest(settings) as ih:
    profile = ih.profile.scrape("instagram")
    print(profile.followers, profile.is_verified)

    # Phase 2 — posts and reels share one scraper
    media = ih.media.scrape("https://www.instagram.com/p/ABC1234/")
    print(media.kind, media.like_count)        # MediaKind.IMAGE  4521

    reel = ih.media.scrape("https://www.instagram.com/reel/XYZ4567/")
    print(reel.kind, reel.video_duration)      # MediaKind.REEL   12.5

    # Phase 2 — comments with replies, fully paginated
    page = ih.comments.scrape(media, max_comments=200, include_replies=True)
    for c in page.comments:
        print(f"@{c.author.username}: {c.text}")

    # Phase 3 — followers list (read-only, always available)
    followers = ih.followers.list_followers(profile.user_id, max_users=100)
    print(f"{followers.total_returned} followers")

    # Phase 4 — discovery surfaces (hashtag, location, search, explore)
    h = ih.hashtag.lookup("fashionweek")
    print(h.name, h.formatted_media_count)         # fashionweek 1.2M

    feed = ih.hashtag.recent("fashionweek", max_items=50)
    print(feed.total_returned, feed.has_more)      # 50  True

    loc = ih.location.lookup(213385402)
    print(loc.name, loc.media_count)

    hits = ih.search.search("fashion week")
    print(len(hits.users), len(hits.hashtags), len(hits.places))

    explore_feed = ih.explore.feed(max_items=30)

    # Phase 5 — stories, highlights, notifications
    stories = ih.stories.get_stories(["12345678"])
    for slide in stories.slides:
        print(slide.media_type, slide.image_url)

    highlights = ih.highlights.list_highlights("12345678")
    for h in highlights.highlights:
        slides = ih.highlights.get_highlight(h.pk)
        print(f"{h.title}: {len(slides)} slides")

    activity = ih.notifications.feed(max_items=20)
    for n in activity.notifications:
        print(f"{n.notification_type.value}: {n.text}")

    # Phase 5 — evasion (opt-in, disabled by default)
    # settings = replace(settings, evasion=EvasionConfig(
    #     enabled=True, stealth_enabled=True,
    # ))

    # Phase 3 — write operations (opt-in!)
    # By default ih.actions raises ConfigError. To enable:
    #
    # settings = replace(settings, actions=replace(
    #     settings.actions, enabled=True, dry_run=False,
    # ))
    #
    # And only THEN:
    # result = ih.actions.follow("instagram")
    # print(result.status, result.message)
```

No god-config. No 70-method facade. No four HTTP stacks. One way in,
one way out — and write operations require *explicit* opt-in.
