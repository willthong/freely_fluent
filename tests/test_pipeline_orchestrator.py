"""Tracer-bullet test for Story 20: Extract PipelineOrchestrator from app.py.

One test → one implementation → repeat.
"""

import httpx
import pytest

from pipeline_orchestrator import PipelineOrchestrator


def _make_wiktionary_client():
    """httpx client serving the Wiktionary HTML fixture for 你."""
    path = "tests/fixtures/wiktionary_你.html"
    with open(path, encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=body)
    )
    return httpx.Client(transport=transport)


def _make_brave_client():
    """httpx client returning mock Brave image search results."""
    json_response = {
        "results": [
            {
                "type": "image_result",
                "url": "https://example.com/page1",
                "thumbnail": {
                    "src": "https://example.com/thumb1.jpg",
                    "width": 480,
                    "height": 360,
                },
                "properties": {
                    "url": "https://example.com/original1.jpg",
                },
            }
        ]
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=json_response)
    )
    return httpx.Client(transport=transport)


def _make_audio_download_client():
    """httpx client returning mock audio bytes for any URL."""
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    return httpx.Client(transport=transport)


def test_full_pipeline_orchestrate_one_word():
    """Pipeline orchestrator coordinates lookup → search → add → audio
    for a single word through SessionManager's save-advance cycle.

    Tracer bullet: proves the path works end-to-end.
    """
    import tempfile
    from card_store import CardStore
    from session_manager import SessionManager
    from cantodict_lookup import CantoneseDictionary
    from brave_image_search import BraveImageSearch
    from wiktionary_audio import WiktionaryAudio
    from audio_service import AudioService

    cantodict_path = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    import sqlite3
    conn = sqlite3.connect(cantodict_path.name)
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
    conn.execute(
        "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping) "
        "VALUES (?, 2, 100, 'hello; hi; how are you', 'nei5 hou2')",
        ("你好",),
    )
    conn.commit()
    conn.close()

    card_db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False)

    # Arrange: inject mock clients into each service
    cantodict = CantoneseDictionary(cantodict_path.name)
    card_store = CardStore(card_db_path.name)
    wiktionary = WiktionaryAudio(client=_make_wiktionary_client())
    brave = BraveImageSearch(api_key="test-key", client=_make_brave_client())
    audio_svc = AudioService(client=_make_audio_download_client())

    audio_download = _make_audio_download_client()
    session = SessionManager(
        ["hello"], card_store=card_store,
        http_client=audio_download,
    )

    orch = PipelineOrchestrator(
        cantodict=cantodict,
        brave=brave,
        wiktionary=wiktionary,
        audio_svc=audio_svc,
    )

    # Act: full pipeline through orchestrator + SessionManager
    # 1. Lookup translations
    entries = orch.lookup_translations(session, session.current_word)
    assert len(entries) == 1
    assert entries[0]["chinese"] == "你好"
    session.select_entry(entries[0])
    assert session.current_step == "image"

    # 2. Search images
    results = orch.search_images(session)
    assert len(results) == 1
    assert results[0]["thumbnail_url"] == "https://example.com/thumb1.jpg"
    session.add_image(results[0])
    assert session.current_step == "audio"

    # 3. Wiktionary audio URL + playback
    url = orch.fetch_wiktionary_audio_url(session)
    assert url.startswith("https://upload.wikimedia.org")
    audio_bytes = orch.play_audio(session, url)
    assert audio_bytes == b"OggS\x00\x00\x00\x00mock audio data"

    # 4. Confirm audio → saves card, advances session
    result = orch.confirm_audio(session, "wiktionary", audio_bytes)
    assert result is not None  # saved Flashcard
    assert session.is_complete

    # Assert: flashcard persisted
    cards = card_store.get_all()
    assert len(cards) == 1
    assert cards[0].english_word == "hello"
    assert cards[0].chinese_characters == "你好"
    assert cards[0].audio_data == b"OggS\x00\x00\x00\x00mock audio data"


def test_two_word_pipeline_advances_then_completes():
    """Orchestrator + SessionManager process two words in sequence.

    After confirming the first word, session advances to next word.
    After the second word, session is complete.
    """
    import tempfile
    import sqlite3
    from card_store import CardStore
    from session_manager import SessionManager
    from cantodict_lookup import CantoneseDictionary
    from brave_image_search import BraveImageSearch
    from wiktionary_audio import WiktionaryAudio
    from audio_service import AudioService

    cantodict_path = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    conn = sqlite3.connect(cantodict_path.name)
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
    conn.execute(
        "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping) "
        "VALUES (?, 2, 100, 'hello; hi; how are you', 'nei5 hou2')",
        ("你好",),
    )
    conn.execute(
        "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping) "
        "VALUES (?, 2, 101, 'goodbye; see you later', 'zoii3 gin3')",
        ("再見",),
    )
    conn.commit()
    conn.close()

    card_db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False)

    cantodict = CantoneseDictionary(cantodict_path.name)
    card_store = CardStore(card_db_path.name)
    wiktionary = WiktionaryAudio(client=_make_wiktionary_client())
    brave = BraveImageSearch(api_key="test-key", client=_make_brave_client())
    audio_svc = AudioService(client=_make_audio_download_client())

    audio_download = _make_audio_download_client()
    session = SessionManager(
        ["hello", "goodbye"], card_store=card_store,
        http_client=audio_download,
    )

    orch = PipelineOrchestrator(
        cantodict=cantodict, brave=brave,
        wiktionary=wiktionary, audio_svc=audio_svc,
    )

    # ── Word 1: hello ──
    entries = orch.lookup_translations(session, session.current_word)
    session.select_entry(entries[0])
    results = orch.search_images(session)
    session.add_image(results[0])
    orch.confirm_audio(session, "wiktionary", b"audio1")
    assert session.current_word == "goodbye"
    assert session.current_step == "translate"
    assert not session.is_complete

    # ── Word 2: goodbye ──
    entries = orch.lookup_translations(session, session.current_word)
    session.select_entry(entries[0])
    results = orch.search_images(session)
    session.add_image(results[0])
    orch.confirm_audio(session, "wiktionary", b"audio2")
    assert session.is_complete

    cards = card_store.get_all()
    assert len(cards) == 2
    assert cards[0].english_word == "hello"
    assert cards[1].english_word == "goodbye"
