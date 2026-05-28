
import os
import time
from pathlib import Path
from typing import List, Optional

from .network_client import NetworkClient
from .post_data import PostData
from .logging_config import get_logger
from .config import ScraperConfig

class MediaDownloader:
    """
    Handles downloading media files (Images/Videos) from Instagram.
    Uses NetworkClient for high-speed downloads with browser impersonation.
    Falls back to yt-dlp for videos when direct download fails.
    """

    def __init__(
        self, 
        output_dir: Optional[str] = None, 
        config: Optional[ScraperConfig] = None
    ):
        self.config = config or ScraperConfig()

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(self.config.base_output_dir) / "downloads"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = NetworkClient()
        self.logger = get_logger('MediaDownloader')

    def _download_with_ytdlp(self, post_url: str, save_dir: Path, shortcode: str, timestamp: str) -> Optional[str]:
        """
        Download video using yt-dlp (most reliable for Instagram videos).
        
        Args:
            post_url: Instagram post/reel URL
            save_dir: Directory to save video
            shortcode: Post shortcode for filename
            timestamp: Timestamp for filename
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            import yt_dlp
        except ImportError:
            self.logger.warning("yt-dlp not installed. Run: pip install yt-dlp")
            return None
        
        cookie_file = None
        try:
            safe_timestamp = timestamp.replace(':', '-').replace('/', '-').replace('\\', '-')
            output_template = str(save_dir / f"{safe_timestamp}_{shortcode}_ytdlp.%(ext)s")

            # Create Netscape cookie file from session.
            # SECURITY: this file contains live Instagram cookies; we must
            # remove it in the finally branch even if yt-dlp raises, so it
            # never lingers in /tmp readable by other local processes.
            cookie_file = self._create_cookie_file_from_session()

            ydl_opts = {
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'format': 'best[ext=mp4]/best',
                'noplaylist': True,
            }

            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info(f"🎬 Using yt-dlp for: {shortcode}")
                info = ydl.extract_info(post_url, download=True)
                if info:
                    # Find the downloaded file
                    ext = info.get('ext', 'mp4')
                    expected_path = save_dir / f"{safe_timestamp}_{shortcode}_ytdlp.{ext}"
                    if expected_path.exists():
                        self.logger.info(f"✅ yt-dlp downloaded: {expected_path.name}")
                        return str(expected_path)

        except Exception as e:
            self.logger.warning(f"yt-dlp failed: {e}")
        finally:
            # Always remove the cookie file — leaks here would expose the
            # user's Instagram session to anyone with /tmp access.
            if cookie_file:
                try:
                    import os as _os
                    _os.unlink(cookie_file)
                except FileNotFoundError:
                    pass
                except OSError as cleanup_err:
                    self.logger.warning(
                        f"Failed to remove temp cookie file {cookie_file}: {cleanup_err}"
                    )

        return None

    def _create_cookie_file_from_session(self) -> Optional[str]:
        """
        Create Netscape format cookie file from instagram_session.json
        
        Returns:
            Path to cookie file or None if failed
        """
        import json
        import tempfile
        
        # Look for session file in common locations
        session_paths = [
            Path('instagram_session.json'),
            Path('examples/instagram_session.json'),
            Path.home() / '.instagram_session.json',
        ]
        
        session_file = None
        for p in session_paths:
            if p.exists():
                session_file = p
                break
        
        if not session_file:
            self.logger.debug("No session file found for yt-dlp cookies")
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            cookies = session_data.get('cookies', [])
            if not cookies:
                return None
            
            # Create Netscape format cookie file
            cookie_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', delete=False, prefix='ig_cookies_'
            )
            
            # Write Netscape header
            cookie_file.write("# Netscape HTTP Cookie File\n")
            cookie_file.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
            cookie_file.write("# This is a generated file! Do not edit.\n\n")
            
            for cookie in cookies:
                # Netscape format: domain, domain_flag, path, secure, expiry, name, value
                domain = cookie.get('domain', '.instagram.com')
                domain_flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', True) else 'FALSE'
                expires = int(cookie.get('expires', 0))
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                cookie_file.write(f"{domain}\t{domain_flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
            
            cookie_file.close()
            self.logger.debug(f"Created cookie file: {cookie_file.name}")
            return cookie_file.name
            
        except Exception as e:
            self.logger.debug(f"Failed to create cookie file: {e}")
            return None

    def download_post(self, post: PostData, username: str = "unknown") -> List[str]:
        """
        Download all media from a PostData object.
        
        Args:
            post: PostData object containing media_urls
            username: Owner username for file organization
            
        Returns:
            List of saved file paths
        """
        # Create user specific directory
        user_dir = self.output_dir / username
        user_dir.mkdir(exist_ok=True)
        
        saved_files = []
        shortcode = post.url.strip('/').split('/')[-1]
        
        # For Reels/Videos: Use yt-dlp directly (most reliable!)
        if post.is_video:
            self.logger.info(f"🎬 Video detected - using yt-dlp for {shortcode}...")
            ytdlp_path = self._download_with_ytdlp(
                post.url, user_dir, shortcode, post.timestamp
            )
            if ytdlp_path:
                saved_files.append(ytdlp_path)
                self.logger.info(f"✅ Downloaded 1/1 files (via yt-dlp).")
                return saved_files
            else:
                self.logger.warning("yt-dlp failed, falling back to direct download...")
        
        if not post.media_urls:
            self.logger.warning(f"No media URLs found for post: {post.url}")
            return []

        self.logger.info(f"⬇️ Downloading {len(post.media_urls)} files for post {shortcode}...")

        for index, url in enumerate(post.media_urls):
            try:
                # determine extension
                is_video = ".mp4" in url or "fv" in url # simple heuristic
                ext = ".mp4" if is_video else ".jpg"
                if post.is_video and len(post.media_urls) == 1:
                     ext = ".mp4"

                # Sanitize timestamp for valid filename (N/A has slash!)
                safe_timestamp = post.timestamp.replace(':', '-').replace('/', '-').replace('\\', '-')
                filename = f"{safe_timestamp}_{shortcode}_{index}{ext}"
                save_path = user_dir / filename
                
                if self.client.download_media(url, str(save_path)):
                    # Check if file is valid (at least 1MB for videos)
                    if ext == ".mp4" and save_path.exists() and save_path.stat().st_size < 1_000_000:
                        self.logger.warning(f"Video too small ({save_path.stat().st_size} bytes), trying yt-dlp...")
                        save_path.unlink()  # Delete small file
                        ytdlp_path = self._download_with_ytdlp(
                            post.url, user_dir, shortcode, post.timestamp
                        )
                        if ytdlp_path:
                            saved_files.append(ytdlp_path)
                            break  # yt-dlp handles all videos in post
                    else:
                        saved_files.append(str(save_path))
                    # Tiny delay to be nice
                    time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Failed to download {url}: {e}")

        self.logger.info(f"✅ Downloaded {len(saved_files)}/{len(post.media_urls)} files.")
        return saved_files
