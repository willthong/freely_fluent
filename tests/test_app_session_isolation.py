"""Test that _sessions is scoped inside create_app, not module-level.

Story 24: Move `_sessions` module-level mutable state inside the app
factory, so that test runs are isolated and session lifecycle follows
app lifecycle.
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
    """Create a fully wired app for testing."""
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


def test_sessions_isolated_between_app_instances():
    """Two create_app() calls must have independent session stores.
    A session created in app1 must not be visible in app2.
    """
    app1 = _make_app()
    app2 = _make_app()

    client1 = TestClient(app1)
    client2 = TestClient(app2)

    # Create a session in app1
    r = client1.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # That session_id must work in app1
    r = client1.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200

    # Same session_id must NOT work in app2 (different session store)
    r = client2.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 404


def test_sessions_not_leaked_from_previous_test():
    """Sessions created in one test function must not persist into another.
    This verifies there's no module-level _sessions dict leaking state.
    """
    app = _make_app()
    client = TestClient(app)

    # Create a session
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Advance it to image step
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})

    # Now create a FRESH app — it must have no sessions
    fresh_app = _make_app()
    fresh_client = TestClient(fresh_app)

    # The old session_id must be unknown in the fresh app
    r = fresh_client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 404

    # Fresh app must have zero sessions
    r = fresh_client.post("/sessions", json={"words": ["goodbye"]})
    new_id = r.json()["session_id"]
    assert new_id != session_id

    # Only the new session should exist in fresh_app
    r = fresh_client.get(f"/sessions/{new_id}/translate")
    assert r.status_code == 200
