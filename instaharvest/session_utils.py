"""
Instagram Session Management Utilities

This module provides utilities for creating and managing Instagram sessions.
Sessions are saved to allow reuse across multiple runs without re-logging in.

ARCHITECTURE v2.0:
- Smart session discovery across multiple locations
- Robust path handling for different IDEs and working directories
- Backward compatible with existing code
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Callable
from playwright.sync_api import sync_playwright
from .config import ScraperConfig

# Module-level logger
_logger = logging.getLogger(__name__)

# Session file name constant
SESSION_FILENAME = 'instagram_session.json'


def _get_search_paths() -> List[str]:
    """
    Get list of directories to search for session file.
    
    Search order (most likely to least likely):
    1. Current working directory
    2. Script's directory (where main.py is located)
    3. User's home/.instaharvest directory
    4. Library directory (where this file is)
    
    Returns:
        List of directory paths to search
    """
    paths = []
    
    # 1. Current working directory (most common)
    try:
        cwd = os.getcwd()
        if cwd not in paths:
            paths.append(cwd)
    except Exception:
        pass
    
    # 2. Script's directory (where the user's script is)
    try:
        if sys.argv and sys.argv[0]:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            if script_dir and script_dir not in paths:
                paths.append(script_dir)
    except Exception:
        pass
    
    # 3. User's instaharvest config directory
    try:
        user_config_dir = os.path.expanduser('~/.instaharvest')
        if user_config_dir not in paths:
            paths.append(user_config_dir)
    except Exception:
        pass
    
    # 4. Library directory (fallback)
    try:
        lib_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(lib_dir)
        if parent_dir not in paths:
            paths.append(parent_dir)
    except Exception:
        pass
    
    return paths


def find_session_file(filename: str = SESSION_FILENAME) -> Optional[str]:
    """
    Search for an existing session file in multiple locations.
    
    This function searches for the session file in the following order:
    1. Current working directory
    2. Script's directory
    3. User's ~/.instaharvest directory
    4. Library's parent directory
    
    Args:
        filename: Name of the session file to find
        
    Returns:
        Absolute path to the session file if found, None otherwise
        
    Example:
        >>> path = find_session_file()
        >>> if path:
        ...     print(f"Found session at: {path}")
        ... else:
        ...     print("No session found, please create one")
    """
    search_paths = _get_search_paths()
    
    for directory in search_paths:
        session_path = os.path.join(directory, filename)
        if os.path.isfile(session_path):
            _logger.debug(f"Found session file at: {session_path}")
            return os.path.abspath(session_path)
    
    _logger.debug(f"Session file '{filename}' not found in any of: {search_paths}")
    return None


def get_default_session_path(filename: str = SESSION_FILENAME, auto_discover: bool = True) -> str:
    """
    Get the default session file path with smart discovery.
    
    This function provides intelligent session file path resolution:
    - If auto_discover is True, searches multiple locations for existing session
    - Falls back to current working directory if no session found
    - Ensures consistent behavior across different IDEs and terminals
    
    Args:
        filename: Name of the session file
        auto_discover: If True, search for existing session in multiple locations.
                      If False, always return CWD path (legacy behavior).
    
    Returns:
        str: Absolute path to the session file
        
    Example:
        >>> # Will find existing session or default to CWD
        >>> path = get_default_session_path()
        >>> print(f"Session path: {path}")
        
        >>> # Force CWD (legacy behavior)
        >>> path = get_default_session_path(auto_discover=False)
    """
    if auto_discover:
        # Try to find existing session file
        found_path = find_session_file(filename)
        if found_path:
            return found_path
    
    # Default: current working directory
    return os.path.join(os.getcwd(), filename)


def get_session_save_path(filename: str = SESSION_FILENAME, prefer_cwd: bool = True) -> str:
    """
    Get the path where a new session should be saved.
    
    Unlike get_default_session_path which searches for existing sessions,
    this function determines where to SAVE a new session file.
    
    Args:
        filename: Name of the session file
        prefer_cwd: If True, save to current working directory.
                   If False, save to user's config directory.
    
    Returns:
        str: Absolute path where session should be saved
    """
    if prefer_cwd:
        return os.path.join(os.getcwd(), filename)
    else:
        # Use user's config directory
        config_dir = os.path.expanduser('~/.instaharvest')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, filename)


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
        page.goto(config.instagram_base_url, wait_until=config.session_save_wait_until)

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

        import tempfile
        tmp_path = session_file + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, session_file)

        cookies = session_data.get("cookies", [])
        print(f'✅ Session successfully saved: {session_file}')
        print(f'📊 Number of cookies: {len(cookies)}')

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
