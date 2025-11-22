"""
Instagram Scraper - Performance Monitoring System
Track speed, memory usage, and optimize resource consumption
"""

import time
import psutil
import os
import functools
import logging
from typing import Callable, Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation"""
    operation_name: str
    start_time: float
    end_time: float = 0.0
    duration: float = 0.0
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_delta_mb: float = 0.0
    cpu_percent: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def finalize(self, memory_after: float, cpu_percent: float, success: bool = True, error: Optional[str] = None):
        """Finalize metrics after operation completes"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.memory_after_mb = memory_after
        self.memory_delta_mb = memory_after - self.memory_before_mb
        self.cpu_percent = cpu_percent
        self.success = success
        self.error = error


@dataclass
class PerformanceStats:
    """Overall performance statistics"""
    metrics: List[PerformanceMetrics] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def add_metric(self, metric: PerformanceMetrics):
        """Add performance metric"""
        self.metrics.append(metric)

    def get_total_time(self) -> float:
        """Get total elapsed time since start"""
        return time.time() - self.start_time

    def get_average_duration(self, operation_name: Optional[str] = None) -> float:
        """Get average duration for operations"""
        relevant_metrics = self.metrics
        if operation_name:
            relevant_metrics = [m for m in self.metrics if m.operation_name == operation_name]

        if not relevant_metrics:
            return 0.0

        return sum(m.duration for m in relevant_metrics) / len(relevant_metrics)

    def get_total_memory_used(self) -> float:
        """Get total memory used (MB)"""
        if not self.metrics:
            return 0.0
        return max(m.memory_after_mb for m in self.metrics)

    def get_operations_per_second(self) -> float:
        """Get operations per second"""
        total_time = self.get_total_time()
        if total_time == 0:
            return 0.0
        return len(self.metrics) / total_time

    def get_success_rate(self) -> float:
        """Get success rate percentage"""
        if not self.metrics:
            return 100.0
        successful = sum(1 for m in self.metrics if m.success)
        return (successful / len(self.metrics)) * 100

    def get_report(self) -> str:
        """Generate performance report"""
        lines = [
            "=" * 70,
            "PERFORMANCE REPORT",
            "=" * 70,
            f"Total Time: {self.get_total_time():.2f}s",
            f"Total Operations: {len(self.metrics)}",
            f"Operations/Second: {self.get_operations_per_second():.2f}",
            f"Success Rate: {self.get_success_rate():.1f}%",
            f"Peak Memory: {self.get_total_memory_used():.2f} MB",
            "",
            "Operation Breakdown:",
        ]

        # Group by operation name
        operations = {}
        for metric in self.metrics:
            if metric.operation_name not in operations:
                operations[metric.operation_name] = []
            operations[metric.operation_name].append(metric)

        for op_name, metrics_list in sorted(operations.items()):
            avg_duration = sum(m.duration for m in metrics_list) / len(metrics_list)
            total_duration = sum(m.duration for m in metrics_list)
            count = len(metrics_list)
            success_count = sum(1 for m in metrics_list if m.success)

            lines.append(
                f"  {op_name}:"
            )
            lines.append(
                f"    Count: {count}, Success: {success_count}/{count}, "
                f"Avg: {avg_duration:.3f}s, Total: {total_duration:.2f}s"
            )

        # Slowest operations
        lines.append("")
        lines.append("Slowest Operations (Top 5):")
        sorted_metrics = sorted(self.metrics, key=lambda m: m.duration, reverse=True)[:5]
        for i, metric in enumerate(sorted_metrics, 1):
            lines.append(
                f"  {i}. {metric.operation_name}: {metric.duration:.3f}s "
                f"(Memory: +{metric.memory_delta_mb:.2f} MB)"
            )

        lines.append("=" * 70)
        return "\n".join(lines)


class PerformanceMonitor:
    """
    Performance monitoring system

    Features:
    - Track execution time
    - Monitor memory usage
    - Track CPU usage
    - Generate performance reports
    - Optimize resource consumption
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize performance monitor"""
        self.logger = logger or logging.getLogger(__name__)
        self.stats = PerformanceStats()
        self.process = psutil.Process(os.getpid())

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024

    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage"""
        return self.process.cpu_percent(interval=0.1)

    @contextmanager
    def measure(self, operation_name: str):
        """
        Context manager for measuring operation performance

        Usage:
            with monitor.measure("scrape_post"):
                scrape_post(url)
        """
        # Start metrics
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            memory_before_mb=self.get_memory_usage()
        )

        success = True
        error = None

        try:
            yield metric
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            # Finalize metrics
            metric.finalize(
                memory_after=self.get_memory_usage(),
                cpu_percent=self.get_cpu_percent(),
                success=success,
                error=error
            )

            # Add to stats
            self.stats.add_metric(metric)

            # Log performance
            status = "✓" if success else "✗"
            self.logger.debug(
                f"{status} {operation_name}: {metric.duration:.3f}s "
                f"(Memory: +{metric.memory_delta_mb:.2f} MB, CPU: {metric.cpu_percent:.1f}%)"
            )

    def measure_function(self, operation_name: Optional[str] = None):
        """
        Decorator for measuring function performance

        Usage:
            @monitor.measure_function("my_operation")
            def my_function():
                pass
        """
        def decorator(func: Callable) -> Callable:
            op_name = operation_name or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.measure(op_name):
                    return func(*args, **kwargs)

            return wrapper
        return decorator

    def get_stats(self) -> PerformanceStats:
        """Get performance statistics"""
        return self.stats

    def print_report(self):
        """Print performance report"""
        report = self.stats.get_report()
        self.logger.info("\n" + report)

    def check_memory_threshold(self, threshold_mb: float = 500.0) -> bool:
        """
        Check if memory usage exceeds threshold

        Args:
            threshold_mb: Memory threshold in MB

        Returns:
            True if memory usage is below threshold
        """
        current_memory = self.get_memory_usage()
        if current_memory > threshold_mb:
            self.logger.warning(
                f"⚠️ Memory usage high: {current_memory:.2f} MB (threshold: {threshold_mb} MB)"
            )
            return False
        return True

    def optimize_memory(self):
        """Force garbage collection to free memory"""
        import gc
        before = self.get_memory_usage()
        gc.collect()
        after = self.get_memory_usage()
        freed = before - after

        if freed > 0:
            self.logger.info(f"♻️ Memory optimized: Freed {freed:.2f} MB")

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
            'memory_percent': psutil.virtual_memory().percent,
            'process_memory_mb': self.get_memory_usage(),
            'process_cpu_percent': self.get_cpu_percent()
        }

    def log_system_info(self):
        """Log system information"""
        info = self.get_system_info()
        self.logger.info(
            f"\n💻 SYSTEM INFO:\n"
            f"  CPU: {info['cpu_count']} cores @ {info['cpu_percent']:.1f}%\n"
            f"  RAM: {info['memory_available_gb']:.1f}/{info['memory_total_gb']:.1f} GB available "
            f"({100 - info['memory_percent']:.1f}% free)\n"
            f"  Process: {info['process_memory_mb']:.2f} MB, CPU: {info['process_cpu_percent']:.1f}%"
        )


# Singleton instance for global usage
_global_monitor = None


def get_monitor(logger: Optional[logging.Logger] = None) -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor(logger)
    return _global_monitor


def measure(operation_name: str):
    """
    Decorator for measuring function performance (uses global monitor)

    Usage:
        @measure("my_operation")
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            with monitor.measure(operation_name):
                return func(*args, **kwargs)

        return wrapper
    return decorator
