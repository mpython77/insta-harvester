"""
Instagram Session Manager - Multi-Account Auto Rotation

Manage multiple Instagram sessions with automatic rotation,
health checking, and expired session handling.

Usage:
    from instaharvest import SessionManager

    sm = SessionManager()
    sm.add_session('session_account1.json')
    sm.add_session('session_account2.json')
    sm.add_session('session_account3.json')

    # Automatically rotates to next healthy session
    session_data = sm.get_session()
"""

import json
import time
import random
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


class SessionRotationStrategy(Enum):
    """Session rotation strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"


@dataclass
class SessionStats:
    """Statistics for a single session"""
    path: str
    requests: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    last_used: float = 0.0
    last_failure: float = 0.0
    is_healthy: bool = True
    is_expired: bool = False
    cookies_count: int = 0
    username: str = ''

    @property
    def success_rate(self) -> float:
        if self.requests == 0:
            return 1.0
        return self.successes / self.requests

    @property
    def status(self) -> str:
        if self.is_expired:
            return 'expired'
        if not self.is_healthy:
            return 'unhealthy'
        return 'healthy'


class SessionManager:
    """
    Professional multi-session manager for Instagram scraping.

    Features:
    - Multiple session file management
    - Auto rotation: round-robin, random, least-used
    - Health checking with failure tracking
    - Auto-skip expired/unhealthy sessions
    - Session stats and reporting
    - Max failure threshold with auto-disable
    - Cooldown between same session reuse

    Usage:
        sm = SessionManager(
            rotation=SessionRotationStrategy.ROUND_ROBIN,
            max_failures=5,
            cooldown_seconds=60,
        )
        sm.add_session('session1.json')
        sm.add_session('session2.json')

        # Get next healthy session data
        data = sm.get_session()

        # Mark session after use
        sm.mark_success()  # or sm.mark_failure()
    """

    def __init__(
        self,
        rotation: SessionRotationStrategy = SessionRotationStrategy.ROUND_ROBIN,
        max_failures: int = 5,
        cooldown_seconds: float = 30.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize SessionManager.

        Args:
            rotation: Rotation strategy (round_robin, random, least_used)
            max_failures: Max consecutive failures before disabling session
            cooldown_seconds: Min seconds between reusing same session
            logger: Optional logger
        """
        self.rotation = rotation
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.logger = logger or logging.getLogger(__name__)

        self._sessions: List[SessionStats] = []
        self._current_index: int = 0
        self._current_session: Optional[SessionStats] = None

    # ==================== Session Management ====================

    def add_session(self, path: str) -> bool:
        """
        Add a session file to the pool.

        Args:
            path: Path to session JSON file

        Returns:
            True if session added successfully
        """
        session_path = Path(path)

        if not session_path.exists():
            self.logger.warning(f"Session file not found: {path}")
            return False

        # Check for duplicates
        for s in self._sessions:
            if str(Path(s.path).resolve()) == str(session_path.resolve()):
                self.logger.warning(f"Session already added: {path}")
                return False

        # Validate session file
        try:
            with open(session_path, 'r') as f:
                data = json.load(f)

            cookies = data.get('cookies', [])
            if not cookies:
                self.logger.warning(f"No cookies in session: {path}")
                return False

            # Extract username if available
            username = ''
            for cookie in cookies:
                if cookie.get('name') == 'ds_user_id':
                    username = cookie.get('value', '')
                    break

            stats = SessionStats(
                path=str(session_path.resolve()),
                cookies_count=len(cookies),
                username=username,
            )
            self._sessions.append(stats)

            self.logger.info(
                f"Session added: {session_path.name} "
                f"({len(cookies)} cookies, user: {username or 'unknown'})"
            )
            return True

        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Invalid session file {path}: {e}")
            return False

    def add_sessions_from_dir(self, directory: str, pattern: str = '*session*.json') -> int:
        """
        Add all matching session files from a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for session files

        Returns:
            Number of sessions added
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            self.logger.warning(f"Directory not found: {directory}")
            return 0

        count = 0
        for path in sorted(dir_path.glob(pattern)):
            if self.add_session(str(path)):
                count += 1

        self.logger.info(f"Added {count} sessions from {directory}")
        return count

    # ==================== Session Retrieval ====================

    def get_session(self) -> Optional[Dict[str, Any]]:
        """
        Get the next healthy session data with rotation.

        Returns:
            Session data dict (cookies, etc.) or None if no healthy sessions
        """
        if not self._sessions:
            self.logger.warning("No sessions in pool")
            return None

        healthy = [s for s in self._sessions if s.is_healthy and not s.is_expired]
        if not healthy:
            self.logger.error("No healthy sessions available!")
            return None

        # Apply rotation strategy
        session = self._select_session(healthy)
        if session is None:
            return None

        # Load session data
        try:
            with open(session.path, 'r') as f:
                data = json.load(f)

            session.last_used = time.time()
            session.requests += 1
            self._current_session = session

            self.logger.info(
                f"Using session: {Path(session.path).name} "
                f"(#{session.requests}, {session.status})"
            )
            return data

        except Exception as e:
            self.logger.error(f"Failed to load session {session.path}: {e}")
            session.is_healthy = False
            return self.get_session()  # Try next

    def _select_session(self, healthy: List[SessionStats]) -> Optional[SessionStats]:
        """Select session based on rotation strategy"""
        now = time.time()

        # Filter by cooldown
        available = [
            s for s in healthy
            if (now - s.last_used) >= self.cooldown_seconds
        ]

        if not available:
            # All on cooldown — use the one with oldest last_used
            available = sorted(healthy, key=lambda s: s.last_used)

        if not available:
            return None

        if self.rotation == SessionRotationStrategy.ROUND_ROBIN:
            self._current_index = self._current_index % len(available)
            session = available[self._current_index]
            self._current_index += 1
            return session

        elif self.rotation == SessionRotationStrategy.RANDOM:
            return random.choice(available)

        elif self.rotation == SessionRotationStrategy.LEAST_USED:
            return min(available, key=lambda s: s.requests)

        return available[0]

    @property
    def current_session_path(self) -> Optional[str]:
        """Get path of currently active session"""
        return self._current_session.path if self._current_session else None

    # ==================== Health Tracking ====================

    def mark_success(self, session_path: Optional[str] = None) -> None:
        """Record successful request for a session"""
        session = self._find_session(session_path)
        if session:
            session.successes += 1
            session.consecutive_failures = 0

    def mark_failure(
        self,
        session_path: Optional[str] = None,
        error: Optional[str] = None,
        is_expired: bool = False,
    ) -> None:
        """
        Record failed request for a session.

        Args:
            session_path: Session path (uses current if None)
            error: Error message
            is_expired: True if failure was due to session expiration
        """
        session = self._find_session(session_path)
        if not session:
            return

        session.failures += 1
        session.consecutive_failures += 1
        session.last_failure = time.time()

        if is_expired:
            session.is_expired = True
            session.is_healthy = False
            self.logger.warning(
                f"Session expired: {Path(session.path).name} "
                f"(marked as expired)"
            )
        elif session.consecutive_failures >= self.max_failures:
            session.is_healthy = False
            self.logger.warning(
                f"Session disabled after {session.consecutive_failures} failures: "
                f"{Path(session.path).name}"
            )

        if error:
            self.logger.debug(f"Session failure: {error}")

    def mark_expired(self, session_path: Optional[str] = None) -> None:
        """Mark a session as expired (LoginRequired error)"""
        self.mark_failure(session_path, error="Session expired", is_expired=True)

    def _find_session(self, path: Optional[str] = None) -> Optional[SessionStats]:
        """Find session by path or return current"""
        if path is None:
            return self._current_session

        path_resolved = str(Path(path).resolve())
        for s in self._sessions:
            if str(Path(s.path).resolve()) == path_resolved:
                return s
        return None

    # ==================== Stats & Info ====================

    @property
    def total_sessions(self) -> int:
        return len(self._sessions)

    @property
    def healthy_count(self) -> int:
        return sum(1 for s in self._sessions if s.is_healthy and not s.is_expired)

    @property
    def expired_count(self) -> int:
        return sum(1 for s in self._sessions if s.is_expired)

    def get_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all sessions"""
        return [
            {
                'path': Path(s.path).name,
                'status': s.status,
                'requests': s.requests,
                'successes': s.successes,
                'failures': s.failures,
                'success_rate': f"{s.success_rate:.1%}",
                'cookies': s.cookies_count,
                'username': s.username,
            }
            for s in self._sessions
        ]

    def print_stats(self) -> None:
        """Print session pool statistics"""
        print(f"\n{'='*60}")
        print(f"  Session Pool: {self.total_sessions} total, "
              f"{self.healthy_count} healthy, {self.expired_count} expired")
        print(f"{'='*60}")

        for s in self._sessions:
            status_icon = {'healthy': '✅', 'unhealthy': '⚠️', 'expired': '❌'}.get(s.status, '?')
            print(
                f"  {status_icon} {Path(s.path).name:30s} | "
                f"req={s.requests:3d} ok={s.successes:3d} fail={s.failures:3d} | "
                f"{s.success_rate:.0%} | user={s.username or '?'}"
            )

    def reset_all(self) -> None:
        """Reset all session stats"""
        for s in self._sessions:
            s.requests = 0
            s.successes = 0
            s.failures = 0
            s.consecutive_failures = 0
            s.is_healthy = True
            s.is_expired = False
        self._current_index = 0
        self.logger.info("All session stats reset")
