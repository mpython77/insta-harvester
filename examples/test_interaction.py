#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Script for Instagram Interactions
Tests like/comment functionality on posts and reels
"""

import time
import os

# Robust import - works whether installed via pip or run from source
import sys

# ALWAYS prioritize local development version if available
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.exists(os.path.join(parent_dir, 'instaharvest')):
    sys.path.insert(0, parent_dir)

from instaharvest.orchestrator import InstagramOrchestrator
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file


def test_interaction():
    # Use the session - automatically discovered
    config = ScraperConfig()
    
    # Use intelligent session discovery
    session_path = find_session_file()
    if session_path:
        config.session_file = session_path
        print(f"✅ Found session at: {session_path}")
    else:
        print("❌ No session file found!")
        print("   Run save_session.py first to create one.")
        return
    
    config.headless = False  # Run visible to see it work
    
    orchestrator = InstagramOrchestrator(config)
    
    # 1. Test Like/Comment on specific post
    target_post = "https://www.instagram.com/p/DTSlgl9iPrn"
    print(f"Testing interaction on: {target_post}")
    
    orchestrator.interact_with_post(
        url=target_post,
        like=True,
        comment="Test comment agent" # Optional: turn off if risky
    )
    
    # 2. Test Reels Flow
    #orchestrator.run_reels_interaction_flow(duration_minutes=1, like_probability=0.5)

if __name__ == "__main__":
    test_interaction()
