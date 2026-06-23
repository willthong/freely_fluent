"""Tests for the manual POS override dropdown (PRD2).

Replaces the global POS toggle with a per-entry dropdown on the
translate step.
"""

from __future__ import annotations

import tempfile
from unittest.mock import Mock

import httpx
from fastapi.testclient import TestClient

from app import create_app
from card_generator import CardGenerator
from card_store import CardStore, Flashcard
from cantodict_lookup import CantoneseDictionary


def _make_cantodict_db(definition: str = "n. hello; hi") -> str:
    """Create a minimal CantoDict fixture database."""
    import sqlite3
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
    conn.execute(
        "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping) "
        "VALUES (?, 2, 100, ?, 'nei5 hou2')",
        ("\u4f60\u597d", definition),
    )
    conn.commit()
    conn.close()
    return tmp.name


def _make_cantodict_db_no_pos() -> str:
    """Fixture where CantoDict definition has no POS abbreviation."""
    return _make_cantodict_db(definition="hello; hi (greeting)")


def _make_wiktionary_client():
    """Mock HTTP client that returns Wiktionary HTML with audio."""
    path = "tests/fixtures/wiktionary_\u4f60.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def _make_brave_client():
    """Mock HTTP client that returns one Brave image search result."""
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
    """Mock HTTP client that returns mock audio bytes."""
    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    return httpx.Client(transport=transport)


def _make_app(cantodict_path: str | None = None) -> TestClient:
    """Create a TestClient with all dependencies wired up."""
    if cantodict_path is None:
        cantodict_path = _make_cantodict_db()
    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(tempfile.mktemp(suffix=".db"))
    card_generator = CardGenerator()

    app = create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        wiktionary_client=_make_wiktionary_client(),
        brave_client=_make_brave_client(),
        audio_download_client=_make_audio_download_client(),
        api_key="test-key",
    )
    return TestClient(app)


# ── Translate step HTML page ──

def test_translate_step_has_pos_placeholder():
    """The translate step renders a POS dropdown area placeholder,
    not the old tickbox."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    page = client.get(f"/translate/{session_id}")
    assert page.status_code == 200
    html = page.text
    # Placeholder div is present
    assert 'id="pos-dropdown-area"' in html
    # Old include_pos checkbox is gone
    assert 'name="include_pos"' not in html
    assert "Show part-of-speech hints" not in html


# ── select-entry HTMX endpoint ──

def test_select_entry_returns_pos_dropdown_with_suggestion():
    """POST /sessions/{id}/select-entry returns POS row HTML with suggestion."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # Get entries
    entries_resp = client.get(f"/sessions/{session_id}/translate")
    entries = entries_resp.json()["entries"]
    assert len(entries) > 0
    chinese = entries[0]["chinese"]

    # Select entry via HTMX endpoint
    r = client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})
    assert r.status_code == 200
    html = r.text
    # Dropdown should be present and enabled (no disabled attribute)
    assert 'id="pos-dropdown"' in html
    assert "disabled" not in html
    # Suggestion label renders because CantoDict detected "n"
    assert "Suggestion: n" in html


def test_select_entry_no_suggestion_when_no_cantodict_pos():
    """When CantoDict has no POS, the suggestion label is absent."""
    cantodict_path = _make_cantodict_db_no_pos()
    client = _make_app(cantodict_path)
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    entries = entries_resp.json()["entries"]
    chinese = entries[0]["chinese"]

    r = client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})
    assert r.status_code == 200
    html = r.text
    assert "Suggestion:" not in html


def test_select_entry_unknown_session_redirects():
    """Select-entry on unknown session redirects to index page."""
    client = _make_app()
    r = client.post("/sessions/bogus/select-entry", data={"chinese": "你"})
    assert r.status_code == 200
    # Should have been redirected to index — check for textarea
    assert 'name="words"' in r.text or "Paste your words" in r.text


def test_select_entry_unknown_chinese_returns_404():
    """Select-entry with unknown chinese value returns 404."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    r = client.post(f"/sessions/{session_id}/select-entry", data={"chinese": "BOGUS"})
    assert r.status_code == 404


# ── POS set endpoint ──

def test_set_pos_returns_confirmation():
    """POST /sessions/{id}/pos with a value returns a ✓ confirmation."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # First select an entry
    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]
    client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})

    # Set POS
    r = client.post(f"/sessions/{session_id}/pos", data={"pos": "v"})
    assert r.status_code == 200
    assert "&#10003;" in r.text
    assert "pos-confirmed" in r.text


def test_set_pos_empty_clears_confirmation():
    """POST /sessions/{id}/pos with empty value returns cleared indicator."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]
    client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})

    # Set POS to blank
    r = client.post(f"/sessions/{session_id}/pos", data={"pos": ""})
    assert r.status_code == 200
    assert "pos-cleared" in r.text


def test_set_pos_strips_whitespace():
    """POS values are stripped before storage."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]
    client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})

    # Set POS with whitespace
    client.post(f"/sessions/{session_id}/pos", data={"pos": "  n  "})

    # Verify it was stored stripped
    session_detail = client.get(f"/sessions/{session_id}").json()
    assert session_detail["selected_entry"]["part_of_speech"] == "n"


def test_set_pos_custom_value():
    """Free-form POS (e.g. 'measure word') is stored and confirmed."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]
    client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})

    r = client.post(f"/sessions/{session_id}/pos", data={"pos": "measure word"})
    assert r.status_code == 200
    assert "&#10003;" in r.text

    # Verify stored
    session_detail = client.get(f"/sessions/{session_id}").json()
    assert session_detail["selected_entry"]["part_of_speech"] == "measure word"


def test_set_pos_expired_session_redirects_to_index():
    """POS endpoint on unknown session redirects to index page."""
    client = _make_app()
    r = client.post("/sessions/bogus/pos", data={"pos": "v"})
    assert r.status_code == 200
    # Should have been redirected to index
    assert 'name="words"' in r.text or "Paste your words" in r.text


# ── Form submit (translate → image) ──

def test_form_submit_advances_to_image():
    """POST /translate/{id}/select advances step and redirects to image."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # Select entry first
    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]
    client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})

    # Submit form (TestClient follows redirect by default)
    r = client.post(f"/translate/{session_id}/select", data={"chinese": chinese})
    # After redirect, we should be on the image step page
    assert r.status_code == 200
    # Check we're on the image page
    assert "Image Search" in r.text or 'id="image-grid"' in r.text or "Select images" in r.text

    # Verify step advanced
    session_detail = client.get(f"/sessions/{session_id}").json()
    assert session_detail["current_step"] == "image"


def test_form_submit_no_entry_returns_400():
    """Form submit without selecting an entry returns 400."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    r = client.post(f"/translate/{session_id}/select", data={"chinese": "你好"})
    assert r.status_code == 400


# ── End-to-end: POS flows to flashcard ──

def _complete_pipeline_with_pos(client, session_id, chinese, pos_value=None):
    """Helper: complete the pipeline for a word with optional POS."""
    if pos_value is not None:
        client.post(f"/sessions/{session_id}/select-entry", data={"chinese": chinese})
        client.post(f"/sessions/{session_id}/pos", data={"pos": pos_value})

    # Advance to image
    client.post(f"/translate/{session_id}/select", data={"chinese": chinese})

    # Add image
    img_resp = client.get(f"/sessions/{session_id}/images")
    results = img_resp.json().get("results", [])
    if results:
        client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    # Confirm audio
    client.post(f"/sessions/{session_id}/audio", json={"source": "wiktionary"})


def test_end_to_end_pos_appears_on_card():
    """Manual POS selection flows through to the saved flashcard."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]

    _complete_pipeline_with_pos(client, session_id, chinese, pos_value="v")

    # Check the completion page shows POS
    complete = client.get(f"/complete/{session_id}")
    html = complete.text
    assert "<em>v</em>" in html


def test_end_to_end_no_pos_shows_blank_on_card():
    """When no POS is selected, the flashcard has empty POS."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]

    _complete_pipeline_with_pos(client, session_id, chinese, pos_value=None)

    # Check completion page — should NOT show POS
    complete = client.get(f"/complete/{session_id}")
    html = complete.text
    # No <em> tag for POS (the template only renders when card.part_of_speech is truthy)
    assert "<em>n</em>" not in html


def test_end_to_end_custom_pos_on_card():
    """Custom POS like 'measure word' appears on the completion screen."""
    client = _make_app()
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    entries_resp = client.get(f"/sessions/{session_id}/translate")
    chinese = entries_resp.json()["entries"][0]["chinese"]

    _complete_pipeline_with_pos(client, session_id, chinese, pos_value="measure word")

    complete = client.get(f"/complete/{session_id}")
    html = complete.text
    assert "<em>measure word</em>" in html
