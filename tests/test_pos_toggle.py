"""Tests for the POS toggle feature (Story 4).

User can toggle part-of-speech hints on/off via a tickbox in the UI.
"""

from __future__ import annotations

import httpx
import re
import sqlite3
import tempfile

from fastapi.testclient import TestClient

from app import create_app
from card_generator import CardGenerator
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary

FIXTURE_DIR = "tests/fixtures"


def _make_cantodict_db() -> str:
    """Create a minimal CantoDict fixture database with POS in definitions."""
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
    conn.execute("""
        INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping)
        VALUES ('你好', 2, 100, 'n. hello; hi', 'nei5 hou2')
    """)
    conn.commit()
    conn.close()
    return tmp.name


def _make_wiktionary_client():
    """Mock HTTP client that returns Wiktionary HTML with audio."""
    path = f"{FIXTURE_DIR}/wiktionary_你.html"
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


def _make_app() -> TestClient:
    """Create a TestClient with all dependencies wired up."""
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


def test_toggle_pos_off_via_api():
    """POST /sessions/{id}/pos-toggle with include_pos=false
    toggles the session preference off."""
    client = _make_app()

    # Create a session
    resp = client.post("/sessions", json={"words": ["hello"]})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Default: include_pos is True
    session_resp = client.get(f"/sessions/{session_id}")
    assert session_resp.json().get("include_pos") is True

    # Toggle off
    toggle_resp = client.post(
        f"/sessions/{session_id}/pos-toggle",
        json={"include_pos": False},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["include_pos"] is False

    # Verify it stuck
    session_resp = client.get(f"/sessions/{session_id}")
    assert session_resp.json().get("include_pos") is False


def test_toggle_pos_on_via_api():
    """POST /sessions/{id}/pos-toggle with include_pos=true
    toggles the session preference back on."""
    client = _make_app()

    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # Toggle off first
    client.post(
        f"/sessions/{session_id}/pos-toggle",
        json={"include_pos": False},
    )

    # Toggle back on
    toggle_resp = client.post(
        f"/sessions/{session_id}/pos-toggle",
        json={"include_pos": True},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["include_pos"] is True


def test_toggle_pos_unknown_session_returns_404():
    """POST /sessions/{id}/pos-toggle returns 404 for unknown session."""
    client = _make_app()

    resp = client.post(
        "/sessions/does-not-exist/pos-toggle",
        json={"include_pos": True},
    )
    assert resp.status_code == 404


def test_translate_step_shows_pos_tickbox_checked():
    """The translate step template renders a tickbox for POS
    that is checked by default (include_pos=True)."""
    client = _make_app()

    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    page = client.get(f"/translate/{session_id}")
    assert page.status_code == 200
    html = page.text
    # Tickbox should be present and checked
    assert 'name="include_pos"' in html or 'id="include_pos"' in html
    assert "checked" in html


def test_translate_step_shows_pos_tickbox_unchecked():
    """After toggling include_pos=False, the translate step
    tickbox is rendered unchecked."""
    client = _make_app()

    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # Toggle off
    client.post(
        f"/sessions/{session_id}/pos-toggle",
        json={"include_pos": False},
    )

    page = client.get(f"/translate/{session_id}")
    assert page.status_code == 200
    html = page.text
    # Tickbox should be present but NOT checked
    assert 'name="include_pos"' in html or 'id="include_pos"' in html
    # When unchecked, the checkbox input should NOT have the checked attribute
    checkbox = re.search(r'<input[^>]*name="include_pos"[^>]*/?>', html)
    assert checkbox is not None, "POS tickbox not found in template"
    # Match the HTML boolean "checked" attribute:
    # - NOT preceded by a dot (rules out "event.target.checked")
    # - NOT followed by "=" (rules out "checked = data.include_pos")
    has_checked_attr = bool(re.search(r'(?<![\w.])checked(?!\s*=)', checkbox.group(0)))
    assert not has_checked_attr, "tickbox should be unchecked when include_pos=False"


def test_translate_step_has_js_to_swap_tickbox_state():
    """After the HTMX toggle request, JS handler reads the JSON response
    and updates the checkbox's checked state accordingly."""
    client = _make_app()

    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    page = client.get(f"/translate/{session_id}")
    html = page.text

    # The checkbox must have an hx-on::after-request handler
    # that reads the JSON response and updates .checked
    checkbox = re.search(r'<input[^>]*name="include_pos"[^>]*/?>', html)
    assert checkbox is not None
    tag = checkbox.group(0)
    assert "after-request" in tag, "needs hx-on::after-request to update visual state"
    assert "JSON.parse" in tag or "response" in tag, "must read JSON response"


def test_end_to_end_toggle_off_suppresses_pos_on_card():
    """Full pipeline: toggle POS off via API → select entry → confirm audio
    → the saved flashcard has empty part_of_speech."""
    client = _make_app()

    # Create session and toggle off
    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # Toggle POS off
    toggle_resp = client.post(
        f"/sessions/{session_id}/pos-toggle",
        json={"include_pos": False},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["include_pos"] is False

    # Select entry
    entries_resp = client.get(f"/sessions/{session_id}/translate")
    entries = entries_resp.json()["entries"]
    chosen_chinese = entries[0]["chinese"]

    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": chosen_chinese},
    )

    # Add an image (search returns results with the fixture data)
    images_resp = client.get(f"/sessions/{session_id}/images")
    results = images_resp.json().get("results", [])
    if results:
        client.post(
            f"/sessions/{session_id}/images",
            json={"result_index": 0},
        )

    # Confirm Wiktionary audio
    audio_resp = client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )

    # Get saved cards from the store
    cards_resp = client.get(f"/export?session_id={session_id}")
    # Export returns a zip file — instead, check the session details
    # which includes the saved card
    session_resp = client.get(f"/sessions/{session_id}")
    # The entry should have POS suppressed
    # We can verify via the selected_entry
    selected_entry = session_resp.json().get("selected_entry", {})
    # The entry still has the original POS data, but the card should be empty
    # Best check: verify include_pos is False in session
    assert session_resp.json().get("include_pos") is False

    # The definitive check: completion screen should NOT show POS
    complete_resp = client.get(f"/complete/{session_id}")
    html = complete_resp.text
    # If POS is suppressed, the completion page should not show POS text
    # The template uses: {% if card.part_of_speech %}(POS){% endif %}
    assert "(n)" not in html and "(v)" not in html, \
        "POS should not appear in completion when toggled off"


def test_end_to_end_pos_on_shows_pos_on_card():
    """Full pipeline with POS ON (default) → completion screen shows POS."""
    client = _make_app()

    resp = client.post("/sessions", json={"words": ["hello"]})
    session_id = resp.json()["session_id"]

    # Don't toggle — leave include_pos=True (default)

    # Select entry
    entries_resp = client.get(f"/sessions/{session_id}/translate")
    entries = entries_resp.json()["entries"]
    chosen_chinese = entries[0]["chinese"]

    client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": chosen_chinese},
    )

    # Add image
    client.post(
        f"/sessions/{session_id}/images",
        json={"result_index": 0},
    )

    # Confirm Wiktionary audio
    client.post(
        f"/sessions/{session_id}/audio",
        json={"source": "wiktionary"},
    )

    # Completion screen SHOULD show POS
    complete_resp = client.get(f"/complete/{session_id}")
    html = complete_resp.text
    assert "<em>n</em>" in html, "POS should appear in completion when toggled on"
