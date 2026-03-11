"""
Instagram Search API
Search users, hashtags, and places using Instagram's web search.

Strategy: Direct API first (fetch topsearch), UI search as fallback.

Usage:
    from instaharvest import SearchAPI, ScraperConfig

    api = SearchAPI(ScraperConfig())
    result = api.search("fashion")
    for user in result.users:
        print(f"@{user['username']} - {user['full_name']}")
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from .base import BaseScraper
from .config import ScraperConfig


@dataclass
class SearchResult:
    """Aggregated search result"""
    query: str = ''
    users: List[Dict[str, Any]] = field(default_factory=list)
    hashtags: List[Dict[str, Any]] = field(default_factory=list)
    places: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def total_count(self) -> int:
        return len(self.users) + len(self.hashtags) + len(self.places)


class SearchAPI(BaseScraper):
    """
    Instagram Search using web endpoints.

    Strategy (v2.10):
    1. PRIMARY: Direct API via browser fetch() — fastest, most reliable
    2. FALLBACK: UI search via DOM interaction — when API blocked

    Features:
    - Search users, hashtags, and locations
    - Filter by type (all, users, hashtags, places)
    - Extract profile pics, follower counts, verified status
    - Uses existing session for authenticated results
    - Automatic fallback from API to UI search
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self._search_responses: List[Dict] = []

    def scrape(self, query: str, search_type: str = 'all') -> SearchResult:
        """
        Scrape/search Instagram (satisfies BaseScraper abstract).
        Alias for search().
        """
        return self.search(query, search_type)

    def search(self, query: str, search_type: str = 'all') -> SearchResult:
        """
        Search Instagram for users, hashtags, and places.

        Args:
            query: Search query string
            search_type: 'all', 'users', 'hashtags', or 'places'

        Returns:
            SearchResult with matched items
        """
        query = query.strip()
        self.logger.info(f"Searching: '{query}' (type: {search_type})")

        result = SearchResult(query=query)
        self._search_responses = []

        try:
            # ═══════ AUTO BROWSER SETUP ═══════
            is_shared_browser = self.page is not None and self.browser is not None
            if not is_shared_browser:
                session_data = self._load_session()
                self.setup_browser(session_data)

                # Navigate to Instagram home first (session warm-up, only standalone)
                base = self.config.instagram_base_url.rstrip('/')
                self.goto_url(base)
                time.sleep(self.config.page_stability_delay)

            # PRIMARY: Direct API via fetch()
            result = self._direct_api_search(query, search_type)

            # FALLBACK: UI search if API returned nothing
            if result.total_count == 0:
                self.logger.info("Direct API returned 0, trying UI search...")
                self._setup_search_interceptor()
                self._perform_search(query)
                result = self._parse_search_results(query, search_type)

            self.logger.info(
                f"Search results: {len(result.users)} users, "
                f"{len(result.hashtags)} hashtags, "
                f"{len(result.places)} places"
            )

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
        finally:
            if not is_shared_browser:
                self.close()

        return result

    def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Search only users"""
        return self.search(query, 'users').users

    def search_hashtags(self, query: str) -> List[Dict[str, Any]]:
        """Search only hashtags"""
        return self.search(query, 'hashtags').hashtags

    def search_places(self, query: str) -> List[Dict[str, Any]]:
        """Search only places"""
        return self.search(query, 'places').places

    # ==================== PRIMARY: Direct API ====================

    def _direct_api_search(self, query: str, search_type: str) -> SearchResult:
        """
        PRIMARY search method: Direct API call through browser's fetch().
        Uses the browser's cookies/session for authenticated results.
        """
        result = SearchResult(query=query)
        encoded = quote(query)

        # Try multiple API endpoints
        endpoints = [
            f"https://www.instagram.com/web/search/topsearch/?context=blended&query={encoded}&include_reel=true",
            f"https://www.instagram.com/web/search/topsearch/?query={encoded}",
        ]

        for url in endpoints:
            try:
                self.logger.info(f"Direct API: {url[:80]}...")

                data = self.page.evaluate("""
                    async (url) => {
                        try {
                            const res = await fetch(url, {
                                method: 'GET',
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'Accept': 'application/json',
                                    'X-IG-App-ID': '936619743392459',
                                },
                                credentials: 'include',
                            });
                            if (res.ok) {
                                const text = await res.text();
                                try { return JSON.parse(text); }
                                catch(e) { return null; }
                            }
                            return null;
                        } catch(e) { return null; }
                    }
                """, url)

                if data and isinstance(data, dict):
                    self._search_responses = [{'url': url, 'data': data}]
                    result = self._parse_search_results(query, search_type)

                    if result.total_count > 0:
                        self.logger.info(
                            f"Direct API success: {len(result.users)} users, "
                            f"{len(result.hashtags)} hashtags, "
                            f"{len(result.places)} places"
                        )
                        return result

            except Exception as e:
                self.logger.debug(f"API endpoint failed: {e}")
                continue

        return result

    # ==================== FALLBACK: UI Search ====================

    def _setup_search_interceptor(self) -> None:
        """Intercept search API responses from network"""
        def handle_response(response):
            try:
                url = response.url
                search_patterns = [
                    '/web/search/topsearch/',
                    '/api/v1/web/search/',
                    'graphql/query',
                ]
                if any(p in url for p in search_patterns):
                    try:
                        body = response.json()
                        self._search_responses.append({
                            'url': url,
                            'data': body,
                        })
                    except Exception:
                        pass
            except Exception:
                pass

        self.page.on('response', handle_response)

    def _perform_search(self, query: str) -> None:
        """Type search query in Instagram search bar (UI fallback)"""
        try:
            self.logger.info("UI fallback: looking for search input...")

            # Step 1: Click the Search link/icon
            clicked = False
            click_selectors = [
                'a[href="/explore/"] span',
                'svg[aria-label="Search"]',
                '[aria-label="Search"]',
                'a[href="/explore/"]',
                'span:text("Search")',
            ]

            for selector in click_selectors:
                try:
                    el = self.page.locator(selector).first
                    if el.count() > 0 and el.is_visible():
                        el.click()
                        clicked = True
                        self.logger.info(f"Clicked search: {selector}")
                        time.sleep(1.0)
                        break
                except Exception:
                    continue

            if not clicked:
                self.logger.warning("Could not find search button, trying keyboard")
                self.page.keyboard.press('Control+k')
                time.sleep(0.5)

            # Step 2: Find and type in search input
            time.sleep(0.5)
            input_selectors = [
                'input[aria-label="Search input"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                'input[type="text"]',
                'input[aria-label*="Search"]',
            ]

            for selector in input_selectors:
                try:
                    input_el = self.page.locator(selector).first
                    if input_el.count() > 0 and input_el.is_visible():
                        input_el.click()
                        time.sleep(0.3)
                        input_el.fill('')
                        input_el.type(query, delay=80)
                        self.logger.info(f"Typed: '{query}' in {selector}")
                        time.sleep(self.config.search_api_response_delay)  # Wait for API response
                        return
                except Exception:
                    continue

            self.logger.warning("Could not find search input")

        except Exception as e:
            self.logger.warning(f"UI search failed: {e}")

    # ==================== Result Parsing ====================

    def _parse_search_results(self, query: str, search_type: str) -> SearchResult:
        """Parse intercepted/fetched search API responses"""
        result = SearchResult(query=query)

        for response in self._search_responses:
            try:
                data = response['data']

                # Parse users
                if search_type in ('all', 'users'):
                    users = data.get('users', [])
                    for u in users:
                        user = u.get('user', u)
                        result.users.append({
                            'username': user.get('username', ''),
                            'full_name': user.get('full_name', ''),
                            'is_verified': user.get('is_verified', False),
                            'is_private': user.get('is_private', False),
                            'profile_pic_url': user.get('profile_pic_url', ''),
                            'follower_count': user.get('follower_count', 0),
                        })

                # Parse hashtags
                if search_type in ('all', 'hashtags'):
                    hashtags = data.get('hashtags', [])
                    for h in hashtags:
                        tag = h.get('hashtag', h)
                        result.hashtags.append({
                            'name': tag.get('name', ''),
                            'post_count': tag.get('media_count', 0),
                            'search_result_subtitle': tag.get('search_result_subtitle', ''),
                        })

                # Parse places
                if search_type in ('all', 'places'):
                    places = data.get('places', [])
                    for p in places:
                        place = p.get('place', p)
                        location = place.get('location', place)
                        result.places.append({
                            'id': str(location.get('pk', '')),
                            'name': location.get('name', place.get('title', '')),
                            'address': location.get('address', ''),
                            'city': location.get('city', ''),
                            'lat': location.get('lat', 0),
                            'lng': location.get('lng', 0),
                        })

            except Exception as e:
                self.logger.debug(f"Parse error: {e}")

        return result

    def _load_session(self) -> Dict:
        session_file = Path(self.config.session_file)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}
