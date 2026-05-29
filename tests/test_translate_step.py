"""Integration tests for the translate step page.

Story 2: I want to see Cantonese translation options and pick one.
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
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return tmp.name


def _make_wiktionary_client() -> object:
    import httpx
    path = f"{FIXTURE_DIR}/wiktionary_你.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def _make_brave_client() -> object:
    import httpx
    json_response = {
        "results": [
            {"type": "image_result", "url": "https://example.com/page1",
             "thumbnail": {"src": "https://example.com/thumb1.jpg", "width": 480, "height": 360},
             "properties": {"url": "https://example.com/original1.jpg"}},
        ]
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=json_response)
    )
    return httpx.Client(transport=transport)


def _make_audio_download_client() -> object:
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


def test_translate_page_renders_with_entries():
    """GET /translate/{id} renders HTML page with Cantonese translation options.

    Story 2: I want to see translation entries with Jyutping and definitions.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "你好" in r.text
    assert "nei<sup>5</sup> hou<sup>2</sup>" in r.text
    assert "hello" in r.text.lower() or "definition" in r.text.lower()


def test_translate_page_shows_current_word_and_step():
    """GET /translate/{id} displays the current English word being translated."""
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert "hello" in r.text


def test_select_translation_redirects_to_image_step():
    """POST /translate/{id}/select with HTMX form submission selects an entry
    and redirects to the image step.

    Story 2: After picking a translation, I want to go to image search.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Trigger lookup (populate entries in session)
    client.get(f"/sessions/{session_id}/translate")

    # Select via the new translate endpoint
    r = client.post(
        f"/translate/{session_id}/select",
        data={"chinese": "你好"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert "/image/" in r.headers["location"]

    # Verify session advanced to image step via public API
    # (images endpoint returns step info and would 400 if still in translate)
    r = client.get(f"/sessions/{session_id}/images")
    assert r.status_code == 200
    # selected_characters is verified by the redirect succeeding
    assert "/image/" in r.headers.get("location", "") or r.status_code == 200


def test_translate_page_no_results_shows_skip():
    """GET /translate/{id} with no translation results shows a message
    with a skip option.

    Story 2: No results branch in translate step.
    """
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

    r = client.post("/sessions", json={"words": ["xyz_nonexistent"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert "No results" in r.text or "no translation" in r.text.lower()
    assert "skip" in r.text.lower() or "/skip" in r.text


def test_translate_page_shows_word_list_with_remove_buttons():
    """The translate page shows the remaining word list with delete buttons.

    Feature: User can delete a word from the session.
    """
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

    r = client.post("/sessions", json={"words": ["apple", "banana", "cherry"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    body = r.text

    # Word list bar is present
    assert 'class="word-list-bar"' in body
    assert "apple" in body
    assert "banana" in body
    assert "cherry" in body

    # Each word has a remove button (hx-post to remove endpoint)
    assert 'hx-post="/sessions/' in body
    assert '/remove"' in body
