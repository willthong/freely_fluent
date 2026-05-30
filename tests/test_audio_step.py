"""Tests for Story 7: Wiktionary Cantonese pronunciation UI (audio step).

Follows the existing test_app.py patterns: TestClient + create_app +
mock clients (wiktionary_client, audio_download_client).
"""

import httpx
from fastapi.testclient import TestClient

from app import create_app
from card_generator import CardGenerator
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary
from brave_image_search import BraveImageSearch

from tests.test_app import (
    _make_cantodict_fixture,
    _make_card_store_fixture,
    _make_brave_client,
    _make_audio_download_client,
)


def _make_wiktionary_client_char(char):
    """httpx client serving the Wiktionary HTML fixture for a given character."""
    path = f"tests/fixtures/wiktionary_{char}.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def test_audio_step_shows_recording_controls():
    """Audio step page renders recording controls (Record/Stop buttons)
    alongside the Wiktionary audio player.

    Story 8: User can record own pronunciation even when Wiktionary audio exists.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text

    # Wiktionary player still present
    assert "Cantonese Pronunciation" in body
    assert 'type="audio/ogg"' in body
    assert "Confirm" in body

    # Recording section visible alongside Wiktionary player
    assert "Record your own pronunciation" in body
    assert 'id="record-btn"' in body
    assert 'id="stop-btn"' in body


def test_audio_step_page_renders_with_player():
    """Audio step page shows audio player, Jyutping, and confirm button
    when Wiktionary has Cantonese audio.

    Story 7 acceptance criteria:
    - Page loads with character and Jyutping displayed
    - Audio player with playback controls
    - Confirm button to select Wiktionary audio
    - Skip button as fallback
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    # "你" has Cantonese audio in Wiktionary fixture
    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Start session → translate → select → image → audio step
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. GET /audio/{id} → 200 HTML with player, Jyutping, Confirm, Skip
    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]

    body = r.text
    assert "Cantonese Pronunciation" in body
    # Jyutping is now stored in the RAW_JYUTPING JS variable (editable tone editor)
    assert "RAW_JYUTPING" in body
    assert "nei5 hou2" in body  # Raw jyutping in JS variable
    assert "你好" in body  # Characters from selected entry
    assert 'type="audio/ogg"' in body  # Audio player source
    assert "Confirm" in body  # Confirm button
    assert "Skip" in body  # Skip button


def test_audio_step_page_shows_no_audio_available():
    """Audio step page shows 'no audio available' message when Wiktionary
    has no Cantonese audio for the character.

    Story 7 edge case: graceful fallback when no audio exists.
    """
    cantodict_path = _make_cantodict_fixture(
        entries=[("山", "saan1", "mountain")]
    )
    card_db_path = _make_card_store_fixture()

    # "山" has NO Cantonese audio — serve fixture with genuinely no Yue/LL-Q9186 audio
    path = "tests/fixtures/wiktionary_山_audio.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    wiktionary_client = httpx.Client(transport=transport)
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
    client = TestClient(app, raise_server_exceptions=False)

    # Start session → translate → select → image → audio step
    r = client.post("/sessions", json={"words": ["mountain"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "山"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # GET /audio/{id} → 200 HTML with "no audio available" message
    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text
    assert "Cantonese Pronunciation" in body
    # Jyutping is now stored in the RAW_JYUTPING JS variable (editable tone editor)
    assert "RAW_JYUTPING" in body
    assert "saan1" in body  # Raw jyutping in JS variable
    assert "山" in body
    assert "no audio" in body.lower() or "not available" in body.lower()
    assert "Skip" in body

    # Wiktionary Confirm button should NOT appear (no wiktionary audio to confirm)
    # The confirm button uses dynamic JS hx-vals, so check for the id instead
    assert 'id="confirm-wiktionary-btn"' not in body

    # Recording section should appear as fallback option
    assert "Record your own pronunciation" in body
    assert 'id="record-btn"' in body
    assert 'id="stop-btn"' in body


def test_audio_step_confirm_wiktionary_audio():
    """POST /audio/{id} with 'wiktionary' source confirms the audio,
    saves the flashcard, and advances session.

    Story 7: User confirms Wiktionary audio via the audio step page.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # Start session → translate → select → image → audio step
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # Confirm wiktionary audio via audio step
    r = client.post(f"/audio/{session_id}", json={"source": "wiktionary"})
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # Verify flashcard was saved
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    assert flashcards[0].english_word == "hello"
    assert flashcards[0].chinese_characters == "你好"
    assert flashcards[0].jyutping == "nei5 hou2"
    assert flashcards[0].audio_data == b"OggS\x00\x00\x00\x00mock audio data"


def test_audio_step_skip():
    """POST /sessions/{id}/skip from audio step discards everything
    and advances to next word.

    Story 7 + Story 3: Skip from audio step.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello", "goodbye"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # Skip from audio step
    r = client.post(f"/sessions/{session_id}/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["current_word"] == "goodbye"
    assert data["current_step"] == "translate"
    assert data["completed"] is False

    # No flashcard saved
    assert card_store.get_all() == []


def test_audio_step_preview_and_confirm_appear():
    """After submitting a recording, preview playback and confirm button appear.

    Story 9: Preview recorded audio + confirm.
    The recording POST with HTMX header returns an HTML fragment that
    hides the recording section and shows the preview section.
    """
    import base64

    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # Submit a mock recording via POST (browser uses fetch(), not HTMX)
    mock_recording = base64.b64encode(b"mock webm audio data").decode()
    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": mock_recording},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "saved"

    # Verify recording was saved to session
    assert len(card_store.get_all()) == 0  # Not confirmed yet, no card saved

    # Verify the audio step page template has preview section with confirm
    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text
    assert "Preview your recording" in body
    assert "Confirm" in body
    assert "Re-record" in body


def test_audio_step_rerecord_flow():
    """Re-record flow: record → preview → re-record → new recording → new preview
    → confirm → card saved with second recording (not first).

    Story 9: User can re-record if the first attempt is bad.
    The re-record button hides preview and shows recording controls again.
    After submitting a new recording, preview + confirm re-appear.
    Confirm uses the latest recording bytes.
    """
    import base64

    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 1. GET /audio/{id} → page has recording controls AND re-record button
    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text
    assert "Record your own pronunciation" in body
    assert 'id="record-btn"' in body
    assert 'id="stop-btn"' in body
    assert 'id="rerecord-btn"' in body  # Re-record button present in template

    # 2. Submit first recording (browser uses fetch(), not HTMX)
    first_recording = base64.b64encode(b"first attempt webm data").decode()
    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": first_recording},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "saved"

    # 3. Submit second recording (different bytes) — simulates re-record
    second_recording = base64.b64encode(b"second attempt webm data!!").decode()
    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": second_recording},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "saved"

    # 4. Confirm recording → card saved with SECOND recording bytes
    r = client.post(f"/audio/{session_id}", json={"source": "recording"})
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # Verify flashcard saved with second recording, not first
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"
    assert card.jyutping == "nei5 hou2"
    # Card audio is the SECOND recording bytes
    assert card.audio_data == b"second attempt webm data!!"
    # Card audio is NOT the first recording bytes
    assert card.audio_data != b"first attempt webm data"


def test_audio_step_record_confirm_saves_card():
    """Full integration: render page → submit recording → confirm recording
    → verify flashcard saved with recording bytes, session completes.

    Story 8 + 9: End-to-end integration test exercising the HTMX recording
    workflow through the audio step page, verifying card persistence.
    Single-attempt flow (no re-record).
    """
    import base64

    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio step
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. GET /audio/{id} → page renders with recording controls
    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text
    assert "Record your own pronunciation" in body
    assert 'id="record-btn"' in body
    assert 'id="stop-btn"' in body

    # 3. Submit recording via POST (browser uses fetch(), not HTMX)
    mock_recording = base64.b64encode(b"mock webm audio data").decode()
    r = client.post(
        f"/sessions/{session_id}/recording",
        json={"recording": mock_recording},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "saved"

    # No card saved yet (not confirmed)
    assert len(card_store.get_all()) == 0

    # 4. Confirm recording → card saved, session completes
    r = client.post(f"/audio/{session_id}", json={"source": "recording"})
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 5. Verify flashcard persisted with recording bytes
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"
    assert card.jyutping == "nei5 hou2"
    assert card.audio_data == b"mock webm audio data"


def test_audio_step_confirm_with_modified_tone():
    """Confirming audio with a modified jyutping tone saves the card with
    the edited tone number instead of the original.

    Feature: User can edit the tone number before moving on to the next word.
    """
    import base64

    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Confirm with a modified jyutping (change tone 2→3: hou2→hou3)
    r = client.post(
        f"/audio/{session_id}",
        json={"source": "wiktionary", "jyutping": "nei5 hou3"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 3. Verify flashcard saved with MODIFIED jyutping, not original
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.jyutping == "nei5 hou3"  # modified tone
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"


def test_audio_step_confirm_without_tone_override_uses_original():
    """Confirming audio without a jyutping override saves the card with the
    original jyutping from the selected entry.

    Ensures backward compatibility: existing confirmations still work.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Confirm WITHOUT jyutping override (backward compat)
    r = client.post(f"/audio/{session_id}", json={"source": "wiktionary"})
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 3. Verify flashcard saved with ORIGINAL jyutping
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.jyutping == "nei5 hou2"  # original, unchanged


def test_audio_step_confirm_with_syllable_removed():
    """Confirming audio with a syllable removed from the jyutping saves
    the card with the remaining syllables only.

    Feature: User can delete individual Jyutping syllables they disagree with.
    """
    import base64

    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Confirm with one syllable removed (just "nei5" instead of "nei5 hou2")
    r = client.post(
        f"/audio/{session_id}",
        json={"source": "wiktionary", "jyutping": "nei5"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 3. Verify flashcard saved with only the remaining syllable
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.jyutping == "nei5"  # one syllable deleted
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"


def test_audio_step_confirm_with_empty_jyutping():
    """Confirming audio with an empty jyutping after deleting all syllables
    saves the card with an empty jyutping.

    Edge case: user deletes all syllables.
    """
    import base64

    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Confirm with empty jyutping (all syllables deleted)
    r = client.post(
        f"/audio/{session_id}",
        json={"source": "wiktionary", "jyutping": ""},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 3. Verify flashcard saved with empty jyutping
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.jyutping == ""  # all syllables deleted
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"


def test_audio_step_page_has_syllable_delete_buttons():
    """The audio step page renders a delete button for each Jyutping syllable.

    Feature: User can delete individual Jyutping syllables.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text

    # The delete button for syllables should appear in the page
    assert "syllable-remove" in body or "delete-syllable" in body
    # The button should have a click handler or onclick attribute
    assert "onclick" in body.lower() or "removeSyllable" in body
    # RAW_JYUTPING confirms JS-based rendering is in place
    assert "RAW_JYUTPING" in body


def test_audio_step_page_has_editable_jyutping_text():
    """The audio step page renders Jyutping text spans as contenteditable,
    allowing the user to edit the romanization text (not just tone numbers).

    Feature: User can edit the actual Jyutping romanization (e.g., change
    "nei" to "neoi") at the same point where they edit tone numbers.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text

    # Each Jyutping syllable text span should be contenteditable
    assert 'class="jyutping-text" contenteditable="true"' in body


def test_audio_step_page_has_add_syllable_button():
    """The audio step page has an "Add syllable" button that lets the
    user insert a new Jyutping syllable into the editor.

    Feature: User can add a new syllable (e.g., adding a missing
    syllable that CantoDict didn't include).
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text

    # An "Add syllable" button should be present in the page
    assert 'add-syllable' in body.lower() or 'Add syllable' in body
    # It should have an onclick handler
    assert 'addSyllable' in body


def test_audio_step_page_has_undo_button():
    """The audio step page has an "Undo" button that can restore
    a previously deleted syllable.

    Feature: User can undo a syllable deletion.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    body = r.text

    # An "Undo" button should be present in the page
    assert 'undo' in body.lower()
    # It should have an onclick handler
    assert 'undoLastSyllable' in body


def test_audio_step_confirm_with_modified_romanization():
    """Confirming audio with a modified jyutping romanization (changing
    the syllable text, not just the tone) saves the card with the edited
    romanization.

    Feature: User can edit the actual Jyutping romanization text
    (e.g., change "nei" to "neoi") before confirming.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Confirm with a modified romanization (nei5 hou2 → neoi5 ho3)
    r = client.post(
        f"/audio/{session_id}",
        json={"source": "wiktionary", "jyutping": "neoi5 ho3"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 3. Verify flashcard saved with MODIFIED romanization
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    assert card.jyutping == "neoi5 ho3"  # modified romanization + tone
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"


def test_audio_step_confirm_strips_non_alpha_from_jyutping():
    """Confirming audio with non-alphabetic characters in the jyutping
    syllable text strips them before saving (only a-zA-Z preserved in
    the romanization part, tone numbers stay intact).

    Validation: User can only type alphabetical characters in the
    romanization text; non-alpha chars are stripped.
    """
    cantodict_path = _make_cantodict_fixture()
    card_db_path = _make_card_store_fixture()

    wiktionary_client = _make_wiktionary_client_char("你")
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
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Pipeline: start session → translate → entry → image → audio
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # 2. Confirm with non-alpha chars in syllable text
    r = client.post(
        f"/audio/{session_id}",
        json={"source": "wiktionary", "jyutping": "nei5!! hou2???"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["completed"] is True

    # 3. Verify flashcard saved with STRIPPED jyutping
    flashcards = card_store.get_all()
    assert len(flashcards) == 1
    card = flashcards[0]
    # Non-alpha chars removed from syllable text, tone numbers preserved
    assert card.jyutping == "nei5 hou2"
    assert card.english_word == "hello"
    assert card.chinese_characters == "你好"
