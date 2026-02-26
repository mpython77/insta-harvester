"""
Instagram Event System & Follower Watcher
Production-grade event-driven architecture with pluggable callbacks.

Usage:
    from instaharvest import EventEmitter, FollowerWatcher, ScraperConfig

    emitter = EventEmitter()

    @emitter.on("new_follower")
    def on_new(event):
        print(f"New follower: {event.data['username']}")

    @emitter.on("unfollow")
    def on_unfollow(event):
        print(f"Unfollowed: {event.data['username']}")

    watcher = FollowerWatcher(config, emitter, interval=300)
    await watcher.start()
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from .config import ScraperConfig
from .logging_config import get_logger


# ==================== Event Data Model ====================

@dataclass
class Event:
    """
    Immutable event object passed to callbacks.

    Attributes:
        type: Event type string (e.g. 'new_follower', 'unfollow')
        data: Event payload dictionary
        timestamp: When the event was created
        source: Module that emitted the event
    """
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = 'instaharvest'

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event for JSON export / logging"""
        return {
            'type': self.type,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
        }

    def __repr__(self) -> str:
        return f"Event(type='{self.type}', data={self.data})"


# ==================== Event Types ====================

class EventTypes:
    """Registry of standard event type constants"""
    # Follower events
    NEW_FOLLOWER = 'new_follower'
    UNFOLLOW = 'unfollow'
    FOLLOWER_COUNT = 'follower_count'

    # Scraping events
    SCRAPE_START = 'scrape_start'
    SCRAPE_COMPLETE = 'scrape_complete'
    SCRAPE_ERROR = 'scrape_error'

    # Download events
    DOWNLOAD_START = 'download_start'
    DOWNLOAD_COMPLETE = 'download_complete'
    DOWNLOAD_ERROR = 'download_error'

    # Rate limit events
    RATE_LIMITED = 'rate_limited'
    RATE_LIMIT_RESOLVED = 'rate_limit_resolved'


# ==================== Event Emitter ====================

class EventEmitter:
    """
    Thread-safe event bus with sync and async support.

    Features:
    - Register/unregister callbacks per event type
    - Wildcard '*' listener receives ALL events
    - Decorator syntax: @emitter.on("event_type")
    - Async emit for non-blocking callback execution
    - Event history with configurable max size
    - Error isolation: one failing callback doesn't block others

    Example:
        emitter = EventEmitter()

        @emitter.on("new_follower")
        def handle(event):
            print(event.data['username'])

        emitter.emit("new_follower", {"username": "john"})
    """

    def __init__(self, max_history: int = 1000):
        self._listeners: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._max_history = max_history
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='event')
        self.logger = get_logger('EventEmitter')

    def on(self, event_type: str, callback: Optional[Callable] = None):
        """
        Register a callback for an event type.
        Can be used as a decorator or direct call.

        Args:
            event_type: Event type string or '*' for all events
            callback: Callable that receives an Event object

        Returns:
            Decorator function if callback is None, else None

        Examples:
            # Direct call
            emitter.on("new_follower", my_handler)

            # Decorator
            @emitter.on("new_follower")
            def my_handler(event):
                ...
        """
        def decorator(func):
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(func)
            self.logger.debug(f"Registered listener for '{event_type}': {func.__name__}")
            return func

        if callback is not None:
            # Direct call: emitter.on("type", callback)
            return decorator(callback)
        # Decorator: @emitter.on("type")
        return decorator

    def off(self, event_type: str, callback: Callable) -> bool:
        """
        Unregister a callback.

        Returns:
            True if callback was found and removed
        """
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                self.logger.debug(f"Unregistered listener for '{event_type}': {callback.__name__}")
                return True
            except ValueError:
                pass
        return False

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None,
             source: str = 'instaharvest') -> Event:
        """
        Emit an event synchronously. All callbacks are called in order.
        Errors in callbacks are logged but don't propagate.

        Args:
            event_type: Event type string
            data: Event payload
            source: Module that emitted the event

        Returns:
            The created Event object
        """
        event = Event(type=event_type, data=data or {}, source=source)

        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Get matching listeners
        listeners = list(self._listeners.get(event_type, []))
        # Also fire wildcard listeners
        listeners.extend(self._listeners.get('*', []))

        if listeners:
            self.logger.debug(f"Emitting '{event_type}' to {len(listeners)} listeners")

        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                self.logger.error(
                    f"Listener error on '{event_type}': "
                    f"{listener.__name__}: {e}"
                )

        return event

    async def emit_async(self, event_type: str, data: Optional[Dict[str, Any]] = None,
                         source: str = 'instaharvest') -> Event:
        """
        Emit event asynchronously using thread pool for sync callbacks.
        Async callbacks are awaited directly.

        Returns:
            The created Event object
        """
        event = Event(type=event_type, data=data or {}, source=source)

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        listeners = list(self._listeners.get(event_type, []))
        listeners.extend(self._listeners.get('*', []))

        loop = asyncio.get_event_loop()

        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    await loop.run_in_executor(self._executor, listener, event)
            except Exception as e:
                self.logger.error(
                    f"Async listener error on '{event_type}': "
                    f"{listener.__name__}: {e}"
                )

        return event

    def once(self, event_type: str, callback: Optional[Callable] = None):
        """
        Register a one-time callback that auto-unregisters after firing.

        Can be used as decorator or direct call.
        """
        def decorator(func):
            def wrapper(event):
                func(event)
                self.off(event_type, wrapper)
            wrapper.__name__ = func.__name__
            self.on(event_type, wrapper)
            return func

        if callback is not None:
            return decorator(callback)
        return decorator

    @property
    def history(self) -> List[Event]:
        """Get event history (newest last)"""
        return list(self._history)

    @property
    def listener_count(self) -> Dict[str, int]:
        """Get count of listeners per event type"""
        return {k: len(v) for k, v in self._listeners.items() if v}

    def clear(self) -> None:
        """Remove all listeners and clear history"""
        self._listeners.clear()
        self._history.clear()
        self.logger.debug("All listeners and history cleared")

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._listeners.values())
        return f"EventEmitter(listeners={total}, history={len(self._history)})"


# ==================== Follower Watcher ====================

class FollowerWatcher:
    """
    Monitor follower changes and emit events.

    Periodically checks the follower list and compares with the previous
    snapshot to detect new followers and unfollows.

    Events emitted:
    - 'new_follower': {username: str, profile_url: str}
    - 'unfollow': {username: str}
    - 'follower_count': {count: int, delta: int, new: int, lost: int}

    Usage:
        watcher = FollowerWatcher(config, emitter, interval=300)
        await watcher.start()  # Runs indefinitely
        # or
        result = await watcher.check_once()  # Single check
    """

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        emitter: Optional[EventEmitter] = None,
        interval: float = 300.0,
        snapshot_file: Optional[str] = None,
    ):
        """
        Args:
            config: ScraperConfig for browser setup
            emitter: EventEmitter to fire events on (creates one if None)
            interval: Check interval in seconds (default: 5 min)
            snapshot_file: Path to store follower snapshots (default: followers_snapshot.json)
        """
        self.config = config or ScraperConfig()
        self.emitter = emitter or EventEmitter()
        self.interval = interval
        self.snapshot_file = Path(snapshot_file or 'followers_snapshot.json')
        self.logger = get_logger('FollowerWatcher')

        self._running = False
        self._previous_followers: Set[str] = set()
        self._task: Optional[asyncio.Task] = None

        # Load existing snapshot
        self._load_snapshot()

    def _load_snapshot(self) -> None:
        """Load previous follower snapshot from disk"""
        if self.snapshot_file.exists():
            try:
                with open(self.snapshot_file, 'r') as f:
                    data = json.load(f)
                self._previous_followers = set(data.get('followers', []))
                self.logger.info(
                    f"Loaded snapshot: {len(self._previous_followers)} followers "
                    f"from {data.get('timestamp', 'unknown')}"
                )
            except Exception as e:
                self.logger.warning(f"Failed to load snapshot: {e}")

    def _save_snapshot(self, followers: Set[str]) -> None:
        """Save current follower snapshot to disk"""
        try:
            data = {
                'followers': sorted(followers),
                'count': len(followers),
                'timestamp': datetime.now().isoformat(),
            }
            with open(self.snapshot_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Saved snapshot: {len(followers)} followers")
        except Exception as e:
            self.logger.warning(f"Failed to save snapshot: {e}")

    async def check_once(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a single follower check and emit events for changes.

        Args:
            username: Instagram username to check (uses config default if None)

        Returns:
            Dict with 'new', 'lost', 'count', 'delta' keys
        """
        from .followers import FollowersCollector

        self.logger.info("🔍 Checking followers...")

        # Collect current followers (runs sync playwright in thread)
        loop = asyncio.get_event_loop()
        current_followers = await loop.run_in_executor(
            None, self._collect_followers_sync, username
        )

        current_set = set(current_followers)
        result = {
            'new': [],
            'lost': [],
            'count': len(current_set),
            'delta': 0,
        }

        # Compare with previous snapshot
        if self._previous_followers:
            new_followers = current_set - self._previous_followers
            lost_followers = self._previous_followers - current_set

            result['new'] = sorted(new_followers)
            result['lost'] = sorted(lost_followers)
            result['delta'] = len(new_followers) - len(lost_followers)

            # Emit events for new followers
            for username in new_followers:
                await self.emitter.emit_async(
                    EventTypes.NEW_FOLLOWER,
                    {'username': username, 'profile_url': f'https://www.instagram.com/{username}/'},
                    source='FollowerWatcher'
                )

            # Emit events for unfollows
            for username in lost_followers:
                await self.emitter.emit_async(
                    EventTypes.UNFOLLOW,
                    {'username': username},
                    source='FollowerWatcher'
                )

            # Emit count summary
            await self.emitter.emit_async(
                EventTypes.FOLLOWER_COUNT,
                {
                    'count': len(current_set),
                    'delta': result['delta'],
                    'new': len(new_followers),
                    'lost': len(lost_followers),
                },
                source='FollowerWatcher'
            )

            self.logger.info(
                f"📊 Followers: {len(current_set)} "
                f"(+{len(new_followers)} new, -{len(lost_followers)} lost)"
            )
        else:
            self.logger.info(f"📊 Initial snapshot: {len(current_set)} followers")

        # Update snapshot
        self._previous_followers = current_set
        self._save_snapshot(current_set)

        return result

    def _collect_followers_sync(self, username: Optional[str] = None) -> List[str]:
        """Synchronous wrapper to collect followers using FollowersCollector"""
        from .followers import FollowersCollector

        collector = FollowersCollector(self.config)
        try:
            target = username or self.config.session_file.replace('instagram_session.json', '').strip('/')
            if not target or target == '.':
                self.logger.error("No username provided and cannot determine from config")
                return []
            return collector.get_followers(target, print_realtime=False)
        except Exception as e:
            self.logger.error(f"Failed to collect followers: {e}")
            return []

    async def start(self, username: Optional[str] = None) -> None:
        """
        Start the follower watching loop.
        Runs indefinitely, checking every `interval` seconds.

        Args:
            username: Instagram username to monitor
        """
        self._running = True
        self.logger.info(
            f"🚀 FollowerWatcher started (interval: {self.interval}s)"
        )

        while self._running:
            try:
                await self.check_once(username)
            except Exception as e:
                self.logger.error(f"Watch cycle error: {e}")
                await self.emitter.emit_async(
                    EventTypes.SCRAPE_ERROR,
                    {'error': str(e), 'module': 'FollowerWatcher'},
                    source='FollowerWatcher'
                )

            # Wait for next check
            if self._running:
                self.logger.debug(f"⏳ Next check in {self.interval}s")
                await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """Stop the watching loop gracefully"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self.logger.info("🛑 FollowerWatcher stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def tracked_count(self) -> int:
        """Number of followers in current snapshot"""
        return len(self._previous_followers)

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"FollowerWatcher({status}, tracked={self.tracked_count}, interval={self.interval}s)"
