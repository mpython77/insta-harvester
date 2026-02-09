"""
InstaHarvest - Smart Logging System
Intelligent logging with context, emojis, and performance tracking.
"""

import logging
import time
import sys
from typing import Optional, Any, Dict
from contextlib import contextmanager
from functools import wraps


class SmartLogger:
    """
    Smart logging with context, emojis, and user-friendly output.
    
    Features:
    - Emoji-prefixed messages for quick status recognition
    - Auto-context (module, function names)
    - Performance tracking with @timed decorator
    - Separate user output vs debug logging
    
    Usage:
        logger = SmartLogger("ProfileScraper")
        logger.success("Profile scraped", username="cristiano")
        logger.error("Failed to load", url="...")
        
        with logger.operation("Scraping posts"):
            # ... your code ...
            # Auto-logs start/end with duration
    """
    
    # Emoji prefixes for terminal
    EMOJI = {
        'success': '[OK]',
        'error': '[ERROR]',
        'warning': '[WARN]',
        'info': '[INFO]',
        'debug': '[DEBUG]',
        'progress': '[...]',
        'proxy': '[PROXY]',
        'browser': '[BROWSER]',
        'network': '[NET]',
    }
    
    def __init__(
        self, 
        name: str,
        level: str = 'INFO',
        log_file: Optional[str] = None,
        show_context: bool = True,
        show_emoji: bool = True,
        log_to_console: bool = True
    ):
        """
        Initialize SmartLogger.
        
        Args:
            name: Logger name (usually module or class name)
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            log_file: Optional file path for logging
            show_context: Include module/function context
            show_emoji: Use emoji prefixes
            log_to_console: Print to console
        """
        self.name = name
        self.show_context = show_context
        self.show_emoji = show_emoji
        
        # Create standard logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # Avoid duplicate handlers
        if not self._logger.handlers:
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            )
            
            if log_to_console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                self._logger.addHandler(console_handler)
            
            if log_file:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)
    
    def _format_message(self, emoji_key: str, msg: str, **context) -> str:
        """Format message with emoji and context"""
        parts = []
        
        if self.show_emoji and emoji_key in self.EMOJI:
            parts.append(self.EMOJI[emoji_key])
        
        parts.append(msg)
        
        if context:
            context_str = ' | '.join(f"{k}={v}" for k, v in context.items())
            parts.append(f"({context_str})")
        
        return ' '.join(parts)
    
    # ==================== Main Logging Methods ====================
    
    def success(self, msg: str, **context) -> None:
        """Log success message"""
        formatted = self._format_message('success', msg, **context)
        self._logger.info(formatted)
    
    def error(self, msg: str, **context) -> None:
        """Log error message"""
        formatted = self._format_message('error', msg, **context)
        self._logger.error(formatted)
    
    def warning(self, msg: str, **context) -> None:
        """Log warning message"""
        formatted = self._format_message('warning', msg, **context)
        self._logger.warning(formatted)
    
    def info(self, msg: str, **context) -> None:
        """Log info message"""
        formatted = self._format_message('info', msg, **context)
        self._logger.info(formatted)
    
    def debug(self, msg: str, **context) -> None:
        """Log debug message"""
        formatted = self._format_message('debug', msg, **context)
        self._logger.debug(formatted)
    
    def progress(self, msg: str, **context) -> None:
        """Log progress message"""
        formatted = self._format_message('progress', msg, **context)
        self._logger.info(formatted)
    
    def proxy(self, msg: str, **context) -> None:
        """Log proxy-related message"""
        formatted = self._format_message('proxy', msg, **context)
        self._logger.info(formatted)
    
    def browser(self, msg: str, **context) -> None:
        """Log browser-related message"""
        formatted = self._format_message('browser', msg, **context)
        self._logger.info(formatted)
    
    def network(self, msg: str, **context) -> None:
        """Log network-related message"""
        formatted = self._format_message('network', msg, **context)
        self._logger.info(formatted)
    
    # ==================== Context Manager ====================
    
    @contextmanager
    def operation(self, name: str, **context):
        """
        Context manager for timed operations.
        
        Usage:
            with logger.operation("Scraping profile"):
                # ... your code ...
        """
        start = time.time()
        self.progress(f"Starting: {name}", **context)
        
        try:
            yield
            duration = time.time() - start
            self.success(f"Completed: {name}", duration=f"{duration:.2f}s", **context)
        except Exception as e:
            duration = time.time() - start
            self.error(f"Failed: {name}", error=str(e), duration=f"{duration:.2f}s", **context)
            raise
    
    # ==================== Decorator ====================
    
    def timed(self, func):
        """
        Decorator to time function execution.
        
        Usage:
            @logger.timed
            def my_function():
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.operation(func.__name__):
                return func(*args, **kwargs)
        return wrapper
    
    # ==================== Factory Methods ====================
    
    @classmethod
    def from_config(cls, config: 'ScraperConfig', name: str = 'InstaHarvest') -> 'SmartLogger':
        """
        Create SmartLogger from ScraperConfig.
        
        Args:
            config: ScraperConfig instance
            name: Logger name
            
        Returns:
            Configured SmartLogger
        """
        return cls(
            name=name,
            level=getattr(config, 'log_level', 'INFO'),
            log_file=getattr(config, 'log_file', None),
            show_context=getattr(config, 'log_show_context', True),
            show_emoji=getattr(config, 'log_emoji_enabled', True),
            log_to_console=getattr(config, 'log_to_console', True)
        )


# ==================== Module-level convenience ====================

_loggers: Dict[str, SmartLogger] = {}

def get_logger(name: str = 'InstaHarvest') -> SmartLogger:
    """Get or create a SmartLogger instance by name"""
    if name not in _loggers:
        _loggers[name] = SmartLogger(name)
    return _loggers[name]


def set_default_logger(name: str, logger: SmartLogger) -> None:
    """Set a logger for a specific name"""
    _loggers[name] = logger

