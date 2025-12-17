# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.5] - 2025-12-17

### Fixed
- **CRITICAL**: Fixed ProfileScraper opening new browser instead of using SharedBrowser session
- **CRITICAL**: Fixed PostLinksScraper and ReelLinksScraper not working with SharedBrowser
- **CRITICAL**: Fixed bio extraction not working with Instagram's new HTML structure
- Enhanced login detection with 4-layer verification (URL, UI elements, form detection, page title)
- Added automatic session recovery when login page is detected
- Bio extraction now uses 3 strategies for maximum reliability (new span structure, external links, fallback)

### Added
- SharedBrowser support for PostLinksScraper and ReelLinksScraper
- `scrape_post_links()` method to SharedBrowser
- `scrape_reel_links()` method to SharedBrowser
- Options 10 and 11 to all_in_one.py example (post/reel link scraping)
- New bio selectors: `selector_profile_bio_text`, `selector_profile_bio_links`, `selector_profile_header`
- Multi-strategy bio extraction (bio text + external links + fallback)

### Changed
- All scrapers now detect SharedBrowser mode and reuse existing browser session
- Login detection now checks navigation UI elements before concluding session expired
- ProfileScraper, PostLinksScraper, and ReelLinksScraper only close browser in standalone mode
- Bio extraction completely rewritten to support Instagram's updated HTML structure

### Technical Details
- **Browser session handling**: All scrapers check `self.page is not None and self.browser is not None` to detect SharedBrowser mode
- **Login detection improvements**:
  - Method 1: URL check (`/accounts/login/`)
  - Method 2: Navigation UI elements (nav bar, Direct messages icon)
  - Method 3: Login form detection
  - Method 4: Page title check
- **Session recovery**: Automatically visits Instagram home to reactivate session before retrying
- **Bio extraction strategies**:
  - Strategy 1: Extract from `span._ap3a._aaco._aacu._aacx._aad7._aade[dir="auto"]`
  - Strategy 2: Extract links from `div.html-div`
  - Strategy 3: Fallback to old `section.xqui205.x172qv1o` selector
- **SharedBrowser properties**: Added `post_links_scraper` and `reel_links_scraper` lazy-loaded properties

## [2.5.4] - 2025-11-23

### Fixed
- **CRITICAL**: Fixed post link extraction stopping at ~46 posts (was collecting only 46/90 posts)
- **CRITICAL**: Added intelligent waiting for Instagram's lazy-loaded containers
- **CRITICAL**: Removed ALL hardcoded values - now fully configurable via config.py
- Optimized `_aggressive_scroll()` in PostLinksScraper with smart container detection
- Simplified 3-stage scroll to single-stage fast scroll for better Instagram container loading

### Changed
- `_aggressive_scroll()` now monitors container count and waits up to 5 seconds for new containers to load
- **ULTRA GRADUAL SCROLL**: Adaptive scrolling - 5 containers from end (or 2 if < 10 containers)
- Scroll waits intelligently: checks every 0.5s if new containers appeared (instead of fixed 0.8s delay)
- Better handling of slow internet: won't move to next scroll until containers load or 5s timeout
- Fallback: Medium 600px scroll if no new containers appear after 5s (increased from 300px)
- **INFO-level logging**: Scroll progress now visible in INFO logs (not just DEBUG)
- **ALL values now in config.py**: No more hardcoded numbers in code!

### Technical Details
- PostLinksScraper now uses same scrolling strategy as ReelLinksScraper (which collects all reels successfully)
- Removed over-engineered 3-stage scroll that caused Instagram to miss containers
- **NEW**: Intelligent waiting loop - checks `div._ac7v.x1ty9z65.xzboxd6` count before/after scroll
- **NEW**: Adaptive timing - fast networks load in 0.5-1s, slow networks get full 5s to load
- **NEW**: Adaptive gradual scrolling - offset = 5 for >10 containers, offset = 2 for ≤10 containers
- **NEW**: Larger fallback scroll - 600px instead of 300px for better unsticking
- **NEW**: 10 new config parameters added to config.py (scroll behavior section):
  * `scroll_container_wait_timeout` (5.0s)
  * `scroll_container_check_interval` (0.5s)
  * `scroll_container_stability_wait` (0.5s)
  * `scroll_adaptive_offset_small` (2)
  * `scroll_adaptive_offset_large` (5)
  * `scroll_adaptive_threshold` (10)
  * `scroll_fallback_pixels` (600)
  * `scroll_fallback_wait` (1.5s)
  * `scroll_max_no_new_attempts` (7)
  * `scroll_max_attempts_override` (150)
- Prevents overshooting: Even smaller scroll distances help Instagram load ALL content
- More patient waiting for slow network/lazy loading (7 attempts vs 5)
- Enhanced logging: Container positions and scroll actions visible in INFO level
- **ZERO hardcoded values**: All magic numbers moved to config for easy tuning

## [2.5.4] - 2025-11-23

### Fixed
- **CRITICAL BUG**: Fixed `NameError: name 'self' is not defined` in parallel scraper worker processes
- Fixed incorrect `self.config` references in module-level functions (`_extract_reel_tags`, `_extract_tags_robust`, `_worker_scrape_batch`)
- Added proper `config` parameter to helper functions used in multiprocessing workers
- Extended `config_dict` serialization to include all necessary timing parameters:
  - `popup_animation_delay`
  - `popup_content_load_delay`
  - `error_recovery_delay_min`
  - `error_recovery_delay_max`
  - `post_open_delay`
  - `ui_element_load_delay`
- Parallel scraping now works correctly without runtime errors

### Technical Details
- Worker functions in multiprocessing pool cannot access `self` since they run in separate processes
- All helper functions now properly receive and use `config` parameter instead of `self.config`
- This fix affects `parallel_scraper.py` lines 47, 48, 261, 329, 330

## [2.5.3] - 2024-11-23

### Added
- **Session utilities module** (`instaharvest/session_utils.py`)
- `save_session()` function - Create Instagram session from anywhere after pip install
- `check_session_exists()` function - Check if session file exists
- `load_session_data()` function - Load session data from file
- `get_default_session_path()` function - Get standard session file location
- Session management now built into the library (no need for external scripts)

### Changed
- Session saving is now part of the main library API
- Users can now create sessions with: `from instaharvest import save_session; save_session()`
- Session file defaults to current working directory for portability
- Improved session setup documentation

### Fixed
- **CRITICAL**: Users installing via `pip install instaharvest` can now create sessions without cloning repository
- Resolved issue where session creation required access to examples directory
- Session utilities now accessible from any Python environment

## [2.5.2] - 2024-11-23

### Added
- Collapsible sections in README.md using HTML `<details>` tags
- Improved documentation navigation with expandable/collapsible content sections
- Better user experience for PyPI package page

### Changed
- README.md restructured with dropdown sections for Installation, Setup Guide, Examples, Documentation
- All major documentation sections now collapsible for compact viewing
- Enhanced README readability and organization

### Fixed
- PyPI documentation links changed from relative to absolute GitHub URLs
- CONTRIBUTING.md, CHANGELOG.md, and CONFIGURATION_GUIDE.md links now work on PyPI
- Documentation accessibility improved for PyPI users

## [2.5.1] - 2024-11-23

### Added
- CHANGELOG.md with complete version history
- CONTRIBUTING.md with contribution guidelines
- SECURITY.md with proper vulnerability reporting process
- Professional badges and quick navigation in README.md
- ScraperConfig examples in all documentation
- Git tag v2.5.1 for version tracking

### Changed
- **BREAKING**: Updated author name from "Artem" to "Doston"
- Improved all README.md examples to consistently use ScraperConfig
- Enhanced markdown formatting across all documentation files
- Consolidated configuration documentation into single CONFIGURATION_GUIDE.md

### Fixed
- **CRITICAL**: Fixed unfollow popup timing issue in all_in_one.py
  - Added ScraperConfig with popup_open_delay=3.0 seconds
  - Added button_click_delay=3.0 seconds
  - Resolves "Could not unfollow" errors caused by Instagram popup delays
- Fixed SharedBrowser.start() headless parameter default override bug
- Fixed setup.py non-existent CLI entry point that caused installation errors
- Corrected 14+ documentation references to deleted example files
- Fixed markdown code block formatting in examples/README.md

### Removed
- INSTALL_UZ.md (contained outdated paths and wrong repository names)
- PYPI_UPLOAD_GUIDE.md (maintainer-only documentation)
- CONFIGURATION_EXPLAINED.md (consolidated into CONFIGURATION_GUIDE.md)
- tests/ directory (not needed for end users)
- Redundant horizontal rules in README.md
- Trailing whitespace from documentation files

### Documentation
- Added ScraperConfig to all 18+ code examples across documentation
- Updated SECURITY.md with actual project information and contact details
- Improved examples/README.md with proper ScraperConfig usage patterns
- Added prominent warning about always using ScraperConfig for reliability
- Consolidated all configuration documentation into single comprehensive guide

## [2.5.0] - 2024-11-22

### Added
- Session management utilities
- Comprehensive configuration system with ScraperConfig
- Excel export functionality with real-time writing
- Parallel post scraping with multiprocessing
- Shared browser context for efficient operation reuse
- Follow/unfollow management with rate limiting
- Direct messaging functionality
- Followers/following collection
- Professional logging system
- HTML structure change detection

### Changed
- Refactored entire codebase for better modularity
- Improved error handling and recovery
- Enhanced rate limiting to prevent Instagram blocks
- Better session management and auto-refresh

### Fixed
- Multiple timing and synchronization issues
- Instagram popup handling
- Rate limiting edge cases
