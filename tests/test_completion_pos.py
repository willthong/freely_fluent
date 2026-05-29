"""Tests for part-of-speech display on the completion page.

PRD Story 9: completion screen shows POS in card summary.
"""

import tempfile

from fastapi.testclient import TestClient
from card_store import CardStore, Flashcard
from app import create_app


def _mock_cantodict():
    from unittest.mock import Mock
    from cantodict_lookup import CantoneseDictionary
    m = Mock(spec=CantoneseDictionary)
    m.lookup = Mock(return_value=[])
    return m


def _make_store() -> CardStore:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return CardStore(tmp.name)


def test_completion_shows_pos_in_summary():
    """Completion page shows part-of-speech for cards that have it."""
    store = _make_store()
    cantodict = _mock_cantodict()
    app = create_app(cantodict=cantodict, card_store=store)
    client = TestClient(app)

    # Create a session and place a card with POS
    resp = client.post("/sessions", json={"words": ["run"]})
    sid = resp.json()["session_id"]

    store.save_flashcard(
        Flashcard(
            english_word="run",
            chinese_characters="\u8dd1",
            jyutping="pou2",
            part_of_speech="v",
            image_data=[b"\x89PNG"],
            audio_data=b"OggS",
            session_id=sid,
        )
    )

    page = client.get(f"/complete/{sid}")
    assert page.status_code == 200
    html = page.text

    # POS should appear in the summary
    assert "v" in html or "(v)" in html


def test_completion_pos_shown_with_italics():
    """POS is rendered with <em> tags for visual distinction."""
    store = _make_store()
    cantodict = _mock_cantodict()
    app = create_app(cantodict=cantodict, card_store=store)
    client = TestClient(app)

    resp = client.post("/sessions", json={"words": ["big"]})
    sid = resp.json()["session_id"]

    store.save_flashcard(
        Flashcard(
            english_word="big",
            chinese_characters="\u5927",
            jyutping="daai6",
            part_of_speech="adj",
            image_data=[b"\x89PNG"],
            audio_data=b"OggS",
            session_id=sid,
        )
    )

    page = client.get(f"/complete/{sid}")
    assert page.status_code == 200
    html = page.text

    # POS should be in <em> tags
    assert "<em>(adj)</em>" in html


def test_completion_no_pos_shown_when_empty():
    """When part_of_speech is empty, no POS hint appears in the summary."""
    store = _make_store()
    cantodict = _mock_cantodict()
    app = create_app(cantodict=cantodict, card_store=store)
    client = TestClient(app)

    resp = client.post("/sessions", json={"words": ["hello"]})
    sid = resp.json()["session_id"]

    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            part_of_speech="",
            image_data=[b"\x89PNG"],
            audio_data=b"OggS",
            session_id=sid,
        )
    )

    page = client.get(f"/complete/{sid}")
    assert page.status_code == 200
    html = page.text

    # No POS brackets should appear
    assert "(adj)" not in html
    assert "(v)" not in html
    assert "(n)" not in html
