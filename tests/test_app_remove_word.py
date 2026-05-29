"""Integration tests for removing a word from the session word list.

Feature: User can delete a word they don't want to learn from the active
session. The word list is adjusted and the current position is preserved.
"""

import httpx
from fastapi.testclient import TestClient

from app import create_app
from card_generator import CardGenerator
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary
from brave_image_search import BraveImageSearch
from audio_service import AudioService


def _make_cantodict_fixture(entries=None):
    import sqlite3, tempfile

    if entries is None:
        entries = [("你好", "nei5 hou2", "hello; hi; how are you")]
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE Entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chinese TEXT,
            entry_type INTEGER NOT NULL,
            cantodict_id INTEGER NOT NULL,
            definition TEXT,
            jyutping TEXT
        )
    """)
    for i, (chinese, jyutping, definition) in enumerate(entries, start=100):
        conn.execute(
            "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping) "
            "VALUES (?, 2, ?, ?, ?)",
            (chinese, i, definition, jyutping),
        )
    conn.commit()
    conn.close()
    return tmp.name


def _make_card_store_fixture():
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return tmp.name


def _make_wiktionary_client():
    path = "tests/fixtures/wiktionary_你.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def _make_brave_client():
    json_response = {
        "results": [
            {"type": "image_result", "url": "https://example.com/page1",
             "thumbnail": {"src": "https://example.com/thumb1.jpg", "width": 480, "height": 360},
             "properties": {"url": "https://example.com/original1.jpg"}},
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=json_response))
    return httpx.Client(transport=transport)


def _make_audio_download_client():
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=audio_bytes))
    return httpx.Client(transport=transport)


def test_remove_word_removes_from_session():
    """Removing a word via the API removes it from the session's word list
    and adjusts the current word index appropriately.

    Given a session with words [apple, banana, cherry]:
    - Removing 'cherry' (index 2) while at index 0 leaves current_word='apple'
    - Removing 'apple' (index 0) while at index 0 advances to 'banana'
    - Removing 'banana' (index 1) while at index 0 leaves current_word='apple'
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    wiktionary_client = _make_wiktionary_client()
    brave_client = _make_brave_client()
    audio_download_client = _make_audio_download_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=wiktionary_client,
        brave_client=brave_client,
        audio_download_client=audio_download_client,
        api_key="test-key",
    )
    client = TestClient(app, raise_server_exceptions=False)

    # Start session with 3 words
    r = client.post("/sessions", json={"words": ["apple", "banana", "cherry"]})
    session_id = r.json()["session_id"]
    assert r.json()["current_word"] == "apple"

    # Remove 'cherry' (index 2, future word) → list shrinks, current word unchanged
    r = client.post(f"/sessions/{session_id}/words/2/remove")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "apple"
    assert len(data["words"]) == 2
    assert data["words"] == ["apple", "banana"]

    # Remove 'apple' (index 0, current word) → advances to 'banana'
    r = client.post(f"/sessions/{session_id}/words/0/remove")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "banana"
    assert data["words"] == ["banana"]


def test_remove_word_returns_404_for_invalid_index():
    """Removing a word with an out-of-range index returns 404."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["apple"]})
    session_id = r.json()["session_id"]

    # Index 5 is out of range (only 1 word)
    r = client.post(f"/sessions/{session_id}/words/5/remove")
    assert r.status_code == 404

    # Index -1 is out of range
    r = client.post(f"/sessions/{session_id}/words/-1/remove")
    assert r.status_code == 404


def test_remove_word_returns_404_for_unknown_session():
    """Removing a word from a non-existent session returns 404."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()
    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
    )
    client = TestClient(app)
    r = client.post("/sessions/nonexistent/words/0/remove")
    assert r.status_code == 404


def test_remove_word_completes_session_when_last_word_removed():
    """When the last remaining word is removed, the session is marked complete."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["only_one"]})
    session_id = r.json()["session_id"]
    # Session starts not complete since there's one word to process
    assert r.json()["current_word"] == "only_one"

    # Remove the only word
    r = client.post(f"/sessions/{session_id}/words/0/remove")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] is None
    assert data["is_complete"] is True
    assert data["words"] == []
