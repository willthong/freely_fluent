"""Unit tests for SessionManager.

Story 21: SessionManager accepts CardStore, completes save-advance.
Story 22: Add unit tests for session_manager.py covering pipeline state,
advancement, skip, load_more_images, recording, and card data building.
"""

import tempfile

import pytest

from card_store import CardStore, CardStoreProtocol
from session_manager import SessionManager


def test_init_sets_translate_step():
    """Fresh session starts at translate step."""
    sm = SessionManager(["hello", "goodbye"])
    assert sm.current_step == "translate"
    assert sm.current_word == "hello"


def test_is_complete_false_on_start():
    """Session is not complete when just started."""
    sm = SessionManager(["hello"])
    assert not sm.is_complete


def test_is_complete_true_after_all_words_processed():
    """Session becomes complete after advancing past all words."""
    sm = SessionManager(["hello"])
    sm.skip()
    assert sm.is_complete


def test_current_word_is_none_when_complete():
    """current_word returns None after session is complete."""
    sm = SessionManager(["hello"])
    sm.skip()
    assert sm.current_word is None


def test_select_entry_advances_to_image_step():
    """select_entry records entry and moves to image step."""
    sm = SessionManager(["hello"])
    entry = {"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"}
    sm.select_entry(entry)
    assert sm.current_step == "image"
    assert sm.selected_characters == "\u4f60\u597d"
    assert sm.selected_entry == entry


def test_add_image_advances_to_audio_step():
    """Adding an image advances to audio step."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    assert sm.current_step == "audio"
    assert len(sm.selected_images) == 1


def test_add_multiple_images():
    """Multiple images accumulate."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img1.jpg"})
    sm.add_image({"thumbnail_url": "https://example.com/img2.jpg"})
    assert len(sm.selected_images) == 2


def test_select_audio_returns_card_data():
    """select_audio returns card data dict when all fields present."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    audio = b"OggS"
    card = sm.select_audio(audio)
    assert card is not None
    assert card["english_word"] == "hello"
    assert card["chinese_characters"] == "\u4f60\u597d"
    assert card["jyutping"] == "nei5 hou2"
    assert card["audio"] == audio


def test_select_audio_advances_to_next_word():
    """select_audio advances to next word after building card."""
    sm = SessionManager(["hello", "goodbye"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.select_audio(b"OggS")
    assert sm.current_word == "goodbye"
    assert sm.current_step == "translate"


def test_select_audio_returns_none_missing_entry():
    """select_audio returns None if no entry selected."""
    sm = SessionManager(["hello"])
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    card = sm.select_audio(b"OggS")
    assert card is None


def test_select_audio_returns_none_missing_images():
    """select_audio returns None if no images selected."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    card = sm.select_audio(b"OggS")
    assert card is None


def test_select_audio_returns_none_missing_audio():
    """select_audio returns None if no audio (downloaded or recorded)."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    card = sm.select_audio(None)
    assert card is None


def test_select_audio_uses_recording_when_download_fails():
    """select_audio falls back to recording if download returns None."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.save_recording(b"\x00\x01webm data")
    card = sm.select_audio(None)
    assert card is not None
    assert card["audio"] == b"\x00\x01webm data"


def test_save_and_get_recording():
    """Browser recording can be saved and retrieved."""
    sm = SessionManager(["hello"])
    data = b"\x00\x01webm data"
    sm.save_recording(data)
    assert sm.get_recording() == data


def test_get_recording_returns_none_by_default():
    """get_recording returns None if no recording saved."""
    sm = SessionManager(["hello"])
    assert sm.get_recording() is None


def test_skip_advances_to_next_word():
    """skip discards current word and moves to next."""
    sm = SessionManager(["hello", "goodbye"])
    sm.skip()
    assert sm.current_word == "goodbye"
    assert sm.current_step == "translate"


def test_skip_resets_selections():
    """skip resets all selections for the new word."""
    sm = SessionManager(["hello", "goodbye"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.save_recording(b"webm data")
    sm.skip()
    assert sm.selected_entry is None
    assert sm.selected_characters is None
    assert len(sm.selected_images) == 0
    assert sm.selected_audio is None
    assert sm.get_recording() is None
    assert sm.image_offset == 0


def test_load_more_images_advances_offset():
    """load_more_images increments offset by batch_size."""
    sm = SessionManager(["hello"])
    new_offset = sm.load_more_images(12)
    assert new_offset == 12
    assert sm.image_offset == 12
    new_offset = sm.load_more_images()
    assert new_offset == 24


def test_load_more_images_returns_offset():
    """load_more_images returns the new offset value."""
    sm = SessionManager(["hello"])
    assert sm.load_more_images(10) == 10


def test_full_pipeline_two_words():
    """Complete pipeline for two words in sequence."""
    sm = SessionManager(["hello", "goodbye"])

    # Process word 1
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img1.jpg"})
    card1 = sm.select_audio(b"OggS")
    assert card1 is not None
    assert card1["english_word"] == "hello"
    assert sm.current_word == "goodbye"

    # Process word 2
    sm.select_entry({"chinese": "\u518d\u89c1", "jyutping": "zaai6 gin3"})
    sm.add_image({"thumbnail_url": "https://example.com/img2.jpg"})
    card2 = sm.select_audio(b"OggS2")
    assert card2 is not None
    assert card2["english_word"] == "goodbye"
    assert sm.is_complete


def test_image_offset_resets_on_advance():
    """image_offset resets when advancing to next word."""
    sm = SessionManager(["hello", "goodbye"])
    sm.load_more_images(12)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.select_audio(b"OggS")
    assert sm.image_offset == 0


def test_steps_constant():
    """STEPS constant defines the pipeline order."""
    assert SessionManager.STEPS == ("translate", "image", "audio")


def test_step_progression():
    """Step advances through translate -> image -> audio."""
    sm = SessionManager(["hello"])
    assert sm.current_step == "translate"
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    assert sm.current_step == "image"
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    assert sm.current_step == "audio"


def test_empty_words_list():
    """Session with empty words list is immediately complete."""
    sm = SessionManager([])
    assert sm.is_complete
    assert sm.current_word is None


def test_single_word_complete_after_skip():
    """Single word session becomes complete after skip."""
    sm = SessionManager(["hello"])
    sm.skip()
    assert sm.is_complete

# ── Story 21: CardStore injection & save-advance ─────────────────────────


def _make_store() -> CardStore:
    """Create a fresh CardStore backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return CardStore(tmp.name)


def test_construction_with_card_store():
    """SessionManager accepts a CardStoreProtocol at construction."""
    sm = SessionManager(["hello"], card_store=_make_store())
    assert sm.current_word == "hello"


def test_select_audio_saves_via_card_store():
    """When card_store is injected, select_audio saves the Flashcard."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    # Should return the saved Flashcard (not a dict)
    from card_store import Flashcard
    assert isinstance(result, Flashcard)
    assert result.id is not None
    # Verify it was actually persisted
    retrieved = store.get_flashcard(result.id)
    assert retrieved is not None
    assert retrieved.english_word == "hello"
    assert retrieved.chinese_characters == "\u4f60\u597d"
    assert retrieved.jyutping == "nei5 hou2"
    assert retrieved.audio_data == b"OggS"


def test_select_audio_saves_image_url_from_first_image():
    """Saved Flashcard image_data is the URL string from first selected image."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.add_image({"thumbnail_url": "https://example.com/img2.jpg"})
    result = sm.select_audio(b"OggS")
    assert result is not None
    assert result.image_data == b"https://example.com/img.jpg"


def test_select_audio_no_save_when_fields_missing():
    """When fields are missing, select_audio returns None and does not save."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    # No entry selected — missing required field
    result = sm.select_audio(b"OggS")
    assert result is None
    assert len(store.get_all()) == 0


def test_select_audio_advances_after_save():
    """After saving, session advances to next word."""
    store = _make_store()
    sm = SessionManager(["hello", "goodbye"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.select_audio(b"OggS")
    assert sm.current_word == "goodbye"
    assert sm.current_step == "translate"


def test_select_audio_backward_compat_no_store():
    """Without card_store, select_audio returns card_data dict."""
    sm = SessionManager(["hello"])
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(b"OggS")
    assert isinstance(result, dict)
    assert result["english_word"] == "hello"


def test_select_audio_backward_compat_no_store_returns_none_when_incomplete():
    """Without card_store, still returns None when fields missing."""
    sm = SessionManager(["hello"])
    result = sm.select_audio(b"OggS")
    assert result is None


def test_full_pipeline_two_words_with_store():
    """Complete pipeline for two words, both saved to CardStore."""
    store = _make_store()
    sm = SessionManager(["hello", "goodbye"], card_store=store)

    # Word 1
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img1.jpg"})
    card1 = sm.select_audio(b"OggS")
    assert card1 is not None
    assert card1.english_word == "hello"

    # Word 2
    sm.select_entry({"chinese": "\u518d\u89c1", "jyutping": "zaai6 gin3"})
    sm.add_image({"thumbnail_url": "https://example.com/img2.jpg"})
    card2 = sm.select_audio(b"OggS2")
    assert card2 is not None
    assert card2.english_word == "goodbye"

    assert sm.is_complete
    assert len(store.get_all()) == 2
    assert store.get_all()[0].english_word == "hello"
    assert store.get_all()[1].english_word == "goodbye"


def test_select_audio_falls_back_to_recording_with_store():
    """When download returns None but recording exists, save from recording."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    sm.save_recording(b"\x00\x01webm data")
    result = sm.select_audio(None)
    assert result is not None
    assert result.audio_data == b"\x00\x01webm data"


def test_select_audio_no_recording_no_save():
    """When no download and no recording, does not save."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({"chinese": "\u4f60\u597d", "jyutping": "nei5 hou2"})
    sm.add_image({"thumbnail_url": "https://example.com/img.jpg"})
    result = sm.select_audio(None)
    assert result is None
    assert len(store.get_all()) == 0
