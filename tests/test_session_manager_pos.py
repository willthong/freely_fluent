"""Tests for part-of-speech propagation through SessionManager.

Covers PRD stories 4, 8, 9:
- Story 4: tickbox to choose whether to include POS on cards
- Story 8: POS extracted from CantoDict flows through to flashcard
- Story 9: completion screen shows POS in summary
"""

import tempfile

from card_store import CardStore, Flashcard
from session_manager import SessionManager


def _make_store() -> CardStore:
    """Create a fresh CardStore backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return CardStore(tmp.name)


def test_pos_flows_from_entry_to_flashcard():
    """When the selected entry has part_of_speech, it flows through
    _build_card_data → _build_flashcard → CardStore."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "part_of_speech": "n",
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert isinstance(result, Flashcard)
    assert result.part_of_speech == "n"


def test_pos_empty_when_entry_has_no_pos():
    """When the entry has no part_of_speech key or empty value,
    the flashcard gets an empty string."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        # No part_of_speech key
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == ""


def test_pos_empty_string_in_entry():
    """When the entry has part_of_speech='', flashcard gets empty string."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "part_of_speech": "",
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == ""


def test_include_pos_false_suppresses_pos():
    """When include_pos=False, part_of_speech is set to empty string
    regardless of what was extracted from the entry."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm._include_pos = False
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "part_of_speech": "v",
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == ""


def test_include_pos_true_includes_pos():
    """When include_pos=True (the default), POS from the entry is included."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm._include_pos = True
    sm.select_entry({
        "chinese": "\u8dd1",
        "jyutping": "pou2",
        "part_of_speech": "v",
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == "v"


def test_include_pos_default_is_true():
    """By default, include_pos is True — POS is included on cards."""
    sm = SessionManager(["hello"])
    assert sm._include_pos is True


def test_set_include_pos():
    """set_include_pos changes the preference."""
    sm = SessionManager(["hello"])
    assert sm._include_pos is True
    sm.set_include_pos(False)
    assert sm._include_pos is False
    sm.set_include_pos(True)
    assert sm._include_pos is True


def test_pos_card_data_without_store():
    """Without card_store, card_data dict includes part_of_speech."""
    sm = SessionManager(["hello"])
    sm.select_entry({
        "chinese": "\u8dd1",
        "jyutping": "pou2",
        "part_of_speech": "v",
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert isinstance(result, dict)
    assert result.get("part_of_speech") == "v"


def test_pos_card_data_suppressed_without_store():
    """Without card_store, include_pos=False suppresses POS in card_data dict."""
    sm = SessionManager(["hello"])
    sm._include_pos = False
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "part_of_speech": "n",
    })
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.get("part_of_speech") == ""
