# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.5] - 2025-11-23

### Fixed
- **CRITICAL**: Fixed post link extraction stopping at ~46 posts (was collecting only 46/90 posts)
- Optimized `_aggressive_scroll()` in PostLinksScraper to match ReelLinksScraper's proven approach
- Simplified 3-stage scroll to single-stage fast scroll for better Instagram container loading
- Increased `MAX_NO_NEW` from 5 to 7 attempts for better coverage of slow-loading content
- Increased max scroll attempts from config limit to 150 (matching ReelLinksScraper)
- Improved scroll timing: replaced multi-stage delays with optimized `scroll_content_load_delay`

### Technical Details
- PostLinksScraper now uses same scrolling strategy as ReelLinksScraper (which collects all reels successfully)
- Removed over-engineered 3-stage scroll that caused Instagram to miss containers
- Better handling of Instagram's `div._ac7v.x1ty9z65.xzboxd6` virtual scrolling containers
- More patient waiting for slow network/lazy loading (7 attempts vs 5)

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
