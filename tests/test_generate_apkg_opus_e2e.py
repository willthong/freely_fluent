"""End-to-end: generate_apkg() with Opus audio produces a playable card.

Exercises the full path:
  Flashcard → generate_apkg() → _write_media() → _is_opus() → _opus_to_vorbis()

The resulting .apkg must contain Vorbis-encoded audio (no OpusHead marker)
so that Anki's Qt 5 can play it.
"""

import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from card_generator import CardGenerator
from card_store import Flashcard


# OGG container with Opus codec marker — this is the "problem" format
_FAKE_OPUS_AUDIO = b"OggS\x1bOpusHead\x01\x02fake opus payload data"

# OGG container with Vorbis codec — the target "playable" format
_FAKE_VORBIS_AUDIO = b"OggS\x1bVorbisHead\x01\x02converted vorbis payload"

# A valid PNG image
_FAKE_PNG_IMAGE = b"\x89PNG\r\n\x1a\nfake png image data"


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _read_media(z: zipfile.ZipFile, basename: str) -> bytes:
    """Read a media file from the .apkg by its basename.

    genanki 0.13.1 stores media with numeric index keys ("0", "1", ...)
    and a JSON manifest at "media" mapping index → basename.
    We reverse that mapping to find the right zip entry.
    """
    manifest = json.loads(z.read("media"))  # {"0": "abc123.ogg", "1": "def456.png"}
    idx_to_name = {int(k): v for k, v in manifest.items()}
    name_to_idx = {v: str(k) for k, v in idx_to_name.items()}
    idx = name_to_idx[basename]
    return z.read(idx)


def test_generate_apkg_with_opus_audio_produces_playable_card():
    """Opus audio in a Flashcard is re-encoded to Vorbis during generate_apkg(),
    producing an .apkg whose media contains playable Vorbis audio.

    This exercises the full path:
      Flashcard → generate_apkg() → _write_media() → _is_opus() → _opus_to_vorbis()
    """
    generator = CardGenerator()

    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="你好",
        jyutping="nei5 hou2",
        image_data=_FAKE_PNG_IMAGE,
        audio_data=_FAKE_OPUS_AUDIO,
    )

    # Mock subprocess.run to simulate ffmpeg converting Opus → Vorbis
    def mock_subprocess_run(*args, **kwargs):
        # args[0] is the command list; last element is the output path
        out_path = args[0][-1]
        with open(out_path, "wb") as f:
            f.write(_FAKE_VORBIS_AUDIO)
        return MagicMock(returncode=0)

    with patch("card_generator.subprocess.run", side_effect=mock_subprocess_run):
        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
            path = tmp.name

        count = generator.generate_apkg([flashcard], path)

    try:
        # 1. Reversed pair produced
        assert count == 2

        # 2. Valid .apkg (zip with collection database and media manifest)
        assert zipfile.is_zipfile(path)

        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()
            assert "collection.anki2" in names
            assert "media" in names  # JSON manifest

            # 3. Audio .ogg in the .apkg contains converted Vorbis data,
            #    not the original Opus data. The filename uses SHA1 of the
            #    ORIGINAL Opus bytes (as written by _write_media), but the
            #    CONTENT is the Vorbis output from _opus_to_vorbis().
            audio_basename = f"{_sha1(_FAKE_OPUS_AUDIO)}.ogg"
            audio_content = _read_media(z, audio_basename)
            assert audio_content == _FAKE_VORBIS_AUDIO, (
                "Audio in .apkg should be the converted Vorbis data, "
                "not the original Opus data"
            )

            # 4. Confirm no OpusHead marker in the stored audio — Anki would fail
            assert b"OpusHead" not in audio_content

            # 5. Image passes through unchanged (no conversion for PNG)
            image_basename = f"{_sha1(_FAKE_PNG_IMAGE)}.png"
            image_content = _read_media(z, image_basename)
            assert image_content == _FAKE_PNG_IMAGE

            # 6. Card fields reference the correct media basenames and jyutping
            tmp_dir = tempfile.mkdtemp()
            db_path = z.extract("collection.anki2", tmp_dir)
            conn = sqlite3.connect(db_path)

            fields = conn.execute("SELECT flds FROM notes").fetchone()[0].split("\x1f")
            conn.close()

            # One field has Audio tag, the other has img tag
            audio_field = next(f for f in fields if '<audio src=' in f)
            image_field = next(f for f in fields if "img src=" in f)

            assert audio_basename in audio_field
            assert image_basename in image_field
            assert "nei<sup>5</sup> hou<sup>2</sup>" in audio_field
            assert "nei<sup>5</sup> hou<sup>2</sup>" in image_field

            # 7. English words and Chinese characters never appear on the card face
            for field in fields:
                assert "hello" not in field
                assert "你好" not in field

    finally:
        if os.path.exists(path):
            os.unlink(path)

    # If we got here, the .apkg has playable Vorbis audio — card is good for Anki.
