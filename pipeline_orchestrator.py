"""Orchestrate the card-creation pipeline.

Concentrates pipeline step logic (translate, image, audio) behind a
deep seam. Routes in app.py call these methods; the orchestrator
coordinates the service layer (CantoDict, Brave, Wiktionary, AudioService)
with SessionManager state transitions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from session_manager import SessionManager
    from cantodict_lookup import CantoneseDictionary
    from brave_image_search import BraveImageSearch
    from wiktionary_audio import WiktionaryAudio
    from audio_service import AudioService
    from card_store import Flashcard


class PipelineOrchestrator:
    """Coordinate pipeline step logic across services and SessionManager.

    Accepts injected service instances for testability.
    Each public method maps to a pipeline step.
    """

    def __init__(
        self,
        cantodict: "CantoneseDictionary",
        brave: "BraveImageSearch",
        wiktionary: "WiktionaryAudio",
        audio_svc: "AudioService",
    ) -> None:
        self._cantodict = cantodict
        self._brave = brave
        self._wiktionary = wiktionary
        self._audio_svc = audio_svc

    def lookup_translations(
        self, session: "SessionManager", word: str
    ) -> list[dict[str, Any]]:
        """Look up Cantonese entries for *word* via CantoDict.

        Results are sorted by:
        1. Standalone match (exact word in definition first, substring-only last)
        2. Chinese character length (ascending — shorter/simpler first)
        3. Views (descending — higher views = more popular first)
        4. Match position (ascending — earlier in definition = more likely primary)

        This shows primary characters first, then popular entries, with
        match position as a fine-tune tiebreaker.
        """
        import re

        entries = self._cantodict.lookup(word)

        # Determine standalone match for each entry
        escaped = re.escape(word)
        boundary_re = re.compile(
            r"(?:^|[\s\[\]\(\)\{\}.,;:!?\"'/\\-])"
            + escaped
            + r"(?:$|[\s\[\]\(\)\{\}.,;:!?\"'/\\-])",
            re.IGNORECASE,
        )

        def sort_key(e):
            definition = e.get("definition", "")
            standalone = 0 if boundary_re.search(definition) else 1
            char_len = len(e.get("chinese", ""))
            views = -(e.get("views", 0) or 0)  # descending
            match = boundary_re.search(definition)
            match_pos = match.start() if match else 999999
            return (standalone, char_len, views, match_pos)

        entries.sort(key=sort_key)
        return entries

    def search_images(
        self, session: "SessionManager", batch_size: int = 200
    ) -> list[dict[str, str]]:
        """Search for images matching the session's selected characters.

        Brave Image Search doesn't support offset pagination, so each call
        gets up to *batch_size* results (default 200, the API max). Results
        are stored in the session for client-side pagination.
        """
        characters = session.selected_characters
        return self._brave.search(characters, count=batch_size)

    def search_images_with_query(
        self, session: "SessionManager", query: str, batch_size: int = 200
    ) -> list[dict[str, str]]:
        """Search for images using a user-supplied *query* string.

        Unlike ``search_images`` which uses the session's selected characters,
        this method uses the caller-provided query. Results replace the
        session's cached image results.
        """
        results = self._brave.search(query, count=batch_size)
        session.store_image_results(results)
        return results

    def fetch_wiktionary_audio_url(
        self, session: "SessionManager"
    ) -> str | None:
        """Fetch the Cantonese OGG audio URL for the session's character."""
        characters = session.selected_characters
        return self._wiktionary.fetch_audio_url(characters)

    def play_audio(
        self, session: "SessionManager", url: str
    ) -> bytes | None:
        """Download audio from *url* via AudioService for playback.

        Persists the downloaded bytes to ``session._selected_audio`` so
        that confirm_audio can reuse them instead of re-fetching Wiktionary
        HTML and re-downloading. This avoids transient failures during
        confirmation (rate limits, timeouts, HTML parse failures).
        """
        audio_bytes = self._audio_svc.download_audio(url)
        if audio_bytes is not None:
            session._selected_audio = audio_bytes
        return audio_bytes

    def confirm_audio(
        self, session: "SessionManager", source: str,
        audio_bytes: bytes | None = None,
        jyutping: str | None = None,
    ) -> "Flashcard" | None:
        """Confirm audio choice, save flashcard via SessionManager, advance.

        *source* is one of ``"wiktionary"`` or ``"recording"``.
        If *audio_bytes* is provided, uses those bytes directly.
        Otherwise resolves from source (recording, pre-played audio, or
        fresh wiktionary download). Recording always takes precedence over
        pre-played audio to avoid using stale bytes from a previous play.
        If *jyutping* is provided, it overrides the entry's jyutping
        (allowing the user to edit tone numbers before confirming).

        Returns the saved Flashcard (or None if fields are incomplete).
        """
        if audio_bytes is None:
            if source == "recording":
                audio_bytes = session.get_recording()
                if audio_bytes is None:
                    return None
            elif source == "wiktionary":
                # Reuse pre-played audio if available (avoid re-download)
                if session.selected_audio is not None:
                    audio_bytes = session.selected_audio
                else:
                    url = self._wiktionary.fetch_audio_url(session.selected_characters)
                    if url is None:
                        return None
                    audio_bytes = self._audio_svc.download_audio(url)
            else:
                return None

        if audio_bytes is None:
            return None
        return session.select_audio(audio_bytes, jyutping=jyutping)
