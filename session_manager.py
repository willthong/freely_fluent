"""Server-side session tracking for the card-creation pipeline."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, Optional, Union

import httpx

if TYPE_CHECKING:
    from card_store import CardStoreProtocol, Flashcard


class SessionManager:
    """Track session state through the pipeline steps.

    Manages the current word index, pipeline step, and selected choices
    (Entry, images, audio).
    """

    STEPS = ("translate", "image", "audio")

    def __init__(
        self,
        words: list[str],
        card_store: Optional["CardStoreProtocol"] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._words = words
        self._card_store = card_store
        self._http_client = http_client
        self._word_index = 0
        self._step_index = 0
        self._selected_entry: dict[str, Any] | None = None
        self._selected_characters: str | None = None
        self._selected_images: list[dict[str, Any]] = []
        self._selected_audio: bytes | None = None
        self._recording: bytes | None = None
        self._image_offset = 0
        self._image_results: list[dict[str, Any]] = []
        self._session_id: str = ""
        self._include_pos: bool = True

    @property
    def is_complete(self) -> bool:
        """True when all words have been processed."""
        return self._word_index >= len(self._words)

    @property
    def words(self) -> list[str]:
        """All remaining words in the session."""
        return self._words

    @property
    def current_word(self) -> str | None:
        """The English word currently being processed."""
        if self._word_index >= len(self._words):
            return None
        return self._words[self._word_index]

    @property
    def current_step(self) -> str:
        """The current pipeline step name."""
        return self.STEPS[self._step_index]

    @property
    def selected_characters(self) -> str | None:
        """The Chinese characters chosen for the current word."""
        return self._selected_characters

    @property
    def selected_entry(self) -> dict[str, Any] | None:
        """The Entry chosen for the current word."""
        return self._selected_entry

    @property
    def selected_images(self) -> list[dict[str, Any]]:
        """Images chosen for the current word."""
        return self._selected_images

    @property
    def selected_audio(self) -> bytes | None:
        """The chosen audio bytes for the current word."""
        return self._selected_audio

    def select_entry(self, entry: dict[str, Any]) -> None:
        """Record the chosen Entry and advance to the image step."""
        self._selected_entry = entry
        self._selected_characters = entry["chinese"]
        self._step_index = 1

    def add_image(self, image: dict[str, Any]) -> None:
        """Add an image to the selection. Advances to audio step if not yet there."""
        self._selected_images.append(image)
        if self._step_index < 2:
            self._step_index = 2

    def select_audio(
        self, audio: bytes | None = None, jyutping: str | None = None
    ) -> Union["Flashcard", dict[str, Any], None]:
        """Record the chosen audio, optionally save to CardStore, advance.

        If *audio* is None, uses the saved browser recording (if any).
        If *jyutping* is provided, it overrides the entry's original jyutping
        (allowing users to edit tone numbers before confirming).
        When a *card_store* is injected and all fields are present, builds
        a ``Flashcard``, saves it, and returns the saved ``Flashcard``.
        When no *card_store* is injected, returns a card data ``dict``.
        Returns ``None`` when required fields are missing or the image
        cannot be resolved to actual bytes (no save/advance occurs).
        """
        self._selected_audio = audio
        if jyutping is not None and self._selected_entry is not None:
            self._selected_entry["jyutping"] = jyutping
        card_data = self._build_card_data()
        if card_data is None:
            return None
        # Resolve all images, share results between both code paths.
        image_data_list: list[bytes] = []
        for img in card_data["images"]:
            img_url = img.get("thumbnail_url", img.get("url", ""))
            img_bytes = self._resolve_image(img_url)
            if img_bytes is not None:
                image_data_list.append(img_bytes)
        if not image_data_list:
            return None
        self._advance_to_next_word()
        if self._card_store is not None:
            flashcard = self._build_flashcard(card_data, image_data_list)
            return self._card_store.save_flashcard(flashcard)
        return card_data

    def save_recording(self, data: bytes) -> None:
        """Store a browser recording for the current word."""
        self._recording = data

    def get_recording(self) -> bytes | None:
        """Retrieve the saved browser recording, or None."""
        return self._recording

    def set_include_pos(self, value: bool) -> None:
        """Set whether part-of-speech hints should appear on cards."""
        self._include_pos = value

    def skip(self) -> None:
        """Discard the current word and advance to the next."""
        self._advance_to_next_word()

    def remove_word_at(self, index: int) -> None:
        """Remove the word at *index* from the word list.

        Adjusts ``_word_index`` so processing continues correctly:
        - If a processed word (index < _word_index) is removed, decrement.
        - If the current or a future word is removed, the index is
          unchanged (the next word slides into position or the list ends).
        """
        if index < 0 or index >= len(self._words):
            raise IndexError(f"Word index {index} out of range (0-{len(self._words)-1})")
        if index < self._word_index:
            self._word_index -= 1
        del self._words[index]

    def _build_flashcard(self, card_data: dict[str, Any], image_data_list: list[bytes]) -> "Flashcard":
        """Build a Flashcard dataclass from card data dict and pre-resolved image bytes list."""
        # Import at method level to avoid circular import at module load
        from card_store import Flashcard

        return Flashcard(
            english_word=card_data["english_word"],
            chinese_characters=card_data["chinese_characters"],
            jyutping=card_data["jyutping"],
            part_of_speech=card_data.get("part_of_speech", ""),
            image_data=image_data_list,
            audio_data=card_data["audio"],
            session_id=self._session_id,
        )

    def _decode_brave_redirect_url(self, image_url: str) -> str | None:
        """Decode the original image URL from a Brave redirect proxy URL.

        Brave redirect URLs embed the original URL as base64url after the
        ``g:ce/`` segment: ``https://imgs.search.brave.com/<TOKEN>/.../g:ce/<BASE64URL>``.

        Returns ``None`` if *image_url* is not a Brave redirect or decoding fails.
        """
        if not image_url.startswith("https://imgs.search.brave.com/"):
            return None
        try:
            idx = image_url.index("g:ce/")
            b64url = image_url[idx + len("g:ce/"):] if idx != -1 else ""
            if not b64url:
                return None
            decoded = base64.urlsafe_b64decode(b64url + "==")
            return decoded.decode("utf-8")
        except (ValueError, UnicodeDecodeError, IndexError):
            return None

    def _resolve_image(self, image_url: str | bytes) -> bytes | None:
        """Resolve an image reference to actual image bytes.

        If *image_url* is bytes, return as-is (backward compat / test fixtures).

        If *image_url* is a string:
        - For Brave redirect URLs: decode the original URL, try downloading
          from it first, then fall back to the Brave redirect URL.
        - For other URLs: download directly from the URL.

        Returns ``None`` when the URL cannot be resolved (no HTTP client or
        download fails) — the caller must not save a broken card.
        """
        if isinstance(image_url, bytes):
            return image_url
        if not image_url:
            return None
        if self._http_client is None:
            return None

        # Try to decode Brave redirect URL and attempt original first
        original_url = self._decode_brave_redirect_url(image_url)
        if original_url is not None:
            try:
                resp = self._http_client.get(original_url, timeout=15)
                if resp.status_code == 200:
                    return resp.content
            except httpx.RequestError:
                pass

        # Download (original Brave redirect URL or non-Brave URL)
        try:
            resp = self._http_client.get(image_url, timeout=15)
            if resp.status_code == 200:
                return resp.content
        except httpx.RequestError:
            pass

        return None

    def _build_card_data(self) -> dict[str, Any] | None:
        """Assemble card data from the current selections.

        Returns None if required fields are missing.
        """
        if self._selected_entry is None:
            return None
        if not self._selected_images:
            return None
        audio = self._selected_audio or self._recording
        if audio is None:
            return None
        pos = self._selected_entry.get("part_of_speech", "")
        if not self._include_pos:
            pos = ""
        return {
            "english_word": self.current_word,
            "chinese_characters": self._selected_entry["chinese"],
            "jyutping": self._selected_entry["jyutping"],
            "part_of_speech": pos,
            "images": list(self._selected_images),
            "audio": audio,
        }

    @property
    def image_offset(self) -> int:
        """Display cursor: how many image results have been shown so far.

        Unlike the old Brave offset (which Brave ignored in Image Search),
        this is a client-side cursor into ``all_image_results``.  The first
        batch shown is ``results[:image_offset]`` after an initial fetch,
        and ``load_more_images()`` advances the cursor.
        """
        return self._image_offset

    @property
    def all_image_results(self) -> list[dict[str, Any]]:
        """All image search results fetched from Brave (one call per word).

        Brave Image Search has no pagination, so we store all results and
        paginate client-side.
        """
        return self._image_results

    def store_image_results(self, results: list[dict[str, Any]]) -> None:
        """Store results from Brave, replacing any previous results.

        Brave Image Search doesn't support offset-based pagination, so
        we fetch once per word and paginate client-side.
        """
        self._image_results = list(results)

    def load_more_images(self, batch_size: int = 12) -> int:
        """Advance the display cursor by *batch_size*. Returns new cursor."""
        self._image_offset += batch_size
        return self._image_offset

    def _advance_to_next_word(self) -> None:
        """Move to the next word, resetting selections."""
        self._word_index += 1
        self._step_index = 0
        self._selected_entry = None
        self._selected_characters = None
        self._selected_images = []
        self._selected_audio = None
        self._recording = None
        self._image_offset = 0
        self._image_results = []
