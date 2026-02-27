"""
Instagram Notification Reader — v2.0
Reads and parses notifications from Instagram's activity feed.

Based on full-page HTML analysis of Instagram notification page:
- Sidebar navigation (Home, Reels, Messages, Search, Explore, Notifications, Create, Profile)
- Main content area with section headings (Yesterday, This week, This month, Earlier)
- Each notification item inside div[data-pressable-container]

Supported notification types:
- comment_like: "liked your comment: ..."
- post_like: "liked your post/reel/photo/video"
- follow: "started following you"
- comment: "commented: ..."
- mention: "mentioned you" / "tagged you"
- thread: "posted a thread you might be interested in"
- story: "posted a story"
- follow_request: "requested to follow you"
- follow_accepted: "accepted your follow request"
- system: Meta/Instagram system notifications
- other: Unrecognized types

All selectors are centralized in config.py for easy maintenance.
"""
import re
import time
import random
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from .config import ScraperConfig


# ==================== DATA MODEL ====================

@dataclass
class NotificationItem:
    """Data model for a single notification item"""
    type: str = 'other'
    usernames: List[str] = field(default_factory=list)
    text: str = ''
    time_text: str = ''           # "1d", "2d", "6d", "Jan 28", "Nov 23"
    time_label: str = ''          # "a day ago", "2 days ago", "6 days ago"
    section: str = ''             # "Yesterday", "This week", "This month", "Earlier"
    post_url: Optional[str] = None    # "/p/DVCORGOAHTC/"
    profile_url: Optional[str] = None  # "/taina.srocha/"
    action_button: Optional[str] = None  # "Following" | "Follow Back" | None
    is_grouped: bool = False      # "and 5 others liked..."
    extra_count: int = 0          # 5 from "and 5 others"
    comment_text: Optional[str] = None  # "Test 701 🔥"
    profile_pic_url: Optional[str] = None
    profile_pic_urls: List[str] = field(default_factory=list)  # Grouped: 2 pics

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            'type': self.type,
            'usernames': self.usernames,
            'text': self.text,
            'time_text': self.time_text,
            'time_label': self.time_label,
            'section': self.section,
            'post_url': self.post_url,
            'profile_url': self.profile_url,
            'action_button': self.action_button,
            'is_grouped': self.is_grouped,
            'extra_count': self.extra_count,
            'comment_text': self.comment_text,
            'profile_pic_url': self.profile_pic_url,
            'profile_pic_urls': self.profile_pic_urls,
        }


# ==================== MAIN READER CLASS ====================

class NotificationReader:
    """
    Opens and reads all notifications from the Instagram activity feed.
    
    HTML structure (full-page, updated 2026-02-26):
    
        div#mount_0_0_2Z
        ├── Sidebar Navigation (72px width)
        │   ├── Instagram logo → href="/"
        │   ├── Home, Reels, Messages, Search, Explore
        │   ├── Notifications (svg[aria-label="Notifications"]) ← active
        │   ├── Create, Profile
        │   └── Settings, Also from Meta
        │
        ├── main[role="main"]
        │   └── div.xivu535
        │       ├── div[role="heading"] > span → "Yesterday"
        │       │   └── div[data-pressable-container]
        │       │       ├── div (avatars: 2x 32x32 or 1x 44x44)
        │       │       ├── div.x1iyjqo2 (text content)
        │       │       │   ├── a._a6hd → username link with span._aade
        │       │       │   ├── text: "liked your comment:", "started following you."
        │       │       │   └── abbr[aria-label] → time ("a day ago")
        │       │       └── div (right side)
        │       │           ├── a[aria-label="Media thumbnail"] → post link
        │       │           └── button._aswp → "Following" / "Follow Back"
        │       │
        │       ├── div[role="heading"] → "This week"
        │       ├── div[role="heading"] → "This month"
        │       └── div[role="heading"] → "Earlier"
        │
        └── Footer + Chat sidebar
    
    Usage:
        reader = NotificationReader(page, logger)
        notifications = reader.read_notifications(max_count=50)
        
        for n in notifications:
            print(f"[{n.section}] {n.type}: @{n.usernames} - {n.text}")
        
        # Statistics
        reader.summary(notifications)
        
        # Only follows
        follows = reader.get_follows()
        
        # Filter
        yesterday = reader.filter_by_section(notifications, 'Yesterday')
    """
    
    # Patterns for detecting notification type (order matters!)
    # Multi-language support: English, Russian, Turkish, Spanish, Portuguese,
    # French, German, Indonesian, Arabic, Korean, Japanese, Italian, Chinese, Uzbek
    NOTIFICATION_PATTERNS = [
        # --- COMMENT LIKE ---
        (r'liked your comment', 'comment_like'),
        (r'понравился ваш комментарий', 'comment_like'),       # Russian
        (r'yorumunuzu beğendi', 'comment_like'),                # Turkish
        (r'le gustó tu comentario', 'comment_like'),            # Spanish
        (r'curtiu seu comentário', 'comment_like'),             # Portuguese
        (r'a aimé votre commentaire', 'comment_like'),          # French
        (r'gefällt dein Kommentar', 'comment_like'),            # German
        (r'menyukai komentar', 'comment_like'),                 # Indonesian
        (r'أعجب بتعليقك', 'comment_like'),                      # Arabic
        (r'kommentingizni yoqtirdi', 'comment_like'),           # Uzbek
        
        # --- POST/REEL/PHOTO/VIDEO LIKE ---
        (r'liked your', 'post_like'),                           # English (generic)
        (r'нравится ваш', 'post_like'),                         # Russian  
        (r'нравится ваше видео', 'post_like'),                  # Russian (video Reels)
        (r'gönderinizi beğendi', 'post_like'),                  # Turkish
        (r'le gustó tu', 'post_like'),                          # Spanish
        (r'curtiu sua', 'post_like'),                           # Portuguese
        (r'a aimé votre', 'post_like'),                         # French
        (r'gefällt dein', 'post_like'),                         # German
        (r'menyukai postingan', 'post_like'),                   # Indonesian
        (r'أعجب بمنشورك', 'post_like'),                         # Arabic
        (r'postingizni yoqtirdi', 'post_like'),                 # Uzbek
        
        # --- FOLLOW (most critical for follow-back detection!) ---
        (r'started following you', 'follow'),                   # English
        (r'подписался.*на ваши', 'follow'),                     # Russian (male)
        (r'подписалась.*на ваши', 'follow'),                    # Russian (female)
        (r'подписался\(-ась\) на ваши', 'follow'),              # Russian (combined)
        (r'seni takip etmeye başladı', 'follow'),               # Turkish
        (r'empezó a seguirte', 'follow'),                       # Spanish
        (r'começou a seguir você', 'follow'),                   # Portuguese
        (r'a commencé à vous suivre', 'follow'),                # French
        (r'folgt dir jetzt', 'follow'),                         # German
        (r'mulai mengikuti', 'follow'),                         # Indonesian
        (r'بدأ بمتابعتك', 'follow'),                            # Arabic
        (r'あなたをフォロー', 'follow'),                          # Japanese
        (r'님이 팔로우', 'follow'),                               # Korean
        (r'ha iniziato a seguirti', 'follow'),                  # Italian
        (r'开始关注了你', 'follow'),                              # Chinese
        (r'sizni kuzatishni boshladi', 'follow'),               # Uzbek
        (r'follow', 'follow'),                                  # Fallback: button-based
        
        # --- FOLLOW REQUEST ---
        (r'requested to follow', 'follow_request'),
        (r'запросил.*подписку', 'follow_request'),              # Russian
        
        # --- FOLLOW ACCEPTED ---
        (r'accepted your follow', 'follow_accepted'),
        (r'принял.*запрос на подписку', 'follow_accepted'),     # Russian
        
        # --- COMMENT ---
        (r'прокомментировал', 'comment'),                       # Russian
        (r'commented:', 'comment'),                             # English
        (r'comentó:', 'comment'),                               # Spanish
        (r'comentou:', 'comment'),                              # Portuguese
        (r'yorum yaptı:', 'comment'),                           # Turkish
        (r'a commenté', 'comment'),                             # French
        (r'hat kommentiert', 'comment'),                        # German
        (r'berkomentar:', 'comment'),                           # Indonesian
        (r'komment yozdi', 'comment'),                          # Uzbek
        
        # --- MENTION/TAG ---
        (r'mentioned you', 'mention'),
        (r'tagged you', 'mention'),
        (r'упомянул', 'mention'),                               # Russian
        (r'отметил', 'mention'),                                # Russian (tagged)
        
        # --- THREAD ---
        (r'posted a thread', 'thread'),
        (r'опубликовал.*тему', 'thread'),                       # Russian
        
        # --- STORY ---
        (r'posted a story', 'story'),
        (r'опубликовал.*историю', 'story'),                     # Russian
    ]
    
    # Pattern to find "and X others" in grouped notifications
    GROUPED_PATTERN = re.compile(r'and (\d+) others?')
    
    # Known section headings (multi-language)
    KNOWN_SECTIONS = {
        # English
        'Yesterday', 'This week', 'This month', 'Earlier', 'Today', 'New',
        # Russian
        'Вчера', 'На этой неделе', 'В этом месяце', 'Ранее', 'Сегодня', 'Новинки',
        # Turkish
        'Dün', 'Bu hafta', 'Bu ay', 'Daha önce', 'Bugün', 'Yeni',
        # Spanish
        'Ayer', 'Esta semana', 'Este mes', 'Antes', 'Hoy', 'Nuevo',
    }
    
    def __init__(self, page, logger, config: Optional[ScraperConfig] = None):
        self.page = page
        self.logger = logger
        self.config = config or ScraperConfig()
        self._section_map = {}  # y_position -> section_name
    
    # ==================== PAGE NAVIGATION ====================
    
    def open_notifications(self, wait: float = 3.0) -> bool:
        """
        Opens the notification page.
        
        Strategy:
        1. If already on the activity page — return immediately
        2. If blank/about:blank — first navigate to instagram.com
        3. Navigate to activity URL
        4. Wait for notification elements (data-pressable-container)
        5. Fallback — click Notifications icon in sidebar
        
        Returns:
            True if page opened successfully
        """
        try:
            current_url = self.page.url or ''
            target_url = self.config.notification_url
            
            # 1. Already on notification page
            if 'accounts/activity' in current_url:
                self.logger.info("🔔 Already on notification page")
                # Wait for content to load
                try:
                    self.page.wait_for_selector(
                        self.config.selector_notif_item, timeout=5000
                    )
                except Exception:
                    pass
                return True
            
            # 2. If blank page — first navigate to Instagram
            if not current_url or 'about:blank' in current_url or current_url == '':
                self.logger.info("📍 Blank page — navigating to instagram.com first...")
                self.page.goto('https://www.instagram.com/', wait_until='domcontentloaded')
                time.sleep(3 + random.uniform(0.5, 1.0))
            
            # 3. Navigate to activity page
            self.logger.info(f"📍 Navigating to {target_url}")
            self.page.goto(target_url, wait_until='domcontentloaded')
            time.sleep(wait + random.uniform(0.5, 1.5))
            
            # 4. LOGIN REDIRECT CHECK
            after_url = self.page.url or ''
            if 'accounts/login' in after_url:
                self.logger.error(
                    "❌ Instagram redirected to login page! "
                    "Session has expired or cookies were not loaded. "
                    "Please login first and update the session data."
                )
                return False
            
            # 5. Wait for notification elements (most reliable check)
            try:
                self.page.wait_for_selector(
                    self.config.selector_notif_item, timeout=8000
                )
                self.logger.info("🔔 Notification page loaded ✅")
                return True
            except Exception:
                pass
            
            # 4b. main[role="main"] check
            main = self.page.locator('main[role="main"]')
            if main.count() > 0:
                self.logger.info("🔔 Notification page loaded (main found)")
                time.sleep(2)
                return True
            
            # 5. Fallback — click Notifications icon in sidebar
            self.logger.info("🔄 Fallback — clicking sidebar icon...")
            notif_icon = self.page.locator('svg[aria-label="Notifications"]')
            if notif_icon.count() > 0:
                notif_icon.first.click()
                time.sleep(3)
                
                # Recheck for notification elements
                try:
                    self.page.wait_for_selector(
                        self.config.selector_notif_item, timeout=5000
                    )
                    self.logger.info("🔔 Notification panel opened (via icon) ✅")
                    return True
                except Exception:
                    pass
                
                # Icon click sometimes opens panel, sometimes redirects to page
                if 'accounts/activity' in (self.page.url or ''):
                    self.logger.info("🔔 Redirected to activity page ✅")
                    time.sleep(2)
                    return True
            
            self.logger.warning("⚠️ Failed to load notification page")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to open notifications: {e}")
            return False
    
    # ==================== MAIN READ METHOD ====================
    
    def read_notifications(self, max_count: int = 50, scroll: bool = True, 
                           open_page: bool = True) -> List[NotificationItem]:
        """
        Reads all notifications and returns structured data.
        
        Args:
            max_count: Maximum number of notifications to read
            scroll: Scroll down to load more notifications
            open_page: Automatically open the notification page
            
        Returns:
            List[NotificationItem] — all found notifications
        """
        if open_page:
            if not self.open_notifications():
                return []
        
        notifications = []
        seen_texts = set()
        
        try:
            # 1. Find section headings and record their positions
            self._build_section_map()
            
            # 2. Find all notification items
            items = self.page.locator(self.config.selector_notif_item)
            total = items.count()
            
            if total == 0:
                self.logger.warning("⚠️ No notifications found")
                return []
            
            self.logger.info(f"🔔 Found {total} notifications")
            
            # 3. Scroll to load more notifications
            if scroll and total < max_count:
                total = self._scroll_to_load(max_count)
                items = self.page.locator(self.config.selector_notif_item)
                total = items.count()
            
            count = min(total, max_count)
            
            # 4. Parse each notification item
            for i in range(count):
                try:
                    item = items.nth(i)
                    notif = self._parse_notification_item(item)
                    
                    if notif:
                        # Prevent duplicates
                        key = f"{notif.type}:{':'.join(notif.usernames)}:{notif.time_text}"
                        if key not in seen_texts:
                            seen_texts.add(key)
                            notifications.append(notif)
                except Exception as e:
                    self.logger.debug(f"  Error parsing notification {i}: {e}")
                    continue
            
            # 5. Log statistics
            type_counts = self._count_types(notifications)
            section_counts = self._count_sections(notifications)
            self.logger.info(
                f"🔔 Parsed: {len(notifications)} notifications | "
                f"Types: {type_counts} | Sections: {section_counts}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to read notifications: {e}")
        
        return notifications
    
    # ==================== ITEM PARSER ====================
    
    def _parse_notification_item(self, item) -> Optional[NotificationItem]:
        """Parses a single notification element"""
        notif = NotificationItem()
        
        try:
            # --- 1. Extract text content ---
            text_container = item.locator('div.x1iyjqo2 > span').first
            if text_container.count() > 0:
                raw_text = text_container.inner_text(timeout=2000)
                # Clean text: remove newlines, collapse extra whitespace
                notif.text = self._clean_text(raw_text)
            
            if not notif.text:
                return None
            
            # --- 2. Extract usernames (a._a6hd links) ---
            username_links = item.locator(self.config.selector_notif_username)
            link_count = username_links.count()
            
            for j in range(link_count):
                link = username_links.nth(j)
                href = link.get_attribute('href', timeout=1000)
                if href and href.startswith('/') and not href.startswith('/p/') and not href.startswith('/explore'):
                    # Find the username span
                    username_span = link.locator(self.config.selector_notif_username_text).first
                    if username_span.count() > 0:
                        username = username_span.inner_text(timeout=1000).strip()
                        if username and username not in notif.usernames:
                            notif.usernames.append(username)
                    
                    # First username's profile URL
                    if not notif.profile_url:
                        notif.profile_url = href
            
            # --- 3. Thread usernames (without a._a6hd links, extracted from text) ---
            if not notif.usernames and notif.text:
                thread_match = re.match(r'^(\S+)\s+(posted a thread|posted a story)', notif.text)
                if thread_match:
                    notif.usernames.append(thread_match.group(1))
                    # Thread profile URL
                    thread_link = item.locator('a._a6hd[href]').first
                    if thread_link.count() > 0:
                        notif.profile_url = thread_link.get_attribute('href', timeout=1000)
            
            # --- 4. Detect notification type ---
            notif.type = self._detect_type(notif.text)
            
            # --- 5. Extract timestamp ---
            time_elem = item.locator(self.config.selector_notif_time).first
            if time_elem.count() > 0:
                notif.time_label = time_elem.get_attribute('aria-label', timeout=1000) or ''
                notif.time_text = time_elem.inner_text(timeout=1000).strip()
            else:
                # Time might be embedded in the text (Jan 28, Nov 23, Oct 13)
                date_match = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\b', notif.text)
                if date_match:
                    notif.time_text = date_match.group(0)
            
            # --- 6. Post URL (media thumbnail) ---
            thumbnail = item.locator(self.config.selector_notif_thumbnail).first
            if thumbnail.count() > 0:
                notif.post_url = thumbnail.get_attribute('href', timeout=1000)
            
            # --- 7. Follow button ---
            follow_btn = item.locator(self.config.selector_notif_follow_btn).first
            if follow_btn.count() > 0:
                try:
                    # Get button text — "Following" or "Follow Back"
                    btn_text = follow_btn.inner_text(timeout=1000).strip()
                    if btn_text:
                        notif.action_button = btn_text
                except Exception:
                    pass
            
            # --- 8. Grouped detection (and X others) ---
            grouped_match = self.GROUPED_PATTERN.search(notif.text)
            if grouped_match:
                notif.is_grouped = True
                notif.extra_count = int(grouped_match.group(1))
            
            # --- 9. Comment text (if comment_like type) ---
            if notif.type == 'comment_like' and 'liked your comment:' in notif.text:
                parts = notif.text.split('liked your comment:', 1)
                if len(parts) > 1:
                    comment = parts[1].strip()
                    # Remove time text from the end
                    if notif.time_text and comment.endswith(notif.time_text):
                        comment = comment[:-len(notif.time_text)].strip()
                    notif.comment_text = comment
            
            # --- 10. Profile pictures ---
            # Grouped: 2x 32x32 images (stacked avatars)
            # Single: 1x 44x44 image with alt="username's profile picture"
            pics = item.locator('img')
            pic_count = pics.count()
            
            for p in range(min(pic_count, 3)):
                try:
                    pic = pics.nth(p)
                    alt = pic.get_attribute('alt', timeout=500) or ''
                    src = pic.get_attribute('src', timeout=500) or ''
                    
                    # Skip media thumbnail images
                    if alt == 'Media thumbnail' or 'e15_s150x150' in src:
                        continue
                    
                    if src and ('profile_pic' in src or 'fbcdn.net' in src):
                        notif.profile_pic_urls.append(src)
                        if not notif.profile_pic_url:
                            notif.profile_pic_url = src
                except Exception:
                    pass
            
            # --- 11. Determine section ---
            notif.section = self._get_section_for_item(item)
            
            # --- 12. System notifications ---
            if not notif.usernames:
                text_lower = notif.text.lower()
                if any(kw in text_lower for kw in ['meta', 'instagram', 'learn how', 'privacy', 'your account']):
                    notif.type = 'system'
            
            return notif
            
        except Exception as e:
            self.logger.debug(f"Error parsing item: {e}")
            return None
    
    # ==================== SECTION TRACKING ====================
    
    def _build_section_map(self):
        """
        Finds section headings and creates a map with their y-positions.
        HTML: div[role="heading"] > span → "Yesterday", "This week", etc.
        """
        self._section_map = {}
        try:
            headings = self.page.locator('div[role="heading"]')
            for i in range(headings.count()):
                heading = headings.nth(i)
                text = heading.inner_text(timeout=1000).strip()
                
                if text in self.KNOWN_SECTIONS:
                    box = heading.bounding_box()
                    if box:
                        self._section_map[box['y']] = text
            
            self.logger.debug(f"Section map: {self._section_map}")
        except Exception as e:
            self.logger.debug(f"Error building section map: {e}")
    
    def _get_section_for_item(self, item) -> str:
        """Returns the section name for a notification item (based on y-position)"""
        if not self._section_map:
            return ''
        
        try:
            box = item.bounding_box()
            if not box:
                return ''
            
            item_y = box['y']
            
            # Find the closest section (largest y that is <= item_y)
            sorted_sections = sorted(self._section_map.items(), key=lambda x: x[0])
            current_section = ''
            
            for section_y, section_name in sorted_sections:
                if section_y <= item_y:
                    current_section = section_name
                else:
                    break
            
            return current_section
        except Exception:
            return ''
    
    # ==================== HELPER METHODS ====================
    
    def _detect_type(self, text: str) -> str:
        """Detects notification type based on text content"""
        text_lower = text.lower()
        for pattern, notif_type in self.NOTIFICATION_PATTERNS:
            if re.search(pattern, text_lower):
                return notif_type
        return 'other'
    
    def _clean_text(self, raw_text: str) -> str:
        """
        Cleans raw text:
        - Replaces newlines with spaces
        - Collapses multiple whitespace into single space
        - Strips leading and trailing whitespace
        """
        if not raw_text:
            return ''
        text = raw_text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _scroll_to_load(self, target_count: int, max_scrolls: int = 10) -> int:
        """Scrolls down to load more notifications"""
        for scroll_num in range(max_scrolls):
            items = self.page.locator(self.config.selector_notif_item)
            current = items.count()
            
            if current >= target_count:
                self.logger.debug(f"Reached target: {current} >= {target_count}")
                break
            
            # Scroll down
            self.page.keyboard.press('End')
            time.sleep(random.uniform(1.5, 2.5))
            
            # Check if new items were loaded
            new_count = self.page.locator(self.config.selector_notif_item).count()
            if new_count == current:
                self.logger.debug(f"No more items to load (stuck at {current})")
                break
            
            self.logger.debug(f"Scroll {scroll_num+1}: {current} → {new_count} items")
        
        return self.page.locator(self.config.selector_notif_item).count()
    
    def _count_types(self, notifications: List[NotificationItem]) -> str:
        """Counts notification types → string"""
        counts: Dict[str, int] = {}
        for n in notifications:
            counts[n.type] = counts.get(n.type, 0) + 1
        return ', '.join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda x: -x[1]))
    
    def _count_sections(self, notifications: List[NotificationItem]) -> str:
        """Counts sections → string"""
        counts: Dict[str, int] = {}
        for n in notifications:
            s = n.section or 'Unknown'
            counts[s] = counts.get(s, 0) + 1
        return ', '.join(f"{k}:{v}" for k, v in counts.items())
    
    # ==================== CONVENIENCE METHODS ====================
    
    def get_follows(self, max_count: int = 50, **kwargs) -> List[NotificationItem]:
        """Get only follow notifications"""
        all_notifs = self.read_notifications(max_count=max_count, **kwargs)
        return [n for n in all_notifs if n.type == 'follow']
    
    def get_comment_likes(self, max_count: int = 50, **kwargs) -> List[NotificationItem]:
        """Get only comment like notifications"""
        all_notifs = self.read_notifications(max_count=max_count, **kwargs)
        return [n for n in all_notifs if n.type == 'comment_like']
    
    def get_post_likes(self, max_count: int = 50, **kwargs) -> List[NotificationItem]:
        """Get only post like notifications"""
        all_notifs = self.read_notifications(max_count=max_count, **kwargs)
        return [n for n in all_notifs if n.type == 'post_like']
    
    def get_comments(self, max_count: int = 50, **kwargs) -> List[NotificationItem]:
        """Get only comment notifications"""
        all_notifs = self.read_notifications(max_count=max_count, **kwargs)
        return [n for n in all_notifs if n.type == 'comment']
    
    def get_new_followers_usernames(self, max_count: int = 50, **kwargs) -> List[str]:
        """New followers — returns only username list"""
        follows = self.get_follows(max_count=max_count, **kwargs)
        usernames = []
        for f in follows:
            usernames.extend(f.usernames)
        return usernames
    
    # ==================== FILTER & SUMMARY ====================
    
    def filter_by_type(self, notifications: List[NotificationItem], 
                       notif_type: str) -> List[NotificationItem]:
        """Filter notifications by type"""
        return [n for n in notifications if n.type == notif_type]
    
    def filter_by_section(self, notifications: List[NotificationItem], 
                          section: str) -> List[NotificationItem]:
        """Filter notifications by section (Yesterday, This week, etc.)"""
        return [n for n in notifications if n.section == section]
    
    def filter_by_username(self, notifications: List[NotificationItem], 
                           username: str) -> List[NotificationItem]:
        """Filter notifications by username"""
        return [n for n in notifications if username in n.usernames]
    
    def summary(self, notifications: List[NotificationItem]) -> Dict[str, Any]:
        """
        Generates notification statistics.
        
        Returns:
            {
                'total': 10,
                'by_type': {'comment_like': 4, 'follow': 4, ...},
                'by_section': {'Yesterday': 1, 'This week': 5, ...},
                'unique_users': ['taina.srocha', 'boburjon5931', ...],
                'has_follow_back': ['young_blood_the_gaot247xx', ...],
                'has_following': ['boburjon5931'],
            }
        """
        by_type: Dict[str, int] = {}
        by_section: Dict[str, int] = {}
        unique_users = set()
        follow_back = []
        following = []
        
        for n in notifications:
            by_type[n.type] = by_type.get(n.type, 0) + 1
            section_key = n.section or 'Unknown'
            by_section[section_key] = by_section.get(section_key, 0) + 1
            unique_users.update(n.usernames)
            
            if n.action_button == 'Follow Back':
                follow_back.extend(n.usernames)
            elif n.action_button == 'Following':
                following.extend(n.usernames)
        
        return {
            'total': len(notifications),
            'by_type': dict(sorted(by_type.items(), key=lambda x: -x[1])),
            'by_section': by_section,
            'unique_users': sorted(unique_users),
            'has_follow_back': follow_back,
            'has_following': following,
        }
    
    def to_dicts(self, notifications: List[NotificationItem]) -> List[Dict]:
        """Converts a list of NotificationItems to a list of dicts"""
        return [n.to_dict() for n in notifications]
