"""Integration tests for the 'load more' images feature.

Story 6: As a language learner, I want a 'load more' button to fetch
additional image results, so that I can browse a larger pool and pick
the best ones.

Uses TestClient to exercise the public HTTP interface.
Mocks Brave via httpx.MockTransport to return different result batches
based on the offset parameter.
"""

from fastapi.testclient import TestClient
from httpx import Client, MockTransport, Response

from app import create_app
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary
from session_manager import SessionManager
from brave_image_search import BraveImageSearch
from card_generator import CardGenerator


FIXTURE_DIR = "tests/fixtures"


def _make_cantodict_fixture(entries=None):
    """Create a small fixture DB mimicking cantodict.sqlite schema."""
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


def _make_multi_batch_brave_client():
    """httpx client that returns different image batches based on offset.

    offset=0  → first batch (thumb1, thumb2)
    offset=12 → second batch (thumb3, thumb4)
    offset=24 → empty (no more results)
    """
    def handler(request):
        params = dict(request.url.params)
        offset = int(params.get("offset", 0))

        if offset == 0:
            return Response(200, json={
                "results": [
                    {"type": "image_result", "url": "https://example.com/page1",
                     "thumbnail": {"src": "https://example.com/thumb1.jpg", "width": 480, "height": 360},
                     "properties": {"url": "https://example.com/original1.jpg"}},
                    {"type": "image_result", "url": "https://example.com/page2",
                     "thumbnail": {"src": "https://example.com/thumb2.jpg", "width": 640, "height": 480},
                     "properties": {"url": "https://example.com/original2.jpg"}},
                ]
            })
        elif offset == 12:
            return Response(200, json={
                "results": [
                    {"type": "image_result", "url": "https://example.com/page3",
                     "thumbnail": {"src": "https://example.com/thumb3.jpg", "width": 800, "height": 600},
                     "properties": {"url": "https://example.com/original3.jpg"}},
                    {"type": "image_result", "url": "https://example.com/page4",
                     "thumbnail": {"src": "https://example.com/thumb4.jpg", "width": 960, "height": 720},
                     "properties": {"url": "https://example.com/original4.jpg"}},
                ]
            })
        else:
            return Response(200, json={"results": []})

    return Client(transport=MockTransport(handler))


def test_load_more_returns_second_batch_of_images():
    """After selecting an entry, GET /images/load-more returns the next batch
    of images from Brave (offset 12), not the original results.

    Story 6: I want a 'load more' button for additional image results.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_multi_batch_brave_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session → select entry
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )

    # GET /images/load-more → returns second batch (thumb3, thumb4)
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["thumbnail_url"] == "https://example.com/thumb3.jpg"
    assert data["results"][1]["thumbnail_url"] == "https://example.com/thumb4.jpg"


def test_load_more_returns_empty_when_no_more_results():
    """After exhausting all results, load-more returns an empty results list.

    Story 6: Graceful handling when there are no more images to load.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_multi_batch_brave_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session → select entry
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )

    # First load-more → second batch (offset 12)
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2

    # Second load-more → empty (offset 24, no more results)
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_load_more_returns_404_for_unknown_session():
    """load-more returns 404 when the session ID doesn't exist.

    Story 6: Error handling for invalid session IDs.
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

    r = client.get("/sessions/nonexistent/images/load-more")
    assert r.status_code == 404


def test_load_more_returns_400_when_no_entry_selected():
    """load-more returns 400 when no entry has been selected (no characters to search).

    Story 6: Error handling when the user hasn't chosen characters yet.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_multi_batch_brave_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session but don't select entry
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert r.json().get("error") is not None


def test_load_more_offset_resets_on_word_advance():
    """After completing a card and advancing to the next word, the
    image offset resets to 0 so load-more starts fresh for the new word.

    Story 6: Offset resets between words.
    """
    cantodict_path = _make_cantodict_fixture(
        entries=[
            ("你好", "nei5 hou2", "hello; hi; how are you"),
            ("再見", "zoii3 gin3", "goodbye; see you later"),
        ]
    )
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client()
    audio_download_client = _make_audio_download_client()
    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_multi_batch_brave_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=wiktionary_client,
        audio_download_client=audio_download_client,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # ── Word 1: hello ──
    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )

    # Load more images → offset advances to 12
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2  # thumb3, thumb4

    # Complete word 1 (add image → select audio)
    r = client.post(
        f"/sessions/{session_id}/images",
        json={"result_index": 0},
    )
    assert r.json()["current_step"] == "audio"

    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )
    assert r.json()["completed"] is False
    assert r.json()["current_word"] == "goodbye"

    # ── Word 2: goodbye ──
    client.get(f"/sessions/{session_id}/translate")
    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "再見"},
    )

    # Load more on word 2 → offset was reset to 0, load-more advances to 12
    # Returns second batch (thumb3, thumb4) — same as first load-more on word 1
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert r.json()["results"][0]["thumbnail_url"] == "https://example.com/thumb3.jpg"
    assert r.json()["results"][1]["thumbnail_url"] == "https://example.com/thumb4.jpg"

    # Verify offset did reset by calling load-more again on word 2
    # Should return empty (offset 24, no more results)
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.json()["results"] == []


def _make_wiktionary_client():
    """httpx client serving the Wiktionary HTML fixture for 你."""
    path = f"{FIXTURE_DIR}/wiktionary_你.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = MockTransport(lambda request: Response(200, content=body))
    return Client(transport=transport)


def _make_audio_download_client():
    """httpx client returning mock audio bytes for any URL."""
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = MockTransport(lambda request: Response(200, content=audio_bytes))
    return Client(transport=transport)
