"""Server-side session tracking for the card-creation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

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
    ) -> None:
        self._words = words
        self._card_store = card_store
        self._word_index = 0
        self._step_index = 0
        self._selected_entry: dict[str, Any] | None = None
        self._selected_characters: str | None = None
        self._selected_images: list[dict[str, Any]] = []
        self._selected_audio: bytes | None = None
        self._recording: bytes | None = None
        self._image_offset = 0

    @property
    def is_complete(self) -> bool:
        """True when all words have been processed."""
        return self._word_index >= len(self._words)

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
        self, audio: bytes | None = None
    ) -> Union["Flashcard", dict[str, Any], None]:
        """Record the chosen audio, optionally save to CardStore, advance.

        If *audio* is None, uses the saved browser recording (if any).
        When a *card_store* is injected and all fields are present, builds
        a ``Flashcard``, saves it, and returns the saved ``Flashcard``.
        When no *card_store* is injected, returns a card data ``dict``.
        Returns ``None`` when required fields are missing (no save occurs).
        """
        self._selected_audio = audio
        card_data = self._build_card_data()
        self._advance_to_next_word()
        if card_data is None:
            return None
        if self._card_store is not None:
            flashcard = self._build_flashcard(card_data)
            return self._card_store.save_flashcard(flashcard)
        return card_data

    def save_recording(self, data: bytes) -> None:
        """Store a browser recording for the current word."""
        self._recording = data

    def get_recording(self) -> bytes | None:
        """Retrieve the saved browser recording, or None."""
        return self._recording

    def skip(self) -> None:
        """Discard the current word and advance to the next."""
        self._advance_to_next_word()

    def _build_flashcard(self, card_data: dict[str, Any]) -> "Flashcard":
        """Build a Flashcard dataclass from card data dict."""
        # Import at method level to avoid circular import at module load
        from card_store import Flashcard

        first_image = card_data["images"][0]
        image_url = first_image.get("thumbnail_url", first_image.get("url", ""))
        if isinstance(image_url, str):
            image_url = image_url.encode()
        return Flashcard(
            english_word=card_data["english_word"],
            chinese_characters=card_data["chinese_characters"],
            jyutping=card_data["jyutping"],
            image_data=image_url,
            audio_data=card_data["audio"],
        )

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
        return {
            "english_word": self.current_word,
            "chinese_characters": self._selected_entry["chinese"],
            "jyutping": self._selected_entry["jyutping"],
            "images": list(self._selected_images),
            "audio": audio,
        }

    @property
    def image_offset(self) -> int:
        """Current pagination offset for Brave image search."""
        return self._image_offset

    def load_more_images(self, batch_size: int = 12) -> int:
        """Advance the image search offset by *batch_size*. Returns new offset."""
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
