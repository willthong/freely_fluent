"""Integration tests for the index (home) page.

Story 1: I want to paste a list of English words to start a session.
"""

import io
import sqlite3
import tempfile
import zipfile

from fastapi.testclient import TestClient

from app import create_app
from card_generator import CardGenerator
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary
from session_manager import SessionManager
from brave_image_search import BraveImageSearch
from audio_service import AudioService
from wiktionary_audio import fetch_audio_url


FIXTURE_DIR = "tests/fixtures"


def _make_cantodict_fixture(entries: list[tuple[str, str, str]] | None = None) -> str:
    """Create a small fixture DB mimicking cantodict.sqlite schema."""
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
            views INTEGER DEFAULT 0,
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


def _make_card_store_fixture() -> str:
    """Create an empty temp DB for card persistence."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return tmp.name


def _make_wiktionary_client() -> object:
    """httpx client serving the Wiktionary HTML fixture for 你."""
    import httpx

    path = f"{FIXTURE_DIR}/wiktionary_你.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def _make_brave_client() -> object:
    """httpx client returning mock Brave image search results."""
    import httpx

    json_response = {
        "results": [
            {
                "type": "image_result",
                "url": "https://example.com/page1",
                "thumbnail": {"src": "https://example.com/thumb1.jpg", "width": 480, "height": 360},
                "properties": {"url": "https://example.com/original1.jpg"},
            }
        ]
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=json_response)
    )
    return httpx.Client(transport=transport)


def _make_audio_download_client() -> object:
    """httpx client returning mock audio bytes for any URL."""
    import httpx

    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    return httpx.Client(transport=transport)


def _make_app():
    """Create a fully configured app with all dependencies injected."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()
    wiktionary_client = _make_wiktionary_client()
    brave_client = _make_brave_client()
    audio_download_client = _make_audio_download_client()
    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=wiktionary_client,
        brave_client=brave_client,
        audio_download_client=audio_download_client,
        api_key="test-key",
    )
    return TestClient(app)


def test_index_page_renders_with_textarea():
    """GET / renders the home page with a textarea for pasting words.

    Story 1: I want to paste a linebreak-separated list of English words.
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<textarea" in r.text
    assert 'placeholder=' in r.text
    assert 'type="submit"' in r.text or "<button" in r.text


def test_submit_words_creates_session_redirects_to_translate():
    """POST /words with a form submission creates a session and redirects to
    the translate step.

    Story 1: After pasting words, I want to click 'Start' and go to translation.
    """
    client = _make_app()
    r = client.post("/words", data={"words": "hello\ngoodbye"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/translate/" in r.headers["location"]

    # Extract session_id from redirect location
    location = r.headers["location"]
    session_id = location.split("/translate/")[1]
    assert len(session_id) > 0

    # Verify the session was created with correct words via translate endpoint
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200
    assert r.json()["current_word"] == "hello"
    assert len(r.json()["entries"]) == 1


def test_submit_single_word_creates_session():
    """POST /words with a single word creates a session and redirects to translate.

    Story 1: Single word input.
    """
    client = _make_app()
    r = client.post("/words", data={"words": "hello"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    session_id = r.headers["location"].split("/translate/")[1]

    # Verify via translate endpoint
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200
    assert r.json()["current_word"] == "hello"


def test_submit_empty_words_shows_error():
    """POST /words with empty input shows an error message.

    Story 1: Empty input validation.
    """
    client = _make_app()
    r = client.post("/words", data={"words": ""}, follow_redirects=False)
    # Should re-render the form with an error, not redirect
    assert r.status_code == 200
    assert "error" in r.text.lower() or "no words" in r.text.lower()
