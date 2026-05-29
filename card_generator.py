"""Build genanki reversed cards from flashcards.

Custom note type with 4 fields (Jyutping, Images, Audio, PartOfSpeech)
and 2 card templates (Comprehension and Production).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile

import genanki

from card_store import Flashcard
from jyutping_format import format_jyutping

_DECK_ID = int.from_bytes(hashlib.sha1(b"cantonese_words").digest()[:4], "little")

_NOTE_TYPE_ID = int.from_bytes(hashlib.sha1(b"freely_fluent_card").digest()[:4], "little")

_MODEL = genanki.Model(
    _NOTE_TYPE_ID,
    "FreelyFluentCard",
    fields=[
        {"name": "Jyutping"},
        {"name": "Images"},
        {"name": "Audio"},
        {"name": "PartOfSpeech"},
    ],
    templates=[
        {
            "name": "Comprehension",
            "qfmt": "{{Audio}}<br>{{Jyutping}}{{#PartOfSpeech}} <em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}",
            "afmt": "{{FrontSide}}<hr id=\"answer\">{{Images}}<br>{{Jyutping}}{{#PartOfSpeech}} <em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}<br><audio src=\"{{Audio}}\"></audio>",
        },
        {
            "name": "Production",
            "qfmt": "{{Images}}{{#PartOfSpeech}}<br><em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}",
            "afmt": "{{FrontSide}}<hr id=\"answer\">{{Jyutping}}{{#PartOfSpeech}} <em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}<br><audio src=\"{{Audio}}\"></audio>",
        },
    ],
    css="""
    .card {
        font-family: arial, sans-serif;
        font-size: 20px;
        text-align: center;
        color: black;
        background-color: white;
    }
    img {
        max-width: 600px;
        max-height: 400px;
    }
    em {
        color: #666;
        font-size: 16px;
    }
    """,
)


class CardGenerator:
    """Assembles flashcards into a self-contained .apkg."""

    def generate_apkg(
        self, flashcards: list[Flashcard], output_path: str
    ) -> int:
        deck = genanki.Deck(_DECK_ID, "cantonese_words")

        media_dir = tempfile.mkdtemp()
        media_files: list[str] = []

        for fc in flashcards:
            audio_path = self._write_media(fc.audio_data, self._guess_audio_ext(fc.audio_data), media_dir)
            audio_basename = os.path.basename(audio_path)
            media_files.append(audio_path)

            # Write all images to media folder
            image_basenames: list[str] = []
            for img_data in fc.image_data:
                image_path = self._write_media(img_data, self._guess_image_ext(img_data), media_dir)
                image_basenames.append(os.path.basename(image_path))
                media_files.append(image_path)

            jyutping_html = format_jyutping(fc.jyutping)
            all_img_tags = "".join(f'<img src="{bn}">' for bn in image_basenames) if image_basenames else ""
            audio_tag = f'<audio src="{audio_basename}">'
            pos = fc.part_of_speech

            note = genanki.Note(
                model=_MODEL,
                fields=[jyutping_html, all_img_tags, audio_tag, pos],
            )
            deck.add_note(note)

        package = genanki.Package(deck, media_files=media_files)
        package.write_to_file(output_path)
        return len(flashcards) * 2

    @staticmethod
    def _write_media(data: bytes, ext: str, media_dir: str) -> str:
        digest = hashlib.sha1(data).hexdigest()
        # Re-encode Opus audio to Vorbis (Anki's Qt 5 can't play Opus)
        # Handles both OGG/Opus (Wiktionary) and WebM/Opus (browser recordings)
        if ext == "ogg" and CardGenerator._is_opus(data):
            data, ext = CardGenerator._opus_to_vorbis(data, "ogg")
        elif ext == "webm" and CardGenerator._is_webm_opus(data):
            data, ext = CardGenerator._webm_opus_to_vorbis(data)
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

    @staticmethod
    def _is_opus(data: bytes) -> bool:
        """Detect if OGG data contains Opus encoding."""
        return b"OpusHead" in data

    @staticmethod
    def _is_webm_opus(data: bytes) -> bool:
        """Detect if WebM data contains Opus encoding.

        WebM files start with a RIFF header and contain an OpusHead segment.
        """
        return data[:4] == b"RIFF" and b"OpusHead" in data

    @staticmethod
    def _opus_to_vorbis(data: bytes, input_suffix: str) -> tuple[bytes, str]:
        """Convert Opus audio to Vorbis OGG via ffmpeg.

        Returns (converted_data, output_extension). On failure returns
        (original_data, input_extension) so the caller's ext variable is preserved.
        """
        tmp_in = tempfile.NamedTemporaryFile(suffix=input_suffix, delete=False)
        tmp_out = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        converted = CardGenerator._convert_to_vorbis(tmp_in, tmp_out, data)
        if converted is data:
            # Conversion failed — keep original data and original extension
            return (data, "ogg" if input_suffix == ".ogg" else input_suffix.lstrip("."))
        return (converted, "ogg")

    @staticmethod
    def _webm_opus_to_vorbis(data: bytes) -> tuple[bytes, str]:
        """Convert WebM/Opus to Vorbis OGG via ffmpeg. Returns (data, 'ogg')."""
        tmp_in = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        tmp_out = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        converted = CardGenerator._convert_to_vorbis(tmp_in, tmp_out, data)
        if converted is data:
            return (data, "webm")
        return (converted, "ogg")

    @staticmethod
    def _convert_to_vorbis(tmp_in, tmp_out, data: bytes) -> bytes:
        """Shared ffmpeg conversion logic for Opus → Vorbis.

        Returns the converted Vorbis data on success, or the original data on failure.
        """
        try:
            tmp_in.write(data)
            tmp_in.close()
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", tmp_in.name,
                    "-codec:a", "libvorbis",
                    "-qscale:a", "5",
                    tmp_out.name,
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                with open(tmp_out.name, "rb") as f:
                    return f.read()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        finally:
            os.unlink(tmp_in.name)
            if os.path.exists(tmp_out.name):
                os.unlink(tmp_out.name)
        return data  # fallback: return original
