"""Tests for audio persistence fix.

play_audio downloads audio bytes but must persist them to session._selected_audio
so confirm_audio can reuse them instead of re-fetching Wiktionary HTML + re-downloading.

Without this fix, any transient network failure during confirm (rate limit, timeout,
HTML parse returning None) causes audio confirmation to fail.
"""

import httpx

from pipeline_orchestrator import PipelineOrchestrator
from session_manager import SessionManager
from wiktionary_audio import WiktionaryAudio
from audio_service import AudioService


def _make_wiktionary_audio_client():
    """WiktionaryAudio client serving the 你 fixture."""
    path = "tests/fixtures/wiktionary_你.html"
    with open(path, encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=body)
    )
    return httpx.Client(transport=transport)


def _make_card_download_client():
    """httpx client for image/card downloads (used by SessionManager)."""
    image_bytes = b"\x89PNGmock image data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=image_bytes)
    )
    return httpx.Client(transport=transport)


def test_play_audio_persists_bytes_to_session():
    """After play_audio downloads bytes, session.selected_audio must hold
    those bytes so confirm_audio can reuse them later.
    """
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    audio_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )

    wiktionary = WiktionaryAudio(client=_make_wiktionary_audio_client())
    audio_svc = AudioService(client=httpx.Client(transport=audio_transport))

    session = SessionManager(
        ["hello"],
        http_client=_make_card_download_client(),
    )
    session.select_entry({"chinese": "你好", "jyutping": "nei5 hou2"})
    session.add_image({"url": "https://example.com/img.jpg"})

    orch = PipelineOrchestrator(
        cantodict=None, brave=None,
        wiktionary=wiktionary, audio_svc=audio_svc,
    )

    # Play audio (downloads from URL)
    url = orch.fetch_wiktionary_audio_url(session)
    result = orch.play_audio(session, url)

    assert result == audio_bytes
    # The fix: play_audio must persist to session
    assert session.selected_audio == audio_bytes


def test_confirm_reuses_played_audio_without_redownload():
    """When confirm_audio is called after play_audio, it must reuse the
    persisted bytes — NOT re-fetch Wiktionary HTML or re-download audio.

    Uses a one-shot transport: first download succeeds, second fails.
    Without persistence, confirm_audio triggers a second download → failure.
    With persistence, confirm_audio reuses bytes from play_audio → success.
    """
    import tempfile
    import sqlite3
    from card_store import CardStore
    from cantodict_lookup import CantoneseDictionary
    from brave_image_search import BraveImageSearch

    # Tracking transport: succeeds once, fails on subsequent calls
    download_count = [0]
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"

    def tracking_transport(request):
        download_count[0] += 1
        if download_count[0] == 1:
            return httpx.Response(200, content=audio_bytes)
        # Second download attempt — simulate transient failure
        return httpx.Response(503)

    audio_svc = AudioService(
        client=httpx.Client(transport=httpx.MockTransport(tracking_transport))
    )
    wiktionary = WiktionaryAudio(client=_make_wiktionary_audio_client())

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
    conn.commit()
    conn.close()

    card_db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    card_store = CardStore(card_db_path.name)

    session = SessionManager(
        ["hello"],
        card_store=card_store,
        http_client=_make_card_download_client(),
    )

    cantodict = CantoneseDictionary(cantodict_path.name)
    brave_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": [
                {
                    "type": "image_result",
                    "url": "https://example.com/page1",
                    "thumbnail": {"src": "https://example.com/thumb1.jpg", "width": 480, "height": 360},
                    "properties": {"url": "https://example.com/original1.jpg"},
                }
            ]})
        )
    )
    brave = BraveImageSearch(api_key="test-key", client=brave_client)

    orch = PipelineOrchestrator(
        cantodict=cantodict, brave=brave,
        wiktionary=wiktionary, audio_svc=audio_svc,
    )

    # Full pipeline: lookup → select → image → play audio
    entries = orch.lookup_translations(session, session.current_word)
    session.select_entry(entries[0])

    results = orch.search_images(session)
    session.add_image(results[0])

    # Play audio — downloads bytes (first and only download)
    url = orch.fetch_wiktionary_audio_url(session)
    orch.play_audio(session, url)

    # Confirm audio WITHOUT passing audio_bytes — must reuse persisted bytes
    # Without fix: confirm_audio fetches URL → calls download_audio again → 503 → None
    # With fix: confirm_audio reuses session.selected_audio → returns Flashcard
    result = orch.confirm_audio(session, "wiktionary", None)

    assert result is not None, (
        f"confirm_audio returned None — audio was not reused from play_audio. "
        f"download was called {download_count[0]} times (expected 1)."
    )
    assert session.is_complete
    assert download_count[0] == 1, (
        f"download_audio was called {download_count[0]} times. "
        "confirm_audio should NOT re-download audio that was already played."
    )
