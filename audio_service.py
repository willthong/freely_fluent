"""Download audio for flashcards from URLs.

Single responsibility: download audio from Wiktionary OGG/MP3 URLs.
Browser-recorded audio is managed by SessionManager, not this service.
"""

from __future__ import annotations

import httpx


class AudioService:
    """Download audio from URLs."""

    def __init__(self, client: httpx.Client | None = None):
        if client is None:
            self._client = httpx.Client(
                headers={"User-Agent": "Mozilla/5.0 (FreeLyFluent)"},
                timeout=15,
            )
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    def download_audio(self, url: str) -> bytes | None:
        """Download audio from *url*. Returns raw bytes, or None on failure."""
        try:
            response = self._client.get(url)
            if response.status_code != 200:
                return None
            return response.content
        except httpx.RequestError:
            return None

    def close(self) -> None:
        """Clean up the httpx client if we own it."""
        if self._owns_client:
            self._client.close()
