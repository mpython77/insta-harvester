#!/usr/bin/env python3
"""
Test script to verify unfollow works with SharedBrowser
"""

import sys
sys.dont_write_bytecode = True  # Don't create .pyc files

from instaharvest import SharedBrowser

print("=" * 60)
print("Testing Unfollow with SharedBrowser")
print("=" * 60)

username = input("\nEnter username to unfollow: ").strip()

print(f"\n🔄 Testing unfollow @{username}...")
print("Using SharedBrowser...\n")

try:
    with SharedBrowser() as browser:
        print("✅ Browser opened")

        result = browser.unfollow(username)

        print("\n" + "=" * 60)
        if result['success']:
            print(f"✅ SUCCESS: {result['message']}")
        else:
            print(f"❌ FAILED: {result['message']}")
        print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
