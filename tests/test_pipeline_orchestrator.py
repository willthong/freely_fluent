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
            views INTEGER DEFAULT 0,
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
    assert session.current_step == "translate"
    session.advance_to_image()
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
            views INTEGER DEFAULT 0,
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


def test_lookup_translations_sorted_by_standalone_then_views_then_length():
    """lookup_translations sorts entries by:
    1. Standalone match (exact word in definition first)
    2. Views (descending — higher views = more popular first)
    3. Chinese character length (ascending — shorter first)
    4. Definition length (ascending — shorter first)

    This improves UX by showing the most relevant + popular + concise translations first.
    """
    import tempfile
    import sqlite3
    from card_store import CardStore
    from session_manager import SessionManager
    from cantodict_lookup import CantoneseDictionary
    from brave_image_search import BraveImageSearch
    from wiktionary_audio import WiktionaryAudio
    from audio_service import AudioService

    # Fixture: entries that test all 4 sort criteria for the word "love"
    #
    # Match positions for standalone "love":
    #   愛      → pos 0  ("love; affection")
    #   情人    → pos 11 ("...eart; love; paramour")
    #   女朋友  → pos 11 ("...iend; love; lass")
    #   心愛    → pos 14 ("...dear; love")
    #   手套    → no standalone match ("glove" only substring)
    #
    # Expected sort order:
    #   1. 愛   — standalone, pos 0, views=2000
    #   2. 情人 — standalone, pos 11, views=3000 (tie-break: higher views)
    #   3. 女朋友 — standalone, pos 11, views=1000 (same pos, lower views)
    #   4. 心愛 — standalone, pos 14, views=1000
    #   5. 手套 — substring-only ("glove"), 5000 views
    entries = [
        ("心愛", "sam1 oi3", "beloved; dear; love", 1000),
        ("愛", "oi3", "love; affection", 2000),
        ("女朋友", "neoi5 pang4 jau5", "girlfriend; love; lass", 1000),
        ("情人", "cing4 jan4", "sweetheart; love; paramour", 3000),
        ("手套", "sau2 tou3", "glove (hand wear)", 5000),
    ]
    cantodict_path = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    conn = sqlite3.connect(cantodict_path.name)
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
    for i, (chinese, jyutping, definition, views) in enumerate(entries, start=100):
        conn.execute(
            "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping, views) "
            "VALUES (?, 2, ?, ?, ?, ?)",
            (chinese, i, definition, jyutping, views),
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
    session = SessionManager(["love"], card_store=card_store, http_client=audio_download)

    orch = PipelineOrchestrator(
        cantodict=cantodict, brave=brave,
        wiktionary=wiktionary, audio_svc=audio_svc,
    )

    # Act
    results = orch.lookup_translations(session, session.current_word)

    # Assert: sorted by the 4 criteria
    assert len(results) == 5

    # --- Standalone matches (0-3) come before substring-only (4) ---
    # Entry 4: "手套" ("glove") is a substring-only match (no standalone "love")
    assert results[4]["chinese"] == "手套"

    # --- Entry 0: standalone with earliest match position ---
    # "愛" has "love" at position 0 (earliest of all)
    assert results[0]["chinese"] == "愛"

    # --- Entries 1-2: same match position (11), higher views first ---
    # "情人" has 3000 views > "女朋友" has 1000 views
    assert results[1]["chinese"] == "情人"
    assert results[2]["chinese"] == "女朋友"

    # --- Entry 3: later match position (14) ---
    # "心愛" has "love" at position 14
    assert results[3]["chinese"] == "心愛"

    # No definition-length check needed — it's been replaced by match position 
