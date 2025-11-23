# 🧪 Tests Directory

This directory contains test and debug scripts for InstaHarvest development.

## 📁 Contents

- **test_unfollow_debug.py** - Debug script for testing unfollow functionality with detailed logging

## 🚀 Running Tests

These are debug/development scripts, not automated unit tests.

### Run Unfollow Debug Test

```bash
# From project root
python tests/test_unfollow_debug.py
```

This will:
- Enable DEBUG logging to show all selector attempts
- Prompt for a username to unfollow
- Display detailed output of the unfollow process
- Help diagnose any issues with the unfollow operation

## 📝 Notes

- These scripts are for **development and debugging** purposes
- They require an active Instagram session (`instagram_session.json`)
- Run them from the project root directory
- They use headless=False by default so you can see what's happening

## ⚠️ Important

These are not production scripts - they're tools to help debug and test specific functionality during development.

For production usage, see the `examples/` directory instead.
