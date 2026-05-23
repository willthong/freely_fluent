"""Build genanki reversed cards from flashcards."""

from __future__ import annotations

import hashlib
import os
import tempfile

import genanki

from card_store import Flashcard

_DECK_ID = int.from_bytes(hashlib.sha1(b"cantonese_words").digest()[:4], "little")


class CardGenerator:
    """Assembles flashcards into a self-contained .apkg."""

    def generate_apkg(
        self, flashcards: list[Flashcard], output_path: str
    ) -> int:
        deck = genanki.Deck(_DECK_ID, "cantonese_words")
        model = genanki.BASIC_AND_REVERSED_CARD_MODEL

        media_dir = tempfile.mkdtemp()
        media_files: list[str] = []

        for fc in flashcards:
            audio_path = self._write_media(fc.audio_data, self._guess_audio_ext(fc.audio_data), media_dir)
            image_path = self._write_media(fc.image_data, self._guess_image_ext(fc.image_data), media_dir)

            audio_basename = os.path.basename(audio_path)
            image_basename = os.path.basename(image_path)

            front_field = f"{{{{Audio:{audio_basename}}}}}<br>{fc.jyutping}"
            back_field = f'<img src="{image_basename}"><br>{fc.jyutping}'

            note = genanki.Note(model=model, fields=[front_field, back_field])
            deck.add_note(note)

            media_files.append(audio_path)
            media_files.append(image_path)

        package = genanki.Package(deck, media_files=media_files)
        package.write_to_file(output_path)
        return len(flashcards) * 2

    @staticmethod
    def _write_media(data: bytes, ext: str, media_dir: str) -> str:
        digest = hashlib.sha1(data).hexdigest()
        path = os.path.join(media_dir, f"{digest}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    @staticmethod
    def _guess_audio_ext(data: bytes) -> str:
        if data.startswith(b"OggS"):
            return "ogg"
        if data[:4] == b"\xff\xfb" or data[:4] == b"\xff\xf3":
            return "mp3"
        return "webm"

    @staticmethod
    def _guess_image_ext(data: bytes) -> str:
        if data[:4] == b"\x89PNG":
            return "png"
        if data[:2] == b"\xff\xd8":
            return "jpg"
        if data[:3] == b"GIF":
            return "gif"
        return "png"
