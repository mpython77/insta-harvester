"""
Instagram Session Management Utilities

This module provides utilities for creating and managing Instagram sessions.
Sessions are saved to allow reuse across multiple runs without re-logging in.
"""

import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from .config import ScraperConfig


def get_default_session_path():
    """
    Get the default session file path.

    Returns the session file in the current working directory.
    This ensures the session is easily accessible and portable.

    Returns:
        str: Path to the default session file
    """
    return os.path.join(os.getcwd(), 'instagram_session.json')


def save_session(session_file=None, headless=False):
    """
    Save Instagram session by manually logging in through a browser.

    This function opens a Chrome browser window, navigates to Instagram,
    and waits for you to manually log in. Once logged in, it saves your
    session cookies and storage state to a file for future use.

    Args:
        session_file (str, optional): Path where to save the session file.
            Defaults to 'instagram_session.json' in current directory.
        headless (bool, optional): Whether to run browser in headless mode.
            Defaults to False (visible browser for login).

    Returns:
        str: Path to the saved session file

    Example:
        >>> from instaharvest import save_session
        >>> save_session()
        🚀 Instagram session save utility started...
        📱 Opening Instagram...
        ✋ WAITING MODE:
        1️⃣  Manually login to Instagram
        2️⃣  Select "Remember me" after login
        3️⃣  Once you reach the home page, return to this terminal and press ENTER
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        ⌨️  Press ENTER when ready:

        💾 Saving session...
        ✅ Session successfully saved: instagram_session.json
        📊 Number of cookies: 12
        👋 Browser closed. Program finished!
    """
    if session_file is None:
        session_file = get_default_session_path()

    print('🚀 Instagram session save utility started...')
    print(f'📁 Session will be saved to: {session_file}')

    # Use config for consistent settings
    config = ScraperConfig(headless=headless)

    with sync_playwright() as p:
        # Launch browser using config settings
        browser = p.chromium.launch(
            channel='chrome',  # Use real Chrome
            headless=config.headless
        )

        # Create context using config settings
        context = browser.new_context(
            viewport={'width': config.viewport_width, 'height': config.viewport_height},
            user_agent=config.user_agent
        )

        page = context.new_page()

        print('📱 Opening Instagram...')
        page.goto('https://www.instagram.com/', wait_until='networkidle')

        print('\n✋ WAITING MODE:')
        print('1️⃣  Manually login to Instagram')
        print('2️⃣  Select "Remember me" after login')
        print('3️⃣  Once you reach the home page, return to this terminal and press ENTER')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        # Wait for Enter key
        input('\n⌨️  Press ENTER when ready: ')

        print('\n💾 Saving session...')

        # Save session data
        session_data = context.storage_state()

        # Ensure directory exists
        session_dir = os.path.dirname(session_file)
        if session_dir and not os.path.exists(session_dir):
            os.makedirs(session_dir, exist_ok=True)

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        print(f'✅ Session successfully saved: {session_file}')
        print(f'📊 Number of cookies: {len(session_data["cookies"])}')

        browser.close()
        print('👋 Browser closed. Program finished!')

        return session_file


def check_session_exists(session_file=None):
    """
    Check if a session file exists.

    Args:
        session_file (str, optional): Path to session file to check.
            Defaults to 'instagram_session.json' in current directory.

    Returns:
        bool: True if session file exists, False otherwise

    Example:
        >>> from instaharvest import check_session_exists
        >>> if not check_session_exists():
        ...     print("Please create a session first!")
        ...     save_session()
    """
    if session_file is None:
        session_file = get_default_session_path()

    return os.path.exists(session_file)


def load_session_data(session_file=None):
    """
    Load session data from file.

    Args:
        session_file (str, optional): Path to session file.
            Defaults to 'instagram_session.json' in current directory.

    Returns:
        dict: Session data containing cookies and storage state

    Raises:
        FileNotFoundError: If session file doesn't exist

    Example:
        >>> from instaharvest import load_session_data
        >>> session = load_session_data()
        >>> print(f"Loaded {len(session['cookies'])} cookies")
    """
    if session_file is None:
        session_file = get_default_session_path()

    if not os.path.exists(session_file):
        raise FileNotFoundError(
            f"Session file not found: {session_file}\n"
            f"Please create a session first using: save_session()"
        )

    with open(session_file, 'r', encoding='utf-8') as f:
        return json.load(f)
