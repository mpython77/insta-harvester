# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.4] - 2024-11-23

### Fixed
- **CRITICAL**: Fixed "name 'self' is not defined" error in parallel scraper
- Fixed `_extract_reel_tags()` function - now correctly receives config parameter
- Fixed `_extract_tags_robust()` function - now correctly receives config parameter
- Fixed timing delays in worker functions to use passed config instead of self.config
- Parallel scraping with multiple workers now works correctly without errors

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
- Initial stable release
- Complete Instagram automation toolkit
- SharedBrowser for efficient multi-operation workflows
- Follow/Unfollow functionality with popup handling
- Direct messaging capabilities
- Followers/Following collection with rate limiting
- Profile scraping with comprehensive data extraction
- Post and Reel data scraping
- Excel export functionality
- Parallel processing support
- Session management with persistent authentication
- Comprehensive configuration system via ScraperConfig

### Features
- **FollowManager**: Follow and unfollow Instagram users
- **MessageManager**: Send direct messages programmatically
- **FollowersCollector**: Collect followers and following lists
- **ProfileScraper**: Extract detailed profile information
- **PostDataScraper**: Scrape post metadata and content
- **ReelDataScraper**: Extract Reel information
- **SharedBrowser**: Single browser instance for multiple operations
- **ExcelExporter**: Export data to formatted Excel files
- **ParallelPostDataScraper**: Multi-threaded scraping support

### Configuration
- 40+ configurable parameters via ScraperConfig dataclass
- Customizable delays and timeouts
- Browser viewport settings
- Headless/headed mode support
- User agent customization
- Rate limiting controls

### Documentation
- Comprehensive README.md with usage examples
- CONFIGURATION_GUIDE.md with all parameters explained
- CONFIGURATION_EXPLAINED.md with beginner-friendly explanations
- Example scripts in examples/ directory
- MIT License

### Technical
- Built on Playwright for reliable browser automation
- Synchronous API for simplicity
- Python 3.8+ support
- Modern Instagram div[role="button"] selector support
- Robust error handling with custom exceptions
- Logging support with configurable levels

---

## Version History Summary

- **2.5.1** - Bug fixes, documentation improvements, repository cleanup
- **2.5.0** - Initial stable release with full feature set

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
