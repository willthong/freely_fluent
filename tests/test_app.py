"""Integration tests for the FastAPI app.

Uses TestClient to exercise the public HTTP interface.
Mocks all external dependencies (cantodict DB, Wiktionary, Brave) so
tests are deterministic and require no network.
"""

import httpx
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
    """Create a small fixture DB mimicking cantodict.sqlite schema.

    *entries* is a list of (chinese, jyutping, definition) tuples.
    Defaults to a single "你好" entry if not provided.
    """
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


def test_full_pipeline_session_start_to_export():
    """Critical path: start session → translate → select → image → add →
    wiktionary audio → audio → select → complete → export .apkg.
    """
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
    client = TestClient(app)

    # 1. Start session
    r = client.post("/sessions", json={"words": ["hello"]})
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "hello"
    assert data["current_step"] == "translate"
    session_id = data["session_id"]

    # 2. Get translation entries
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["chinese"] == "你好"
    assert entries[0]["jyutping"] == "nei5 hou2"

    # 3. Select an entry
    r = client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )
    assert r.status_code == 200
    assert r.json()["current_step"] == "image"

    # 4. Get image search results
    r = client.get(f"/sessions/{session_id}/images")
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["thumbnail_url"] == "https://example.com/thumb1.jpg"

    # 5. Add an image
    r = client.post(
        f"/sessions/{session_id}/images",
        json={"result_index": 0},
    )
    assert r.status_code == 200
    assert r.json()["current_step"] == "audio"

    # 6. Fetch Wiktionary audio URL
    r = client.get(f"/sessions/{session_id}/wiktionary-audio")
    assert r.status_code == 200
    assert "url" in r.json()
    assert r.json()["url"].startswith("https://upload.wikimedia.org")

    # 7. Play Wiktionary audio (downloads and streams bytes)
    r = client.get(f"/sessions/{session_id}/audio")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/ogg"
    assert r.content == b"OggS\x00\x00\x00\x00mock audio data"

    # 8. Select audio (assembles card, saves, advances)
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # 9. Export .apkg
    r = client.get("/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["content-disposition"].startswith("attachment")
    assert "cantonese_words.apkg" in r.headers["content-disposition"]
    assert zipfile.is_zipfile(io.BytesIO(r.content))


def test_recording_audio_without_recording_returns_error():
    """select_audio with source 'recording' returns 400 when no recording was submitted."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client()
    brave_client = _make_brave_client()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=wiktionary_client,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # No recording submitted — request recording as source
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "recording"},
    )
    assert r.status_code == 200
    assert r.json().get("error") is not None


def test_translate_no_results_auto_skips_with_message():
    """When a word has no translation entries, the translate endpoint
    auto-skips it and returns a message indicating no results were found.
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

    # Start session with a word that has no results, then one that does
    r = client.post("/sessions", json={"words": ["xyz_nonexistent", "hello"]})
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    # Hit translate — no entries for "xyz_nonexistent" → auto-skip with message
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200
    data = r.json()
    assert data["entries"] == []
    assert "No results found" in data["message"]
    assert data["current_word"] == "hello"
    assert data["current_step"] == "translate"


def test_recording_submit_and_playback():
    """Submit a base64 recording, stream it back for playback, then use it for the card."""
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
    client = TestClient(app)

    # 1. Start session → translate → select → image
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Submit recording (base64)
    import base64
    recording_bytes = b"\x00\x00\x01\x02webm mock recording"
    recording_b64 = base64.b64encode(recording_bytes).decode("ascii")

    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": recording_b64},
    )
    assert r.status_code == 200

    # 3. Playback recording
    r = client.get(f"/sessions/{session_id}/recording")
    assert r.status_code == 200
    assert r.content == recording_bytes

    # 4. Select recording as audio source → card saved
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "recording"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # 5. Card was saved with the recording data
    flashcard = card_store.get_all()[0]
    assert flashcard.audio_data == recording_bytes


def test_translate_no_results_completes_session():
    """When the last word has no translation entries, auto-skip completes
    the session.
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

    # Single word with no results
    r = client.post("/sessions", json={"words": ["xyz_nonexistent"]})
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    r = client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True
    assert "No results found" in data["message"]


def test_recording_preview_then_rerecord():
    """Submit a recording, preview it, decide it's bad, re-record,
    preview the new one, and confirm it's the replacement in the saved card.
    """
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
    client = TestClient(app)

    # 1. Start session → translate → select → image
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Submit first (bad) recording
    import base64
    bad_recording = b"\x00\x00webm BAD recording data"
    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": base64.b64encode(bad_recording).decode("ascii")},
    )
    assert r.status_code == 200

    # 3. Preview first recording — hear it's bad
    r = client.get(f"/sessions/{session_id}/recording")
    assert r.status_code == 200
    assert r.content == bad_recording

    # 4. Re-record with better audio (overwrites)
    good_recording = b"\xff\xffwebm GOOD recording data"
    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": base64.b64encode(good_recording).decode("ascii")},
    )
    assert r.status_code == 200

    # 5. Preview the replacement — now it's the good one
    r = client.get(f"/sessions/{session_id}/recording")
    assert r.status_code == 200
    assert r.content == good_recording

    # 6. Select recording → card saved with the GOOD recording
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "recording"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # 7. Verify the saved card has the replacement recording, not the original
    flashcard = card_store.get_all()[0]
    assert flashcard.audio_data == good_recording
    assert flashcard.audio_data != bad_recording


def test_skip_from_translate_step():
    """Skip from the translate step discards the current word and
    advances to the next word at the translate step.

    Story 3: I want a 'skip word' button at every pipeline step.
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

    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]
    assert r.json()["current_step"] == "translate"

    # Skip from translate step (haven't selected an entry)
    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "goodbye"
    assert data["current_step"] == "translate"
    assert data["completed"] is False


def test_skip_from_image_step():
    """Skip from the image step discards the selected entry and
    advances to the next word at the translate step.

    Story 3: I want a 'skip word' button at every pipeline step.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client()
    brave_client = _make_brave_client()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=wiktionary_client,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    # Translate → select entry
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    assert client.get(f"/sessions/{session_id}/images").status_code == 200

    # Skip from image step — entry is discarded
    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "goodbye"
    assert data["current_step"] == "translate"

    # Verify no card was saved (skip means no flashcard)
    assert card_store.get_all() == []


def test_skip_from_audio_step():
    """Skip from the audio step discards entry, images, and any
    recording — advances to next word at translate step.

    Story 3: I want a 'skip word' button at every pipeline step.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client()
    brave_client = _make_brave_client()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=wiktionary_client,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    # Translate → select entry → add image
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # Submit a recording too — all that work, then skip!
    import base64
    recording_bytes = b"\x00\x00webm mock recording"
    client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": base64.b64encode(recording_bytes).decode("ascii")},
    )

    # Skip from audio step — everything discarded
    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "goodbye"
    assert data["current_step"] == "translate"

    # Verify no card was saved
    assert card_store.get_all() == []


def test_skip_last_word_completes_session():
    """Skipping the last word in the session marks it complete.

    Story 3: I want a 'skip word' button at every pipeline step.
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

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] is None
    assert data["completed"] is True


def test_two_word_pipeline_continues_to_next_word():
    """After completing a card for the first word, the session advances to
    the second word and the user can create another card.

    Story 15: I want to continue creating cards for the next word after
    finishing one, so that I can work through a list in one session.
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

    # ── Start session with two words ──
    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    assert r.status_code == 200
    session_id = r.json()["session_id"]
    assert r.json()["current_word"] == "hello"
    assert r.json()["current_step"] == "translate"

    # ── Word 1: hello ──
    # Translate
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.json()["entries"][0]["chinese"] == "你好"

    # Select entry
    r = client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )
    assert r.json()["current_step"] == "image"

    # Add image
    r = client.post(
        f"/sessions/{session_id}/images",
        json={"result_index": 0},
    )
    assert r.json()["current_step"] == "audio"

    # Select wiktionary audio → card saved, advances
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is False
    assert data["current_word"] == "goodbye"
    assert data["current_step"] == "translate"

    # ── Word 2: goodbye ──
    # Translate
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.json()["entries"][0]["chinese"] == "再見"

    # Select entry
    r = client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "再見"},
    )
    assert r.json()["current_step"] == "image"

    # Add image
    r = client.post(
        f"/sessions/{session_id}/images",
        json={"result_index": 0},
    )
    assert r.json()["current_step"] == "audio"

    # Select wiktionary audio → card saved, completes session
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # ── Verify both flashcards were saved ──
    flashcards = card_store.get_all()
    assert len(flashcards) == 2
    assert flashcards[0].english_word == "hello"
    assert flashcards[0].chinese_characters == "你好"
    assert flashcards[0].jyutping == "nei5 hou2"
    assert flashcards[1].english_word == "goodbye"
    assert flashcards[1].chinese_characters == "再見"
    assert flashcards[1].jyutping == "zoii3 gin3"

    # ── Export should contain 4 Anki cards (2 reversed per flashcard) ──
    r = client.get("/export")
    assert r.status_code == 200
    assert zipfile.is_zipfile(io.BytesIO(r.content))


def test_image_step_renders_html_with_thumbnails():
    """GET /image/{id} renders HTML page with thumbnail images and
    checkboxes after entry selection.

    Story 5: I want to see thumbnail images with checkboxes for multi-select.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    brave_client = _make_brave_client()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session → select entry → image step
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})

    # GET /image/{id} → 200 HTML with thumbnails and checkboxes
    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<img src=" in r.text
    assert "<input type=" in r.text
    assert 'type="checkbox"' in r.text
    # Thumbnail from mock Brave result should appear
    assert "https://example.com/thumb1.jpg" in r.text


def test_submit_multiple_images_advances_to_audio():
    """POST /image/{id} with form data saves all selected images and
    advances session to audio step.

    Story 5: I want to select multiple representative images.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    # Brave client returning 3 results for multi-select
    import httpx

    json_response = {
        "results": [
            {"type": "image_result", "url": "https://example.com/page1",
             "thumbnail": {"src": "https://example.com/thumb1.jpg", "width": 480, "height": 360},
             "properties": {"url": "https://example.com/original1.jpg"}},
            {"type": "image_result", "url": "https://example.com/page2",
             "thumbnail": {"src": "https://example.com/thumb2.jpg", "width": 640, "height": 480},
             "properties": {"url": "https://example.com/original2.jpg"}},
            {"type": "image_result", "url": "https://example.com/page3",
             "thumbnail": {"src": "https://example.com/thumb3.jpg", "width": 800, "height": 600},
             "properties": {"url": "https://example.com/original3.jpg"}},
        ]
    }
    brave_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=json_response)
        )
    )

    # Wiktionary + audio download clients for completing the card
    wiktionary_client = _make_wiktionary_client()
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

    # Start session → select entry → image step
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})

    # POST /image/{id} with form data selecting images 0 and 2
    # Must redirect to /audio/{id} (HTML form contract)
    r = client.post(
        f"/image/{session_id}",
        data={"images": ["0", "2"]},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/audio/" in r.headers["location"]

    # Verify session advanced to audio step and can complete the card
    # (proves images were saved in session — audio select would fail without them)
    r = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    # Verify the card was saved with the images
    assert len(card_store.get_all()) == 1


def test_image_step_no_results_shows_skip():
    """GET /image/{id} when Brave returns empty results shows
    'No images found' message with a skip link.

    Story 5: No results branch in the image step.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    # Brave client that returns empty results
    import httpx

    brave_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": []})
        )
    )

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session → select entry → image step
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})

    # GET /image/{id} with no results → shows skip option
    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert "No images found" in r.text
    assert '/skip' in r.text

    # Follow skip link → POST /sessions/{id}/skip → advances
    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True  # only word in list was skipped


def test_skip_link_get_request_does_not_return_405():
    """The HTML templates use <a href='/sessions/{id}/skip'> for the skip
    link, which sends a GET request. This must not return 405 Method Not
    Allowed — the endpoint must accept GET and redirect to the next step.

    Regression test for: user clicked 'Skip this word' on the image step
    (no images found) and got {"detail":"Method Not Allowed"}.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    brave_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": []})
        )
    )

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session → select entry → image step (no results, shows skip link)
    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    client.get(f"/image/{session_id}")

    # Click skip link → GET /sessions/{id}/skip
    # Bug: this returned 405 because endpoint was POST-only
    r = client.get(f"/sessions/{session_id}/skip", follow_redirects=False)
    assert r.status_code == 303, (
        f"Expected redirect (303) from GET skip, got {r.status_code}. "
        "The skip endpoint must accept GET requests from template <a href> links."
    )
    # Should redirect to translate step for next word
    assert "/translate" in r.headers["location"]
    assert session_id in r.headers["location"]


def test_skip_link_get_redirects_to_completion_when_last_word():
    """When skipping the last word via GET, redirect to the completion page."""
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

    # Single word session
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Click skip link → GET /sessions/{id}/skip → should redirect to completion
    r = client.get(f"/sessions/{session_id}/skip", follow_redirects=False)
    assert r.status_code == 303
    assert "/complete/" in r.headers["location"]
    assert session_id in r.headers["location"]


def test_skip_post_still_returns_json_for_api_clients():
    """POST /sessions/{id}/skip must still return JSON for programmatic clients,
    even after adding GET support.
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

    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    # POST skip → JSON response (existing API contract)
    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "goodbye"
    assert data["current_step"] == "translate"
    assert data["completed"] is False


def test_image_submit_redirects_to_audio_page():
    """POST /image/{id} with form data must redirect to the audio step page,
    not return JSON. The image_step.html template uses a regular <form
    method="post">, so the response must be an HTTP redirect.

    Regression test for: user submitted the image selection form and
    got JSON (\"{\"current_step\":\"audio\",\"current_word\":\"...\"}\")
    instead of being redirected to the audio step HTML page.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    brave_client = _make_brave_client()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        brave_client=brave_client,
        api_key="test-key",
    )
    client = TestClient(app)

    # Start session
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Navigate translate step → select entry
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})

    # Submit image form (mimics browser form POST from image_step.html)
    r = client.post(
        f"/image/{session_id}",
        data={"images": ["0"]},
        follow_redirects=False,
    )
    assert r.status_code == 303, (
        f"Expected redirect (303) from image submit, got {r.status_code}. "
        "POST /image/{id} must redirect to /audio/{id} for HTML form submissions."
    )
    assert "/audio/" in r.headers["location"]
    assert session_id in r.headers["location"]



# ── English search tests ──


def test_image_step_passes_english_word_to_template():
    """The image step template receives the English word for the search button."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()
    brave_client = _make_brave_client()

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

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
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert "hello" in r.text, "English word should appear in the image step HTML"
    assert "Search in English" in r.text, "English search button should be rendered"


def test_english_search_uses_query_param():
    """The research endpoint accepts a custom query and returns results."""
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    def handler(request):
        import httpx
        return httpx.Response(200, json={
            "results": [
                {"type": "image_result", "url": "https://ex.com/en1",
                 "thumbnail": {"src": "https://ex.com/en_thumb1.jpg", "width": 480, "height": 360},
                 "properties": {"url": "https://ex.com/en_orig1.jpg"}},
            ]
        })
    brave_client = httpx.Client(transport=httpx.MockTransport(handler))

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()

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
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "\u4f60\u597d"})
    client.get(f"/image/{session_id}")

    # Research with English query
    r = client.get(f"/image/{session_id}/research", params={"query": "hello"})
    assert r.status_code == 200
    assert "en_thumb1.jpg" in r.text
