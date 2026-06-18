"""Search for images via the Brave Search API.

Calls Brave's image search endpoint with a Chinese character query,
returns a list of thumbnail URLs with pagination support.

Results are returned as dicts:
    {"thumbnail_url": str, "url": str}
"""

from __future__ import annotations

import httpx


class BraveImageSearch:
    """Search Brave for images matching a query."""

    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key

        if client is None:
            self._client = httpx.Client(
                headers={"User-Agent": "Mozilla/5.0 (FreeLyFluent)"},
                timeout=15,
            )
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    def search(
        self, query: str, count: int = 200
    ) -> list[dict[str, str]]:
        """Search for images matching *query*.

        Brave Image Search does NOT support offset-based pagination, so each
        call returns a fresh snapshot. We use count=200 (the API max) since
        it costs the same as any smaller count — same single API call,
        same token cost. Results are paginated client-side from the cache.

        Returns a list of result dicts with thumbnail_url and url keys.
        """
        try:
            response = self._client.get(
                "https://api.search.brave.com/res/v1/images/search",
                params={"q": query, "count": count},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._api_key,
                },
            )
        except httpx.RequestError:
            return []

        if response.status_code != 200:
            return []

        data = response.json()
        results = data.get("results", [])
        return [
            {
                "thumbnail_url": (img.get("thumbnail") or {}).get("src", ""),
                "url": img.get("properties", {}).get("url", img.get("url", "")),
            }
            for img in results
        ]

    def close(self) -> None:
        """Clean up the httpx client if we own it."""
        if self._owns_client:
            self._client.close()
