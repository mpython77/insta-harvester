"""
Instagram Scraper - Advanced Error Handling System
Intelligent error recovery and retry mechanisms
"""

import time
import functools
import logging
from typing import Callable, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .config import ScraperConfig


@dataclass
class ErrorContext:
    """Detailed error context for debugging"""
    timestamp: str
    function_name: str
    url: Optional[str] = None
    selector: Optional[str] = None
    error_type: str = ''
    error_message: str = ''
    retry_count: int = 0
    recovery_action: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class ErrorStats:
    """Error statistics tracking"""
    total_errors: int = 0
    recovered_errors: int = 0
    failed_errors: int = 0
    error_types: dict = field(default_factory=dict)
    error_contexts: List[ErrorContext] = field(default_factory=list)
    config: Optional[ScraperConfig] = None

    def __post_init__(self):
        """Initialize config if not provided"""
        if self.config is None:
            self.config = ScraperConfig()

    def add_error(self, context: ErrorContext, recovered: bool):
        """Add error to statistics"""
        self.total_errors += 1
        if recovered:
            self.recovered_errors += 1
        else:
            self.failed_errors += 1

        # Track error types
        error_type = context.error_type
        if error_type not in self.error_types:
            self.error_types[error_type] = 0
        self.error_types[error_type] += 1

        # Store context
        self.error_contexts.append(context)

    def get_recovery_rate(self) -> float:
        """Calculate error recovery rate"""
        if self.total_errors == 0:
            return 100.0
        return (self.recovered_errors / self.total_errors) * 100

    def get_report(self) -> str:
        """Generate error statistics report"""
        sep_width = self.config.report_separator_width
        recent_limit = self.config.error_recent_limit

        lines = [
            "=" * sep_width,
            "ERROR STATISTICS REPORT",
            "=" * sep_width,
            f"Total Errors: {self.total_errors}",
            f"Recovered: {self.recovered_errors}",
            f"Failed: {self.failed_errors}",
            f"Recovery Rate: {self.get_recovery_rate():.1f}%",
            "",
            "Error Types:",
        ]

        for error_type, count in sorted(self.error_types.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {error_type}: {count}")

        if self.error_contexts:
            lines.append("")
            lines.append(f"Recent Errors (last {recent_limit}):")
            for ctx in self.error_contexts[-recent_limit:]:
                lines.append(f"  [{ctx.timestamp}] {ctx.function_name}: {ctx.error_message[:60]}...")

        lines.append("=" * sep_width)
        return "\n".join(lines)


class ErrorHandler:
    """
    Advanced error handling with intelligent recovery

    Features:
    - Automatic retry with exponential backoff
    - Error categorization
    - Recovery strategies
    - Detailed logging
    - Statistics tracking
    """

    def __init__(self, logger: Optional[logging.Logger] = None, config: Optional[ScraperConfig] = None):
        """Initialize error handler"""
        self.logger = logger or logging.getLogger(__name__)
        self.config = config if config is not None else ScraperConfig()
        self.stats = ErrorStats(config=self.config)

    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: Optional[int] = None,
        initial_delay: Optional[float] = None,
        backoff_factor: Optional[float] = None,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """
        Retry function with exponential backoff

        Args:
            func: Function to retry
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds
            backoff_factor: Multiplier for each retry
            exceptions: Tuple of exceptions to catch

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        if max_retries is None:
            max_retries = self.config.default_max_retries
        if initial_delay is None:
            initial_delay = self.config.default_retry_initial_delay
        if backoff_factor is None:
            backoff_factor = self.config.default_retry_backoff_factor

        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func()
            except exceptions as e:
                last_exception = e

                if attempt < max_retries:
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    self.logger.error(
                        f"All {max_retries + 1} attempts failed. Last error: {e}"
                    )

        if last_exception:
            raise last_exception

    def safe_extract(
        self,
        extractor: Callable,
        element_name: str,
        default: Any = None,
        url: Optional[str] = None,
        selector: Optional[str] = None
    ) -> Any:
        """
        Safely extract data with error handling

        Args:
            extractor: Extraction function
            element_name: Name of element being extracted
            default: Default value if extraction fails
            url: URL being scraped (for logging)
            selector: Selector being used (for logging)

        Returns:
            Extracted value or default
        """
        context = ErrorContext(
            timestamp=datetime.now().strftime(self.config.datetime_format),
            function_name=element_name,
            url=url,
            selector=selector
        )

        try:
            result = extractor()
            return result

        except Exception as e:
            # Build error context
            context.error_type = type(e).__name__
            context.error_message = str(e)

            # Log detailed error
            self.logger.error(
                f"❌ EXTRACTION FAILED: {element_name}\n"
                f"   URL: {url}\n"
                f"   Selector: {selector}\n"
                f"   Error: {context.error_type}: {context.error_message}\n"
                f"   Using default value: {default}"
            )

            # Track error
            self.stats.add_error(context, recovered=True)

            return default

    def with_recovery(
        self,
        primary_func: Callable,
        fallback_func: Optional[Callable] = None,
        element_name: str = 'unknown',
        default: Any = None
    ) -> Any:
        """
        Execute function with fallback recovery

        Args:
            primary_func: Primary extraction function
            fallback_func: Fallback function if primary fails
            element_name: Name for logging
            default: Default if both fail

        Returns:
            Result from primary, fallback, or default
        """
        context = ErrorContext(
            timestamp=datetime.now().strftime(self.config.datetime_format),
            function_name=element_name
        )

        # Try primary
        try:
            result = primary_func()
            self.logger.debug(f"✓ {element_name}: Primary method succeeded")
            return result

        except Exception as e:
            context.error_type = type(e).__name__
            context.error_message = str(e)
            self.logger.warning(f"⚠️ {element_name}: Primary method failed - {e}")

            # Try fallback
            if fallback_func:
                try:
                    result = fallback_func()
                    context.recovery_action = "Fallback method succeeded"
                    self.logger.info(f"✓ {element_name}: Fallback method succeeded")
                    self.stats.add_error(context, recovered=True)
                    return result

                except Exception as e2:
                    context.recovery_action = f"Fallback also failed: {e2}"
                    self.logger.error(f"❌ {element_name}: Fallback method also failed - {e2}")

            # Both failed, use default
            context.recovery_action = f"Using default: {default}"
            self.stats.add_error(context, recovered=False)
            return default

    def get_stats(self) -> ErrorStats:
        """Get error statistics"""
        return self.stats

    def print_stats(self):
        """Print error statistics report"""
        report = self.stats.get_report()
        self.logger.info("\n" + report)


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator for automatic retry with exponential backoff

    Usage:
        @retry_on_error(max_retries=3, delay=1.0)
        def my_function():
            # ...

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= 2
                    else:
                        raise

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def log_errors(logger: Optional[logging.Logger] = None):
    """
    Decorator for automatic error logging

    Usage:
        @log_errors()
        def my_function():
            # ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(
                    f"Error in {func.__name__}: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator
