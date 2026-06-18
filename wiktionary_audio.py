"""Fetch Cantonese (Jyutping) audio URLs from Wiktionary.

Fetches the Wiktionary page for a Chinese character and extracts the
Cantonese pronunciation audio source URL (OGG format).

Audio URLs follow the pattern:
  https://upload.wikimedia.org/wikipedia/commons/.../Yue-{jyutping}.ogg
where `Yue-` is the Cantonese language prefix.

Also matches LL-Q9186 recordings from Wikimedia Commons.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup


class WiktionaryAudio:
    """Fetch and parse Cantonese audio URLs from Wiktionary.

    Accepts an injected httpx client for testability.
    Splits HTTP fetch from HTML parsing into separate methods.
    """

    def __init__(self, client: httpx.Client | None = None):
        if client is None:
            self._client = httpx.Client(
                headers={"User-Agent": "Mozilla/5.0 (FreeLyFluent)"},
                timeout=10,
            )
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    def fetch_html(self, character: str) -> str | None:
        """Fetch the Wiktionary page for *character* and return raw HTML.

        Returns the HTML string, or ``None`` on HTTP or network failure.
        """
        url = f"https://en.wiktionary.org/wiki/{character}"
        try:
            response = self._client.get(url)
            if response.status_code != 200:
                return None
            return response.text
        except (httpx.RequestError, TypeError):
            return None

    def parse_html(self, html: str) -> str | None:
        """Parse Wiktionary HTML and extract the Cantonese OGG audio URL.

        Looks for ``<source>`` tags matching Cantonese audio: either a
        ``Yue-`` prefix (Jyutping) or an ``LL-Q9186-`` prefix (Wikimedia
        Cantonese recording). Excludes ``.ogg.mp3`` transcoded files.

        Returns the full URL string, or ``None`` if no Cantonese audio found.
        """
        soup = BeautifulSoup(html, "html.parser")

        for source in soup.find_all("source"):
            src = source.get("src", "")
            if not src:
                continue
            # Skip transcoded MP3 wrappers around OGG
            if ".ogg.mp3" in src:
                continue
            # Match Cantonese OGG: either Yue- prefix or LL-Q9186- prefix
            if ".ogg" in src and ("Yue-" in src or "LL-Q9186-" in src):
                if src.startswith("//"):
                    src = f"https:{src}"
                return src

        return None

    def fetch_audio_url(self, character: str) -> str | None:
        """Fetch and parse Wiktionary for *character*, return Cantonese OGG URL.

        Convenience method chaining :meth:`fetch_html` and :meth:`parse_html`.
        Returns ``None`` if the page fails to load or no Cantonese audio found.
        """
        html = self.fetch_html(character)
        if html is None:
            return None
        return self.parse_html(html)

    def close(self) -> None:
        """Clean up the httpx client if we own it."""
        if self._owns_client:
            self._client.close()


def fetch_audio_url(
    character: str,
    client: httpx.Client | None = None,
) -> str | None:
    """Fetch Wiktionary page for *character*, extract Cantonese OGG audio URL.

    Backward-compatible convenience function delegating to :class:`WiktionaryAudio`.

    Returns the full URL string, or ``None`` if no Cantonese audio is found
    or the page fails to load.

    When *client* is not provided, a default httpx client is used with a
    browser-like User-Agent header.
    """
    service = WiktionaryAudio(client=client)
    try:
        return service.fetch_audio_url(character)
    finally:
        if client is None:
            service.close()
