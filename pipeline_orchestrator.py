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
        """Look up Cantonese entries for *word* via CantoDict."""
        return self._cantodict.lookup(word)

    def search_images(
        self, session: "SessionManager", batch_size: int = 12, offset: int = 0
    ) -> list[dict[str, str]]:
        """Search for images matching the session's selected characters.

        Uses the session's current image_offset unless *offset* is
        explicitly provided.
        """
        offset = offset or session.image_offset
        characters = session.selected_characters
        return self._brave.search(characters, count=batch_size, offset=offset)

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
        self, session: "SessionManager", source: str, audio_bytes: bytes | None = None
    ) -> "Flashcard" | None:
        """Confirm audio choice, save flashcard via SessionManager, advance.

        *source* is one of ``"wiktionary"`` or ``"recording"``.
        If *audio_bytes* is provided, uses those bytes directly.
        Otherwise resolves from source (recording, pre-played audio, or
        fresh wiktionary download). Recording always takes precedence over
        pre-played audio to avoid using stale bytes from a previous play.

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
        return session.select_audio(audio_bytes)
