"""Integration tests for the completion screen.

Story 15: I want to see a completion screen after finishing all words in a session.
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
    return TestClient(app), card_store


def test_completion_page_renders():
    """GET /complete/{id} renders the completion screen with a success message.

    Story 15: After finishing all words, I want to see 'All done!'.
    """
    client, _ = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Complete the session (full pipeline)
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})
    client.post(f"/sessions/{session_id}/audio", json={"source": "wiktionary"})

    # Completion page
    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "done" in r.text.lower() or "complete" in r.text.lower() or "finished" in r.text.lower()


def test_completion_page_shows_export_link():
    """Completion page includes a link to export the .apkg file.

    Story 15: I want to export my finished cards.
    """
    client, _ = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Complete the session
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})
    client.post(f"/sessions/{session_id}/audio", json={"source": "wiktionary"})

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert "/export" in r.text or "export" in r.text.lower()


def test_completion_page_shows_cards_summary():
    """Completion page displays a count of cards created in the session.

    Story 15: I want to see how many cards I've made.
    """
    cantodict_path = _make_cantodict_fixture(
        entries=[
            ("你好", "nei5 hou2", "hello; hi; how are you"),
            ("再見", "zoii3 gin3", "goodbye; see you later"),
        ]
    )
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
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    # Word 1
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})
    client.post(f"/sessions/{session_id}/audio", json={"source": "wiktionary"})

    # Word 2
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "再見"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})
    client.post(f"/sessions/{session_id}/audio", json={"source": "wiktionary"})

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert "2" in r.text  # shows 2 cards


def test_confirm_audio_step_redirects_to_complete():
    """After confirming the last word's audio on the audio step page,
    the confirm endpoint returns JSON with completed=True.
    The HTMX frontend handles the redirect to the completion page.

    Story 15: After the last card, I want to land on the completion screen.
    """
    client, _ = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # Confirm audio via HTML step endpoint — returns JSON
    r = client.post(
        f"/audio/{session_id}",
        json={"source": "wiktionary"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True
