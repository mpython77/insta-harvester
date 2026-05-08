"""
Instagram GraphQL Interceptor
Captures /graphql/query responses during profile scroll to build a post data cache.
This eliminates the need to visit each post page individually.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from .logging_config import get_logger


class GraphQLInterceptor:
    """
    Intercepts Instagram GraphQL responses during page scrolling.

    Attach to a Playwright page before scrolling a profile. Every
    /graphql/query response that contains post feed data is parsed and
    stored in `cache` keyed by shortcode.

    Usage:
        interceptor = GraphQLInterceptor(page)
        interceptor.attach()
        # ... scroll the page ...
        interceptor.detach()
        data = interceptor.get("DXzt5k7D9Kw")  # PostCacheEntry or None
    """

    # GraphQL endpoints that carry timeline post data
    FEED_ENDPOINTS = {
        "xdt_api__v1__feed__user_timeline_graphql_connection",
        "xdt_api__v1__media__shortcode__web_info",
    }

    def __init__(self, page):
        self.page = page
        self.logger = get_logger("GraphQLInterceptor")
        # shortcode → raw node dict
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._handler = None

    # ── Public API ──────────────────────────────────────────────────

    def attach(self) -> None:
        """Start listening for GraphQL responses on the attached page."""
        self._handler = self._on_response
        self.page.on("response", self._handler)
        self.logger.debug("GraphQL interceptor attached")

    def detach(self) -> None:
        """Stop listening."""
        if self._handler:
            try:
                self.page.remove_listener("response", self._handler)
            except Exception as e:
                self.logger.warning(f"Interceptor detach warning: {e}")
            self._handler = None
        self.logger.debug(f"GraphQL interceptor detached — {len(self.cache)} posts cached")

    def get(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Return cached raw node for shortcode, or None."""
        return self.cache.get(shortcode)

    def has(self, shortcode: str) -> bool:
        return shortcode in self.cache

    def size(self) -> int:
        return len(self.cache)

    # ── Internal ────────────────────────────────────────────────────

    def _on_response(self, response) -> None:
        """Playwright response handler — called for every network response."""
        try:
            url = response.url
            if "/graphql/query" not in url and "graphql" not in url:
                return
            if response.status != 200:
                return

            try:
                body = response.body()
            except Exception as e:
                self.logger.debug(f"GraphQL intercept body error: {e}")
                return

            if not body:
                return

            data = json.loads(body)
            self._parse(data)

        except Exception:
            # Never crash the scroll loop
            pass

    def _parse(self, data: dict) -> None:
        """Walk the response tree and extract post nodes."""
        if not isinstance(data, dict):
            return

        # Path: items[] at top level
        self._try_items(data)

        outer = data.get("data", {})
        if not isinstance(outer, dict):
            return

        # Path: data.items[]
        self._try_items(outer)

        for key, value in outer.items():
            if key in self.FEED_ENDPOINTS:
                self._extract_from_connection(value)
            elif isinstance(value, dict):
                # Path: data.user.edge_owner_to_timeline_media.edges[].node
                edge_owner = value.get("edge_owner_to_timeline_media")
                if isinstance(edge_owner, dict):
                    self._extract_from_connection(edge_owner)
                # Also try items[] one level down
                self._try_items(value)

    def _extract_from_connection(self, connection: Any) -> None:
        """Handle edges[].node pattern."""
        if not isinstance(connection, dict):
            return

        # edges[].node
        edges = connection.get("edges", [])
        for edge in edges:
            node = edge.get("node") if isinstance(edge, dict) else None
            if isinstance(node, dict):
                self._store_node(node)

        # items[] pattern
        self._try_items(connection)

    def _try_items(self, obj: dict) -> None:
        """Handle items[] pattern at any level."""
        if not isinstance(obj, dict):
            return
        items = obj.get("items", [])
        if not isinstance(items, list):
            return
        for item in items:
            if isinstance(item, dict) and ("pk" in item or "code" in item):
                self._store_node(item)

    def _store_node(self, node: dict) -> None:
        """Parse and store one post node."""
        shortcode = node.get("code") or node.get("shortcode")
        if not shortcode:
            return

        # Already cached — keep existing (first occurrence is freshest)
        if shortcode in self.cache:
            return

        parsed = self._build_entry(node, shortcode)
        if parsed:
            self.cache[shortcode] = parsed
            self.logger.debug(
                f"  cached {shortcode}: {parsed.get('like_count')} likes, "
                f"{parsed.get('taken_at_human', '')[:10]}"
            )

    def _build_entry(self, node: dict, shortcode: str) -> Optional[Dict[str, Any]]:
        """Convert raw node → normalised dict matching PostData fields."""
        try:
            taken_at = node.get("taken_at", 0)
            taken_at_human = ""
            timestamp = ""
            if taken_at:
                dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
                taken_at_human = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                timestamp = dt.strftime("%b %d, %Y")

            # Caption
            cap = node.get("caption") or {}
            caption = cap.get("text", "") if isinstance(cap, dict) else str(cap)

            # Location — full object with coordinates
            loc = node.get("location") or {}
            location_name = loc.get("name", "") if isinstance(loc, dict) else ""
            location_full = {
                "name":      loc.get("name", "")      if isinstance(loc, dict) else "",
                "pk":        str(loc.get("pk", ""))   if isinstance(loc, dict) else "",
                "latitude":  loc.get("lat", 0.0)      if isinstance(loc, dict) else 0.0,
                "longitude": loc.get("lng", 0.0)      if isinstance(loc, dict) else 0.0,
                "address":   loc.get("address", "")   if isinstance(loc, dict) else "",
                "city":      loc.get("city", "")      if isinstance(loc, dict) else "",
            }

            # Like count with fallbacks
            like_count = node.get("like_count", 0)
            if not like_count:
                preview = node.get("edge_media_preview_like") or {}
                like_count = preview.get("count", 0)

            # Media URLs (best quality first)
            media_urls = []
            img = node.get("image_versions2") or {}
            candidates = img.get("candidates", [])
            if candidates:
                media_urls.append(candidates[0].get("url", ""))

            carousel_slides = []
            for slide in node.get("carousel_media", []):
                slide_img = slide.get("image_versions2") or {}
                slide_candidates = slide_img.get("candidates", [])
                if slide_candidates:
                    carousel_slides.append(slide_candidates[0].get("url", ""))

            return {
                "shortcode": shortcode,
                "pk": str(node.get("pk", "")),
                "taken_at": taken_at,
                "taken_at_human": taken_at_human,
                "timestamp": timestamp,
                "like_count": like_count,
                "comment_count": node.get("comment_count", 0),
                "caption": caption,
                "location_name": location_name,
                "location_full": location_full,
                "media_type": node.get("media_type", 0),
                "product_type": node.get("product_type", ""),
                "is_video": node.get("media_type", 0) == 2,
                "has_audio": node.get("has_audio", False),
                "video_duration": node.get("video_duration", 0.0),
                "carousel_media_count": node.get("carousel_media_count", 0),
                "top_likers": node.get("top_likers", []) or [],
                "has_liked": node.get("has_liked", False),
                "like_and_view_counts_disabled": node.get("like_and_view_counts_disabled", False),
                "media_urls": [u for u in media_urls if u],
                "carousel_slides": carousel_slides,
                "accessibility_caption": node.get("accessibility_caption", ""),
                "source": "graphql_interceptor",
            }
        except Exception as e:
            self.logger.debug(f"Failed to build entry for {shortcode}: {e}")
            return None
