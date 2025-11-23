# Release Template for InstaHarvest

Use this template when creating a new release on GitHub.

## Release Title Format

```
v{VERSION} - {SHORT_DESCRIPTION}
```

Examples:
- `v2.5.1 - Bug Fixes and Documentation Improvements`
- `v2.6.0 - New CSV Export Feature`
- `v3.0.0 - Major API Redesign`

---

## Release Description Template

```markdown
## 🎉 InstaHarvest v{VERSION}

{Brief overview of the release - 1-2 sentences}

---

### ✨ Highlights

{List 3-5 most important changes}

- 🔥 **Feature Name**: Brief description
- 🐛 **Bug Fix**: What was fixed
- 📝 **Documentation**: What improved

---

### 📋 Full Changelog

See [CHANGELOG.md](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md) for complete details.

#### Added
- New feature 1
- New feature 2

#### Changed
- Updated behavior 1
- Improved performance 2

#### Fixed
- Bug fix 1
- Bug fix 2

#### Removed
- Deprecated feature 1

---

### 📦 Installation

**From PyPI (Recommended):**
```bash
pip install --upgrade instaharvest
```

**From Source:**
```bash
git clone https://github.com/mpython77/insta-harvester.git
cd insta-harvester
git checkout v{VERSION}
pip install -e .
```

---

### 🔄 Upgrading from Previous Version

**Breaking Changes:** {YES/NO}

{If yes, list breaking changes and migration guide}

**Migration Steps:**
1. Step 1
2. Step 2

---

### 📚 Documentation

- 📖 [README](https://github.com/mpython77/insta-harvester#readme)
- 📋 [Full Changelog](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md)
- 🤝 [Contributing Guide](https://github.com/mpython77/insta-harvester/blob/main/CONTRIBUTING.md)
- ⚙️ [Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md)

---

### 🙏 Contributors

Thank you to everyone who contributed to this release:

- @username1 - Feature/fix description
- @username2 - Feature/fix description

{Or use GitHub's auto-generated contributor list}

---

### 🐛 Known Issues

{List any known issues or limitations in this release}

- Issue 1: Description and workaround
- Issue 2: Description and workaround

---

### 📊 Stats

- **Commits**: {number}
- **Files Changed**: {number}
- **Contributors**: {number}

---

**Full Changelog**: https://github.com/mpython77/insta-harvester/compare/v{PREVIOUS}...v{VERSION}

```

---

## Example: v2.5.1 Release

```markdown
## 🎉 InstaHarvest v2.5.1

Bug fixes, documentation improvements, and repository cleanup for better developer experience.

---

### ✨ Highlights

- 🐛 **Critical Fix**: Resolved unfollow popup timing issue that caused "Could not unfollow" errors
- 📝 **Documentation**: Added CHANGELOG.md and CONTRIBUTING.md for professional open-source standards
- 🧹 **Cleanup**: Removed outdated files and organized repository structure

---

### 📋 Full Changelog

See [CHANGELOG.md](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md) for complete details.

#### Added
- Comprehensive CHANGELOG.md following Keep a Changelog format
- CONTRIBUTING.md with development guidelines
- Professional badges to README.md (PyPI version, downloads, stars)
- ScraperConfig examples in all documentation

#### Changed
- Updated author name to Doston across all files
- Improved README.md header with quick navigation links
- Enhanced markdown formatting across documentation

#### Fixed
- **CRITICAL**: Fixed unfollow popup timing in all_in_one.py
  - Increased popup_open_delay to 3.0 seconds
  - Increased button_click_delay to 3.0 seconds
- Fixed SharedBrowser.start() headless parameter override bug
- Fixed setup.py non-existent CLI entry point
- Corrected 14+ documentation references to deleted files

#### Removed
- INSTALL_UZ.md (contained outdated paths)
- PYPI_UPLOAD_GUIDE.md (maintainer-only documentation)

---

### 📦 Installation

**From PyPI (Recommended):**
```bash
pip install --upgrade instaharvest
```

**Verify installation:**
```bash
python -c "import instaharvest; print(instaharvest.__version__)"
# Should output: 2.5.1
```

---

### 🔄 Upgrading from v2.5.0

**Breaking Changes:** NO

This is a patch release with bug fixes and documentation improvements. No code changes required.

Simply upgrade:
```bash
pip install --upgrade instaharvest
```

---

### 📚 Documentation

- 📖 [README](https://github.com/mpython77/insta-harvester#readme)
- 📋 [Changelog](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md)
- 🤝 [Contributing](https://github.com/mpython77/insta-harvester/blob/main/CONTRIBUTING.md)
- ⚙️ [Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md)

---

### 🙏 Contributors

Thank you @mpython77 for maintaining this release!

---

### 📊 Stats

- **Commits**: 12
- **Files Changed**: 15
- **Contributors**: 1

---

**Full Changelog**: https://github.com/mpython77/insta-harvester/compare/v2.5.0...v2.5.1
```

---

## How to Create a Release on GitHub

1. **Go to Releases**: https://github.com/mpython77/insta-harvester/releases
2. **Click "Draft a new release"**
3. **Choose tag**: Select existing tag or create new one (e.g., `v2.5.1`)
4. **Release title**: Use format above
5. **Description**: Copy template and fill in details
6. **Publish release**

---

## Checklist Before Release

- [ ] Version bumped in setup.py
- [ ] Version bumped in instaharvest/__init__.py
- [ ] CHANGELOG.md updated
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Git tag created
- [ ] PyPI package uploaded
- [ ] GitHub release created
