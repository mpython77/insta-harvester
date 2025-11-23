# Contributing to InstaHarvest

First off, thank you for considering contributing to InstaHarvest! 🎉

It's people like you that make InstaHarvest such a great tool. We welcome contributions from everyone, whether it's:

- 🐛 Bug reports
- 💡 Feature requests
- 📝 Documentation improvements
- 🔧 Code contributions
- ✅ Testing and quality assurance

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project and everyone participating in it is governed by common sense and respect. By participating, you are expected to uphold this code. Please report unacceptable behavior to kelajak054@gmail.com.

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/insta-harvester.git
   cd insta-harvester
   ```

3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

---

## How to Contribute

### 🐛 Reporting Bugs

**Before submitting a bug report:**
- Check the [existing issues](https://github.com/mpython77/insta-harvester/issues) to avoid duplicates
- Collect information about the bug:
  - Stack trace / error message
  - Operating system and version
  - Python version
  - InstaHarvest version
  - Steps to reproduce

**Submit a bug report:**
1. Go to [Issues](https://github.com/mpython77/insta-harvester/issues/new)
2. Use the bug report template
3. Provide as much detail as possible
4. Include code samples if applicable

### 💡 Suggesting Features

**Before submitting a feature request:**
- Check if the feature already exists
- Check [existing feature requests](https://github.com/mpython77/insta-harvester/issues?q=is%3Aissue+label%3Aenhancement)
- Clearly describe the use case

**Submit a feature request:**
1. Go to [Issues](https://github.com/mpython77/insta-harvester/issues/new)
2. Use the feature request template
3. Describe the problem you're trying to solve
4. Describe the solution you'd like
5. Include examples if possible

### 📝 Documentation Improvements

Documentation improvements are always welcome! This includes:
- README.md updates
- Code comments
- Configuration guides
- Example scripts
- Fixing typos

Simply submit a pull request with your changes.

---

## Development Setup

### 1. Install Dependencies

```bash
# Install development dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .

# Install Playwright browsers
playwright install chromium
```

### 2. Run Examples

```bash
# Save Instagram session (required once)
python examples/save_session.py

# Test your changes
python examples/all_in_one.py
```

### 3. Test Your Changes

Currently, we use manual testing with example scripts. Automated tests are welcome contributions!

```bash
# Test specific functionality
python tests/test_unfollow_debug.py
```

---

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and small
- Maximum line length: 100 characters

### Configuration Usage

**IMPORTANT:** Always use `ScraperConfig` for timing and delays!

```python
# ✅ CORRECT
from instaharvest.config import ScraperConfig

config = ScraperConfig(
    popup_open_delay=3.0,
    button_click_delay=3.0
)
manager = FollowManager(config=config)

# ❌ WRONG
manager = FollowManager()  # Don't rely on defaults without explicit config
time.sleep(2.5)  # Don't use hardcoded delays
```

### Code Organization

```python
# Standard library imports
import time
import json

# Third-party imports
from playwright.sync_api import sync_playwright

# Local imports
from instaharvest.config import ScraperConfig
from instaharvest.exceptions import InstagramScraperError
```

### Error Handling

```python
# Use custom exceptions
from instaharvest.exceptions import ProfileNotFoundError

try:
    profile = scraper.get_profile(username)
except ProfileNotFoundError:
    logger.error(f"Profile {username} not found")
    raise
```

---

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates

### Examples

```bash
# Feature
git commit -m "feat(follow): Add support for following multiple users at once"

# Bug fix
git commit -m "fix(unfollow): Increase popup_open_delay to prevent timeout errors"

# Documentation
git commit -m "docs(readme): Add example for custom configuration"

# Breaking change
git commit -m "feat(config): Remove deprecated sleep_time parameter

BREAKING CHANGE: sleep_time parameter has been removed.
Use popup_open_delay and button_click_delay instead."
```

---

## Pull Request Process

### Before Submitting

1. **Update documentation** if needed
2. **Test your changes** thoroughly
3. **Update CHANGELOG.md** with your changes
4. **Ensure code follows style guidelines**

### Submitting a Pull Request

1. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub:
   - Use a clear, descriptive title
   - Reference related issues (e.g., "Fixes #123")
   - Describe what changes you made and why
   - Include screenshots if applicable

3. **Review process:**
   - Maintainers will review your PR
   - Address any requested changes
   - Once approved, your PR will be merged!

### Pull Request Template

```markdown
## Description
Brief description of your changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Related Issues
Fixes #(issue number)

## Testing
Describe how you tested your changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] All tests pass
```

---

## Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New features (backwards compatible)
- **PATCH** version: Bug fixes (backwards compatible)

Example: `2.5.1`
- `2` = Major version
- `5` = Minor version
- `1` = Patch version

---

## Questions?

Feel free to ask questions by:
- Opening an issue
- Emailing: kelajak054@gmail.com
- Checking existing documentation

---

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes (if significant contribution)
- CHANGELOG.md

---

**Thank you for contributing to InstaHarvest!** 🎉

Every contribution, no matter how small, makes a difference. We appreciate your time and effort! 🙏
