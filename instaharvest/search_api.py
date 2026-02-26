"""
Instagram Search API
Search users, hashtags, and places using Instagram's web search.

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

    Uses two methods:
    1. Network interception: Capture search API responses from /web/search/topsearch/
    2. DOM extraction: Parse visible search dropdown results

    Features:
    - Search users, hashtags, and locations
    - Filter by type (all, users, hashtags, places)
    - Extract profile pics, follower counts, verified status
    - Uses existing session for authenticated results
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
            session_data = self._load_session()
            self.setup_browser(session_data)

            # Setup interceptor
            self._setup_search_interceptor()

            # Navigate to Instagram
            self.goto_url(self.config.instagram_base_url.rstrip('/'))
            time.sleep(self.config.page_stability_delay)

            # Type in search and capture results
            self._perform_search(query)

            # Parse intercepted API responses
            result = self._parse_search_results(query, search_type)

            # Fallback: try direct API endpoint via network_client
            if result.total_count == 0:
                result = self._direct_api_search(query, search_type)

            self.logger.info(
                f"Search results: {len(result.users)} users, "
                f"{len(result.hashtags)} hashtags, "
                f"{len(result.places)} places"
            )

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
        finally:
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

    def _setup_search_interceptor(self) -> None:
        """Intercept search API responses"""
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
        """Type search query in Instagram search bar"""
        try:
            # Click search icon/input
            search_selectors = [
                'a[href="/explore/"]',
                'svg[aria-label="Search"]',
                'input[aria-label="Search input"]',
                'input[placeholder*="Search"]',
                'span:text("Search")',
            ]

            for selector in search_selectors:
                try:
                    el = self.page.locator(selector).first
                    if el.count() > 0:
                        el.click()
                        time.sleep(0.5)
                        break
                except Exception:
                    continue

            time.sleep(0.5)

            # Find and type in search input
            input_selectors = [
                'input[aria-label="Search input"]',
                'input[placeholder*="Search"]',
                'input[type="text"]',
            ]

            for selector in input_selectors:
                try:
                    input_el = self.page.locator(selector).first
                    if input_el.count() > 0:
                        input_el.fill('')
                        input_el.type(query, delay=50)
                        time.sleep(1.5)  # Wait for search results
                        return
                except Exception:
                    continue

        except Exception as e:
            self.logger.warning(f"Search input failed: {e}")

    def _parse_search_results(self, query: str, search_type: str) -> SearchResult:
        """Parse intercepted search API responses"""
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

    def _direct_api_search(self, query: str, search_type: str) -> SearchResult:
        """Fallback: Direct API call via network_client"""
        result = SearchResult(query=query)
        try:
            url = f"https://www.instagram.com/web/search/topsearch/?query={query}"
            response = self.network_client.get(url)
            if response.status_code == 200:
                data = response.json()
                # Re-parse using same logic
                self._search_responses = [{'url': url, 'data': data}]
                result = self._parse_search_results(query, search_type)
        except Exception as e:
            self.logger.debug(f"Direct API search failed: {e}")
        return result

    def _load_session(self) -> Dict:
        session_file = Path(self.config.session_file)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}
