"""Integration tests for session lifecycle endpoints.

Story 23: Add HTTP endpoints for session lifecycle management — list,
get details, and delete sessions. Enables better UX for multi-word
sessions.
"""

import sqlite3
import tempfile

from fastapi.testclient import TestClient

from app import create_app
from card_generator import CardGenerator
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary


FIXTURE_DIR = "tests/fixtures"


def _make_cantodict_fixture(entries=None):
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


def _make_card_store_fixture():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return tmp.name


def _make_wiktionary_client():
    import httpx
    path = f"{FIXTURE_DIR}/wiktionary_你.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def _make_brave_client():
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


def _make_audio_download_client():
    import httpx
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    return httpx.Client(transport=transport)


def _make_app():
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()
    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    return create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=_make_wiktionary_client(),
        brave_client=_make_brave_client(),
        audio_download_client=_make_audio_download_client(),
        api_key="test-key",
    )


def test_list_sessions_empty():
    """GET /sessions returns empty list when no sessions exist."""
    app = _make_app()
    client = TestClient(app)
    r = client.get("/sessions")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_returns_active_sessions():
    """GET /sessions returns list of active session summaries."""
    app = _make_app()
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    sid1 = r.json()["session_id"]

    r = client.post("/sessions", json={"words": ["goodbye", "thanks"]})
    sid2 = r.json()["session_id"]

    r = client.get("/sessions")
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 2

    # Find our sessions
    ids = [s["id"] for s in sessions]
    assert sid1 in ids
    assert sid2 in ids

    # Verify session details
    for s in sessions:
        assert "id" in s
        assert "current_word" in s
        assert "current_step" in s


def test_get_session_details():
    """GET /sessions/{id} returns full session details."""
    app = _make_app()
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    sid = r.json()["session_id"]

    r = client.get(f"/sessions/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == sid
    assert data["words"] == ["hello"]
    assert data["current_word"] == "hello"
    assert data["current_step"] == "translate"
    assert data["is_complete"] is False


def test_get_session_not_found():
    """GET /sessions/{id} returns 404 for unknown session."""
    app = _make_app()
    client = TestClient(app)
    r = client.get("/sessions/nonexistent")
    assert r.status_code == 404


def test_delete_session():
    """DELETE /sessions/{id} removes a session."""
    app = _make_app()
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    sid = r.json()["session_id"]

    r = client.delete(f"/sessions/{sid}")
    assert r.status_code in (200, 204)

    # Verify session is gone
    r = client.get(f"/sessions/{sid}")
    assert r.status_code == 404

    # Verify list no longer contains it
    r = client.get("/sessions")
    assert len(r.json()) == 0


def test_delete_nonexistent_session():
    """DELETE /sessions/{id} returns 404 for unknown session."""
    app = _make_app()
    client = TestClient(app)
    r = client.delete("/sessions/nonexistent")
    assert r.status_code == 404


def test_session_shows_complete_after_pipeline():
    """Session is_complete reflects pipeline completion."""
    app = _make_app()
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    sid = r.json()["session_id"]

    # Complete the full pipeline: translate → entry → image → audio
    client.get(f"/sessions/{sid}/translate")
    client.post(f"/sessions/{sid}/entries", json={"chinese": "\u4f60\u597d"})
    client.post(f"/sessions/{sid}/images", json={"result_index": 0})
    r = client.post(
        f"/sessions/{sid}/audio",
        json={"source": "wiktionary"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # Check session status
    r = client.get(f"/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["is_complete"] is True
