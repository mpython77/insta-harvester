"""
Instagram Batch Media Downloader
Concurrent downloads with progress tracking, retry logic, and resume support.

Usage:
    from instaharvest import BatchDownloader, ScraperConfig

    downloader = BatchDownloader(config=ScraperConfig(), max_workers=8)
    results = downloader.download_posts(posts_data, username="john")
    print(f"Downloaded {results.success_count}/{results.total} files")
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .network_client import NetworkClient
from .post_data import PostData
from .logging_config import get_logger
from .config import ScraperConfig


# ==================== Data Models ====================

@dataclass
class DownloadTask:
    """Single download task"""
    url: str
    save_path: Path
    post_url: str = ''
    media_type: str = 'image'  # 'image' | 'video'
    index: int = 0
    shortcode: str = ''
    username: str = 'unknown'

    def __repr__(self) -> str:
        return f"DownloadTask({self.shortcode}_{self.index}.{self.media_type})"


@dataclass
class DownloadResult:
    """Result of a single download attempt"""
    task: DownloadTask
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    duration: float = 0.0
    error: Optional[str] = None
    retries: int = 0

    def __repr__(self) -> str:
        status = '✅' if self.success else '❌'
        size = self._format_size(self.file_size)
        return f"{status} {self.task.shortcode}_{self.task.index} ({size}, {self.duration:.1f}s)"

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f}MB"


@dataclass
class BatchResult:
    """Aggregated result of a batch download"""
    results: List[DownloadResult] = field(default_factory=list)
    total: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def total_bytes(self) -> int:
        return sum(r.file_size for r in self.results if r.success)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0.0

    @property
    def speed(self) -> float:
        """Average download speed in bytes/sec"""
        return self.total_bytes / self.duration if self.duration > 0 else 0

    def summary(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'success': self.success_count,
            'failed': self.failed_count,
            'total_bytes': self.total_bytes,
            'total_size': DownloadResult._format_size(self.total_bytes),
            'duration': round(self.duration, 1),
            'speed': DownloadResult._format_size(int(self.speed)) + '/s',
            'failed_files': [
                {'url': r.task.url, 'error': r.error}
                for r in self.results if not r.success
            ],
        }


# ==================== Progress Tracker ====================

class ProgressTracker:
    """
    Thread-safe real-time progress display.

    Output format:
        [████████░░░░] 45/100 | 23.5 MB | 2.3 MB/s | 3 failed
    """

    def __init__(self, total: int, bar_width: int = 30):
        self.total = total
        self.bar_width = bar_width
        self._lock = threading.Lock()
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.bytes_downloaded = 0
        self.start_time = time.time()
        self._last_print_time = 0.0

    def update(self, result: DownloadResult) -> None:
        """Update progress with a download result (thread-safe)"""
        with self._lock:
            if result.success:
                self.completed += 1
                self.bytes_downloaded += result.file_size
            else:
                self.failed += 1

    def skip(self) -> None:
        """Mark a task as skipped (already exists)"""
        with self._lock:
            self.skipped += 1
            self.completed += 1

    def print_progress(self, force: bool = False) -> None:
        """Print progress bar to stderr (thread-safe, rate-limited)"""
        now = time.time()
        # Rate limit to avoid flicker (max 4 updates/sec)
        if not force and (now - self._last_print_time) < 0.25:
            return

        with self._lock:
            self._last_print_time = now
            done = self.completed + self.failed
            pct = done / self.total if self.total > 0 else 0
            filled = int(self.bar_width * pct)
            bar = '█' * filled + '░' * (self.bar_width - filled)

            elapsed = now - self.start_time
            speed = self.bytes_downloaded / elapsed if elapsed > 0 else 0
            speed_str = DownloadResult._format_size(int(speed)) + '/s'
            size_str = DownloadResult._format_size(self.bytes_downloaded)

            parts = [
                f"\r[{bar}] {done}/{self.total}",
                f"{size_str}",
                speed_str,
            ]
            if self.failed > 0:
                parts.append(f"{self.failed} failed")
            if self.skipped > 0:
                parts.append(f"{self.skipped} skipped")

            line = ' | '.join(parts)
            sys.stderr.write(f"{line}  ")
            sys.stderr.flush()

    def finish(self) -> None:
        """Print final progress and newline"""
        self.print_progress(force=True)
        sys.stderr.write('\n')
        sys.stderr.flush()

    def __repr__(self) -> str:
        return f"ProgressTracker({self.completed}/{self.total})"


# ==================== Batch Downloader ====================

class BatchDownloader:
    """
    Concurrent media downloader with progress tracking, retry, and resume.

    Features:
    - ThreadPoolExecutor for parallel I/O (default: 8 workers)
    - Real-time progress bar with speed and stats
    - Auto-retry failed downloads (configurable max retries)
    - Resume support: skip already downloaded files
    - File validation (minimum size check for videos)
    - yt-dlp fallback for failed video downloads

    Usage:
        downloader = BatchDownloader(max_workers=8)
        batch = downloader.download_posts(posts, username="john")
        print(batch.summary())
    """

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        output_dir: Optional[str] = None,
        max_workers: int = 8,
        max_retries: int = 2,
        show_progress: bool = True,
    ):
        """
        Args:
            config: ScraperConfig instance
            output_dir: Base directory for downloads
            max_workers: Number of concurrent download threads
            max_retries: Max retry attempts for failed downloads
            show_progress: Show real-time progress bar
        """
        self.config = config or ScraperConfig()
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.show_progress = show_progress
        self.logger = get_logger('BatchDownloader')

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(self.config.base_output_dir) / 'downloads'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Network client for downloads
        self._client = NetworkClient()

    def download_posts(
        self,
        posts: List[PostData],
        username: str = 'unknown',
    ) -> BatchResult:
        """
        Download all media from multiple posts.

        Args:
            posts: List of PostData objects
            username: Username for directory organization

        Returns:
            BatchResult with all download results
        """
        # Create download tasks
        tasks = self._create_tasks(posts, username)

        if not tasks:
            self.logger.warning("No download tasks created")
            return BatchResult(total=0)

        self.logger.info(
            f"📥 Starting batch download: {len(tasks)} files "
            f"({self.max_workers} workers)"
        )

        # Load progress for resume support
        done_files = self._load_progress(username)

        # Execute downloads
        return self._execute_batch(tasks, username, done_files)

    def download_batch(self, tasks: List[DownloadTask]) -> BatchResult:
        """
        Download a custom list of tasks.

        Args:
            tasks: List of DownloadTask objects

        Returns:
            BatchResult
        """
        return self._execute_batch(tasks)

    def _create_tasks(
        self, posts: List[PostData], username: str
    ) -> List[DownloadTask]:
        """Convert PostData objects into DownloadTask list"""
        tasks = []
        user_dir = self.output_dir / username
        user_dir.mkdir(exist_ok=True)

        for post in posts:
            shortcode = post.url.strip('/').split('/')[-1]
            safe_ts = post.timestamp.replace(':', '-').replace('/', '-').replace('\\', '-')

            if not post.media_urls:
                continue

            for idx, url in enumerate(post.media_urls):
                is_video = '.mp4' in url or 'fv' in url or post.is_video
                ext = '.mp4' if is_video else '.jpg'
                media_type = 'video' if is_video else 'image'
                filename = f"{safe_ts}_{shortcode}_{idx}{ext}"

                tasks.append(DownloadTask(
                    url=url,
                    save_path=user_dir / filename,
                    post_url=post.url,
                    media_type=media_type,
                    index=idx,
                    shortcode=shortcode,
                    username=username,
                ))

        return tasks

    def _execute_batch(
        self,
        tasks: List[DownloadTask],
        username: str = 'unknown',
        done_files: Optional[Set[str]] = None,
    ) -> BatchResult:
        """Execute download tasks with thread pool and progress tracking"""
        batch = BatchResult(total=len(tasks), start_time=time.time())
        progress = ProgressTracker(len(tasks)) if self.show_progress else None

        # Filter already downloaded (resume)
        pending_tasks = []
        if done_files:
            for task in tasks:
                if str(task.save_path) in done_files:
                    if progress:
                        progress.skip()
                    batch.results.append(DownloadResult(
                        task=task, success=True,
                        file_path=str(task.save_path),
                        file_size=task.save_path.stat().st_size if task.save_path.exists() else 0,
                    ))
                else:
                    pending_tasks.append(task)
            if len(tasks) - len(pending_tasks) > 0:
                self.logger.info(
                    f"⏭️ Skipping {len(tasks) - len(pending_tasks)} already downloaded files"
                )
        else:
            pending_tasks = tasks

        # Download with thread pool
        if pending_tasks:
            with ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix='dl'
            ) as executor:
                futures = {
                    executor.submit(self._download_single, task): task
                    for task in pending_tasks
                }

                for future in as_completed(futures):
                    result = future.result()
                    batch.results.append(result)
                    if progress:
                        progress.update(result)
                        progress.print_progress()

        # Retry failed downloads
        failed = [r for r in batch.results if not r.success and r.retries < self.max_retries]
        if failed:
            self.logger.info(f"🔄 Retrying {len(failed)} failed downloads...")
            retry_results = self._retry_failed(failed)
            # Replace failed results with retry results
            for retry_result in retry_results:
                for i, r in enumerate(batch.results):
                    if (r.task.url == retry_result.task.url and not r.success):
                        batch.results[i] = retry_result
                        if progress and retry_result.success:
                            progress.failed -= 1
                            progress.completed += 1
                            progress.bytes_downloaded += retry_result.file_size
                        break

        if progress:
            progress.finish()

        batch.end_time = time.time()

        # Save progress for resume
        self._save_progress(username, batch)

        # Log summary
        s = batch.summary()
        self.logger.info(
            f"✅ Batch complete: {s['success']}/{s['total']} files, "
            f"{s['total_size']}, {s['speed']}, "
            f"{s['duration']}s"
        )
        if s['failed'] > 0:
            self.logger.warning(f"❌ {s['failed']} files failed to download")

        return batch

    def _download_single(self, task: DownloadTask) -> DownloadResult:
        """
        Download a single file (runs in worker thread).

        Returns:
            DownloadResult
        """
        start = time.time()

        try:
            # Skip if already exists and valid
            if task.save_path.exists():
                size = task.save_path.stat().st_size
                if size > 0:
                    return DownloadResult(
                        task=task, success=True,
                        file_path=str(task.save_path),
                        file_size=size,
                        duration=time.time() - start,
                    )

            # Ensure directory exists
            task.save_path.parent.mkdir(parents=True, exist_ok=True)

            # Download via NetworkClient
            success = self._client.download_media(task.url, str(task.save_path))

            if success and task.save_path.exists():
                file_size = task.save_path.stat().st_size

                # Validate video files (must be > 1MB)
                if task.media_type == 'video' and file_size < 1_000_000:
                    self.logger.debug(
                        f"Video too small ({file_size} bytes), "
                        f"trying yt-dlp: {task.shortcode}"
                    )
                    task.save_path.unlink(missing_ok=True)
                    ytdlp_path = self._download_with_ytdlp(task)
                    if ytdlp_path:
                        return DownloadResult(
                            task=task, success=True,
                            file_path=ytdlp_path,
                            file_size=Path(ytdlp_path).stat().st_size,
                            duration=time.time() - start,
                        )
                    return DownloadResult(
                        task=task, success=False,
                        error='Video too small and yt-dlp failed',
                        duration=time.time() - start,
                    )

                return DownloadResult(
                    task=task, success=True,
                    file_path=str(task.save_path),
                    file_size=file_size,
                    duration=time.time() - start,
                )

            return DownloadResult(
                task=task, success=False,
                error='Download returned False or file missing',
                duration=time.time() - start,
            )

        except Exception as e:
            return DownloadResult(
                task=task, success=False,
                error=str(e),
                duration=time.time() - start,
            )

    def _download_with_ytdlp(self, task: DownloadTask) -> Optional[str]:
        """Fallback to yt-dlp for video downloads"""
        try:
            import yt_dlp
        except ImportError:
            return None

        try:
            safe_ts = task.shortcode  # Already sanitized in task creation
            output_template = str(
                task.save_path.parent / f"{task.save_path.stem}_ytdlp.%(ext)s"
            )

            ydl_opts = {
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'format': 'best[ext=mp4]/best',
                'noplaylist': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task.post_url, download=True)
                if info:
                    ext = info.get('ext', 'mp4')
                    expected = task.save_path.parent / f"{task.save_path.stem}_ytdlp.{ext}"
                    if expected.exists():
                        return str(expected)
        except Exception:
            pass

        return None

    def _retry_failed(self, failed_results: List[DownloadResult]) -> List[DownloadResult]:
        """Retry failed downloads with increased delay"""
        retry_results = []

        for result in failed_results:
            time.sleep(1.0)  # Brief delay between retries
            task = result.task
            new_result = self._download_single(task)
            new_result.retries = result.retries + 1

            if new_result.success:
                self.logger.debug(f"✅ Retry success: {task.shortcode}_{task.index}")
            retry_results.append(new_result)

        return retry_results

    def _load_progress(self, username: str) -> Set[str]:
        """Load download progress for resume support"""
        progress_file = self.output_dir / username / '.progress.json'
        if progress_file.exists():
            try:
                with open(progress_file, 'r') as f:
                    data = json.load(f)
                return set(data.get('completed', []))
            except Exception:
                pass
        return set()

    def _save_progress(self, username: str, batch: BatchResult) -> None:
        """Save download progress for resume support"""
        progress_file = self.output_dir / username / '.progress.json'
        try:
            completed = [
                str(r.file_path) for r in batch.results
                if r.success and r.file_path
            ]
            data = {
                'completed': completed,
                'total': batch.total,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.debug(f"Failed to save progress: {e}")

    def __repr__(self) -> str:
        return (
            f"BatchDownloader(workers={self.max_workers}, "
            f"retries={self.max_retries}, dir={self.output_dir})"
        )
