"""Opus detection and Vorbis re-encoding in CardGenerator."""

import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

from card_generator import CardGenerator
from card_store import Flashcard

# Minimal OGG-like bytes containing the OpusHead marker
_FAKE_OPUS_DATA = b"OggS\x1bOpusHead\x01\x02fakeopuspayload"
# OGG audio without Opus marker (Vorbis-like)
_FAKE_VORBIS_DATA = b"OggS\x1bVorbisHead\x01\x02fakevorbispayload"
# WebM-like bytes with RIFF header and OpusHead marker
_FAKE_WEBM_OPUS_DATA = b"RIFF\x1bOpusHead\x01\x02fakeopuspayloadinwebm"
# WebM-like bytes without Opus (Vorbis in WebM)
_FAKE_WEBM_VORBIS_DATA = b"RIFF\x1bVorbisHead\x01\x02fakevorbispayloadinwebm"


# ---------------------------------------------------------------------------
# _is_opus
# ---------------------------------------------------------------------------


def test_is_opus_returns_true_for_opus_data():
    """Opus detection: data containing OpusHead is recognised as Opus."""
    assert CardGenerator._is_opus(_FAKE_OPUS_DATA) is True


def test_is_opus_returns_false_for_vorbis_data():
    """Opus detection: OGG data without OpusHead is not treated as Opus."""
    assert CardGenerator._is_opus(_FAKE_VORBIS_DATA) is False


# ---------------------------------------------------------------------------
# _opus_to_vorbis — fallback paths
# ---------------------------------------------------------------------------


def test_opus_to_vorbis_fallback_when_ffmpeg_missing():
    """When ffmpeg is not found, Opus data is returned unchanged with original extension."""
    with patch("card_generator.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("ffmpeg not installed")
        data, ext = CardGenerator._opus_to_vorbis(_FAKE_OPUS_DATA, "ogg")
    assert data is _FAKE_OPUS_DATA
    assert ext == "ogg"


def test_opus_to_vorbis_fallback_when_ffmpeg_times_out():
    """When ffmpeg times out, Opus data is returned unchanged with original extension."""
    with patch("card_generator.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 30)
        data, ext = CardGenerator._opus_to_vorbis(_FAKE_OPUS_DATA, "ogg")
    assert data is _FAKE_OPUS_DATA
    assert ext == "ogg"


# ---------------------------------------------------------------------------
# _opus_to_vorbis — success path
# ---------------------------------------------------------------------------


def test_opus_to_vorbis_converts_on_success():
    """When ffmpeg converts successfully, returned data is the converted output with 'ogg' ext."""
    converted_data = b"OggS\x1bVorbisHead converted data here"

    def write_output_to_stdout(*args, **kwargs):
        # args[0] is the command list; last element is the output path
        out_path = args[0][-1]
        with open(out_path, "wb") as f:
            f.write(converted_data)
        return MagicMock(returncode=0)

    with patch("card_generator.subprocess.run", side_effect=write_output_to_stdout):
        data, ext = CardGenerator._opus_to_vorbis(_FAKE_OPUS_DATA, "ogg")
    assert data == converted_data
    assert data is not _FAKE_OPUS_DATA
    assert ext == "ogg"


# ---------------------------------------------------------------------------
# _write_media — Opus re-encoding path
# ---------------------------------------------------------------------------


def test_write_media_re_encodes_opus_audio():
    """OGG audio detected as Opus is re-encoded to Vorbis before writing."""
    converted_data = b"OggS converted vorbis output"

    def mock_opus_to_vorbis(data, input_suffix):
        return (converted_data, "ogg")

    with patch.object(CardGenerator, "_opus_to_vorbis", mock_opus_to_vorbis):
        media_dir = tempfile.mkdtemp()
        path = CardGenerator._write_media(_FAKE_OPUS_DATA, "ogg", media_dir)

    # The file on disk should contain the converted data, not the original
    with open(path, "rb") as f:
        assert f.read() == converted_data
    # Extension should be .ogg (Vorbis), not original
    assert path.endswith(".ogg")


def test_write_media_skips_re_encoding_for_vorbis():
    """OGG audio that is already Vorbis is written as-is without conversion."""
    with patch.object(CardGenerator, "_opus_to_vorbis") as mock_convert:
        media_dir = tempfile.mkdtemp()
        CardGenerator._write_media(_FAKE_VORBIS_DATA, "ogg", media_dir)
    # _opus_to_vorbis should never be called for non-Opus data
    mock_convert.assert_not_called()


# ---------------------------------------------------------------------------
# _guess_audio_ext and _guess_image_ext — default branches
# ---------------------------------------------------------------------------


def test_guess_audio_ext_returns_webm_for_unknown_bytes():
    """Unknown audio bytes default to webm extension."""
    unknown_data = b"some_unknown_audio_bytes_here"
    assert CardGenerator._guess_audio_ext(unknown_data) == "webm"


def test_guess_image_ext_returns_png_for_unknown_bytes():
    """Unknown image bytes default to png extension."""
    unknown_data = b"some_unknown_image_bytes_here"
    assert CardGenerator._guess_image_ext(unknown_data) == "png"


# ---------------------------------------------------------------------------
# _is_webm_opus
# ---------------------------------------------------------------------------


def test_is_webm_opus_returns_true_for_webm_opus():
    """WebM Opus detection: RIFF header + OpusHead is recognised as WebM/Opus."""
    assert CardGenerator._is_webm_opus(_FAKE_WEBM_OPUS_DATA) is True


def test_is_webm_opus_returns_false_for_webm_vorbis():
    """WebM Opus detection: WebM without OpusHead is not treated as Opus."""
    assert CardGenerator._is_webm_opus(_FAKE_WEBM_VORBIS_DATA) is False


def test_is_webm_opus_returns_false_for_non_webm():
    """WebM Opus detection: non-RIFF data is not treated as WebM/Opus."""
    assert CardGenerator._is_webm_opus(_FAKE_OPUS_DATA) is False


# ---------------------------------------------------------------------------
# _webm_opus_to_vorbis
# ---------------------------------------------------------------------------


def test_webm_opus_to_vorbis_converts_on_success():
    """When ffmpeg converts WebM/Opus successfully, returns Vorbis data with 'ogg' ext."""
    converted_data = b"OggS\x1bVorbisHead converted webm to ogg"

    def write_output_to_stdout(*args, **kwargs):
        out_path = args[0][-1]
        with open(out_path, "wb") as f:
            f.write(converted_data)
        return MagicMock(returncode=0)

    with patch("card_generator.subprocess.run", side_effect=write_output_to_stdout):
        data, ext = CardGenerator._webm_opus_to_vorbis(_FAKE_WEBM_OPUS_DATA)
    assert data == converted_data
    assert ext == "ogg"


def test_webm_opus_to_vorbis_fallback_when_ffmpeg_missing():
    """When ffmpeg is not found, WebM/Opus data is returned unchanged with 'webm' ext."""
    with patch("card_generator.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("ffmpeg not installed")
        data, ext = CardGenerator._webm_opus_to_vorbis(_FAKE_WEBM_OPUS_DATA)
    assert data is _FAKE_WEBM_OPUS_DATA
    assert ext == "webm"


# ---------------------------------------------------------------------------
# _write_media — WebM/Opus re-encoding path
# ---------------------------------------------------------------------------


def test_write_media_re_encodes_webm_opus():
    """WebM audio detected as Opus is re-encoded to Vorbis OGG before writing."""
    converted_data = b"OggS converted webm to ogg"

    def mock_webm_opus_to_vorbis(data):
        return (converted_data, "ogg")

    with patch.object(CardGenerator, "_webm_opus_to_vorbis", mock_webm_opus_to_vorbis):
        media_dir = tempfile.mkdtemp()
        path = CardGenerator._write_media(_FAKE_WEBM_OPUS_DATA, "webm", media_dir)

    with open(path, "rb") as f:
        assert f.read() == converted_data
    assert path.endswith(".ogg")


def test_write_media_skips_webm_vorbis():
    """WebM audio that is already Vorbis is written as-is without conversion."""
    with patch.object(CardGenerator, "_webm_opus_to_vorbis") as mock_convert:
        media_dir = tempfile.mkdtemp()
        CardGenerator._write_media(_FAKE_WEBM_VORBIS_DATA, "webm", media_dir)
    mock_convert.assert_not_called()

