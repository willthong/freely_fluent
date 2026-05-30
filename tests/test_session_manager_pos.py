"""Tests for part-of-speech propagation through SessionManager.

Covers PRD2: manual POS override replaces global toggle.
POS is always blank by default; only an explicit user choice sets it.
"""

import tempfile

from card_store import CardStore, Flashcard
from session_manager import SessionManager


def _make_store() -> CardStore:
    """Create a fresh CardStore backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return CardStore(tmp.name)


def test_pos_empty_by_default():
    """By default, part_of_speech is empty — the user must explicitly pick."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "_cantodict_pos": "n",
        "part_of_speech": "",
    })
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == ""


def test_pos_flows_from_manual_override_to_flashcard():
    """When set_entry_pos() is called, the value flows to the flashcard."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "_cantodict_pos": "n",
        "part_of_speech": "",
    })
    sm.set_entry_pos("v")
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert isinstance(result, Flashcard)
    assert result.part_of_speech == "v"


def test_set_entry_pos_overwrites_previous():
    """Calling set_entry_pos again overwrites the previous value."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u8dd1",
        "jyutping": "pou2",
        "_cantodict_pos": "v",
        "part_of_speech": "",
    })
    sm.set_entry_pos("v")
    sm.set_entry_pos("n")  # overwrite
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == "n"


def test_set_entry_pos_clearing_pos():
    """Setting POS to empty string clears it."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "_cantodict_pos": "n",
        "part_of_speech": "",
    })
    sm.set_entry_pos("v")
    sm.set_entry_pos("")  # clear
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == ""


def test_set_entry_pos_custom_value():
    """Free-form POS values (e.g. 'measure word') are stored correctly."""
    store = _make_store()
    sm = SessionManager(["hello"], card_store=store)
    sm.select_entry({
        "chinese": "\u500b",
        "jyutping": "go3",
        "_cantodict_pos": "",
        "part_of_speech": "",
    })
    sm.set_entry_pos("measure word")
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.part_of_speech == "measure word"


def test_set_entry_pos_no_entry_is_noop():
    """Calling set_entry_pos when no entry is selected is a no-op."""
    sm = SessionManager(["hello"])
    # Should not raise
    sm.set_entry_pos("v")
    assert sm.selected_entry is None


def test_entry_pos_suggestion_returns_cantodict_value():
    """entry_pos_suggestion returns the CantoDict-derived POS for display."""
    sm = SessionManager(["hello"])
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "_cantodict_pos": "n",
        "part_of_speech": "",
    })
    assert sm.entry_pos_suggestion == "n"


def test_entry_pos_suggestion_empty_when_cantodict_has_none():
    """entry_pos_suggestion returns '' when CantoDict found no POS."""
    sm = SessionManager(["hello"])
    sm.select_entry({
        "chinese": "\u54c8\u56c9",
        "jyutping": "haa1 lou3",
        "_cantodict_pos": "",
        "part_of_speech": "",
    })
    assert sm.entry_pos_suggestion == ""


def test_entry_pos_suggestion_empty_when_no_entry():
    """entry_pos_suggestion returns '' when no entry is selected."""
    sm = SessionManager(["hello"])
    assert sm.entry_pos_suggestion == ""


def test_pos_card_data_without_store():
    """Without card_store, card_data dict includes part_of_speech."""
    sm = SessionManager(["hello"])
    sm.select_entry({
        "chinese": "\u8dd1",
        "jyutping": "pou2",
        "_cantodict_pos": "v",
        "part_of_speech": "",
    })
    sm.set_entry_pos("v")
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert isinstance(result, dict)
    assert result.get("part_of_speech") == "v"


def test_pos_card_data_empty_without_store():
    """Without card_store and no explicit POS, card_data gets empty POS."""
    sm = SessionManager(["hello"])
    sm.select_entry({
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "_cantodict_pos": "n",
        "part_of_speech": "",
    })
    sm.advance_to_image()
    sm.add_image({"thumbnail_url": b"\x89PNG"})
    result = sm.select_audio(b"OggS")

    assert result is not None
    assert result.get("part_of_speech") == ""
