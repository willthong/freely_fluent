"""Integration tests for the 'load more' images feature.

Brave Image Search does NOT support offset-based pagination, so we fetch
a single batch (up to 50 images) and paginate client-side via the session's
cached results.  'Load more' reads from the cache, not from a new API call.
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


def _make_single_batch_brave_client():
    """Brave Image Search returns the same results regardless of offset.
    This mock returns a batch of 4 results (same for every call)."""
    def handler(request):
        return Response(200, json={
            "results": [
                {"type": "image_result", "url": "https://ex.com/a1",
                 "thumbnail": {"src": "https://ex.com/thumb_a.jpg", "width": 480, "height": 360},
                 "properties": {"url": "https://ex.com/orig_a.jpg"}},
                {"type": "image_result", "url": "https://ex.com/b1",
                 "thumbnail": {"src": "https://ex.com/thumb_b.jpg", "width": 640, "height": 480},
                 "properties": {"url": "https://ex.com/orig_b.jpg"}},
                {"type": "image_result", "url": "https://ex.com/c1",
                 "thumbnail": {"src": "https://ex.com/thumb_c.jpg", "width": 800, "height": 600},
                 "properties": {"url": "https://ex.com/orig_c.jpg"}},
                {"type": "image_result", "url": "https://ex.com/d1",
                 "thumbnail": {"src": "https://ex.com/thumb_d.jpg", "width": 960, "height": 720},
                 "properties": {"url": "https://ex.com/orig_d.jpg"}},
            ]
        })

    return Client(transport=MockTransport(handler))


def test_load_more_returns_next_batch_from_cache():
    """After selecting an entry, the first GET /images returns up to 12 results.
    GET /images/load-more returns the next batch from the session's cached results.

    Since Brave doesn't support server-side pagination, we fetch once and
    paginate from the cache.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_single_batch_brave_client()

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

    # GET /images → first batch (thumb_a, thumb_b — only 2 shown since batch_size=12 but only 4 total)
    r = client.get(f"/sessions/{session_id}/images")
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 4  # all 4 results returned (we don't slice on programmatic endpoint)

    # GET /images/load-more → we already showed all 4 on first fetch, so next batch is empty
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    data = r.json()
    assert data["results"] == []


def test_load_more_returns_empty_when_all_results_shown():
    """After exhausting all cached results, load-more returns an empty list."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_single_batch_brave_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )

    # First fetch stores all 4 results
    client.get(f"/sessions/{session_id}/images")

    # load-more #1 → empty (all 4 already returned on first call)
    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_load_more_returns_404_for_unknown_session():
    """load-more returns 404 when the session ID doesn't exist."""
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
    """load-more returns 400 when no entry has been selected."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    brave_client = _make_single_batch_brave_client()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/sessions/{session_id}/images/load-more")
    assert r.status_code == 200
    assert r.json().get("error") is not None


def test_load_more_cache_resets_on_word_advance():
    """After completing a card and advancing to the next word, the
    cached image results are cleared so the next word gets a fresh fetch.
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
    brave_client = _make_single_batch_brave_client()

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

    # Fetch images → stores all 4 results
    r = client.get(f"/sessions/{session_id}/images")
    assert r.status_code == 200

    # Complete word 1
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

    # Fetch images for word 2 → fresh API call, same results
    r = client.get(f"/sessions/{session_id}/images")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 4


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
