#!/usr/bin/env python3
"""
Unfollow Debug Test
Shows exactly what's happening with selectors
"""

import sys
sys.dont_write_bytecode = True  # Don't create .pyc files

from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

print("=" * 70)
print("🔍 UNFOLLOW DEBUG TEST")
print("=" * 70)
print()

# Check code version
print("📋 Code Information:")
try:
    with open('instaharvest/follow.py', 'r') as f:
        code = f.read()
        if "div[role='button'] span:has-text('Unfollow')" in code:
            print("  ✅ FollowManager has UPDATED selectors")
        else:
            print("  ❌ FollowManager has OLD selectors")

        if "Method 1: div[role='button'] span:has-text('Unfollow')" in code:
            print("  ✅ Method 1 selector found in code")
        else:
            print("  ❌ Method 1 selector NOT found")

except Exception as e:
    print(f"  ❌ Error reading code: {e}")

print()

username = input("Enter username to unfollow (for debug test): ").strip()

if not username:
    print("❌ No username provided!")
    sys.exit(1)

print(f"\n🔄 Testing unfollow @{username} with DEBUG logging...")
print()

# Create config with DEBUG logging
config = ScraperConfig(
    headless=False,
    log_level='DEBUG',  # Show all debug messages!
    log_to_console=True
)

try:
    with SharedBrowser(config=config) as browser:
        print("✅ Browser opened with DEBUG logging")
        print()
        print("=" * 70)
        print("STARTING UNFOLLOW - WATCH DEBUG OUTPUT")
        print("=" * 70)
        print()

        result = browser.unfollow(username)

        print()
        print("=" * 70)
        print("RESULT:")
        print("=" * 70)

        if result['success']:
            print(f"✅ SUCCESS: {result['message']}")
        else:
            print(f"❌ FAILED: {result['message']}")

        print()
        print("Status:", result.get('status'))
        print()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("🔍 Debug test complete")
print("=" * 70)
