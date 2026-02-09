#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Media Downloader Test Script
Downloads posts and reels from Instagram

This script demonstrates the download functionality:
- Enter any Instagram post/reel URL
- Downloads all media (images/videos)
- Saves to downloads/ folder
"""

import sys
import os
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Robust import - works whether installed via pip or run from source
# Robust import - works whether installed via pip or run from source
# ALWAYS prioritize local development version if available
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.exists(os.path.join(parent_dir, 'instaharvest')):
    sys.path.insert(0, parent_dir)

from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file


def main():
    """Main function for media download test"""
    print("=" * 60)
    print("🎬 Instagram Media Downloader")
    print("=" * 60)
    print()
    
    # Use intelligent session discovery
    session_file = find_session_file()
    
    if not session_file:
        print("❌ Session file not found!")
        print()
        print("💡 The session file is searched in:")
        print("   1. Current directory")
        print("   2. Script directory")
        print("   3. ~/.instaharvest/")
        print()
        print("📝 Run 'python save_session.py' first to create a session.")
        return
    
    print(f"✅ Using session: {session_file}")
    print()

    # Configuration with intelligent session path
    config = ScraperConfig(
        headless=False,  # Visible browser to see what's happening
        page_load_delay=3.0,
        ui_animation_delay=2.0,
        session_file=session_file
    )

    url = input("📎 Enter Instagram Post/Reel URL to download: ").strip()
    if not url:
        print("❌ No URL provided. Exiting.")
        return
    
    # Validate URL
    if 'instagram.com' not in url:
        print("⚠️  Warning: URL doesn't look like an Instagram URL")
        confirm = input("   Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return

    try:
        print()
        print(f"🚀 Starting download for: {url}")
        print("-" * 60)
        
        with SharedBrowser(config=config) as browser:
            start_time = time.time()
            files = browser.download_post(url)
            end_time = time.time()
            
            print()
            print("-" * 60)
            print(f"⏱️  Finished in {end_time - start_time:.2f} seconds")
            print()
            
            if files:
                print(f"✅ Downloaded {len(files)} file(s):")
                for f in files:
                    print(f"   📁 {f}")
            else:
                print("⚠️  No files downloaded.")
                print("   This might happen if:")
                print("   - The post has no media")
                print("   - The URL is invalid")
                print("   - The account is private")

    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
