#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Instagram Media Downloader Example
Downloads posts and reels from Instagram (Images & Videos)

Usage:
    python examples/download_media.py
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

# Add parent directory to path to import instaharvest
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.exists(os.path.join(parent_dir, 'instaharvest')):
    sys.path.insert(0, parent_dir)

from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file


def main():
    print("=" * 60)
    print("🎬 Instagram Media Downloader")
    print("   Download Images & Videos from Posts/Reels")
    print("=" * 60)
    print()
    
    # 1. Locate Session
    session_file = find_session_file()
    if not session_file:
        print("❌ Session file not found!")
        print("   Please run 'python save_session.py' first.")
        return
    
    print(f"✅ Session found: {session_file}")

    # 2. Get URL
    url = input("\n📎 Enter Post/Reel URL: ").strip()
    if not url:
        return

    # 3. Setup Config
    config = ScraperConfig(
        headless=False,  # Visible browser
        session_file=session_file,
        # base_output_dir="my_downloads",  # Optional: Save files to a specific folder
    )

    print("\n🚀 Starting download manager...")
    if config.base_output_dir:
        print(f"📂 Output directory: {config.base_output_dir}")
    
    try:
        # 4. Use SharedBrowser to download
        with SharedBrowser(config=config) as browser:
            start_time = time.time()
            
            # The magic line:
            files = browser.download_post(url)
            
            duration = time.time() - start_time
            
            print("\n" + "-" * 60)
            if files:
                print(f"✅ Success! Downloaded {len(files)} files in {duration:.1f}s:")
                for f in files:
                    # Show relative path if possible for cleaner output
                    try:
                        rel_path = os.path.relpath(f, os.getcwd())
                        print(f"   📂 {rel_path}")
                    except:
                        print(f"   📂 {f}")
                print(f"\n📍 Saved in: {os.path.dirname(files[0])}")
            else:
                print("⚠️  No files found or download failed.")
                
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
