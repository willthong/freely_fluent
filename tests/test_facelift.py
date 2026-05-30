"""Integration tests for the facelift (Story F1–F7).

Tests are organised by story. Story F1 covers the global CSS, layout,
and static file serving.
"""

import httpx
import sqlite3
import tempfile

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
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return tmp.name


def _make_wiktionary_client() -> object:
    import httpx

    path = f"{FIXTURE_DIR}/wiktionary_你.html"
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().encode("utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return httpx.Client(transport=transport)


def _make_brave_client() -> object:
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
    import httpx

    audio_bytes = b"OggS\x00\x00\x00\x00mock audio data"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=audio_bytes)
    )
    return httpx.Client(transport=transport)


def _make_app():
    """Create a fully configured app with all dependencies injected."""
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
    return TestClient(app)


# ── Story F1: Global CSS & Layout ──


def test_static_css_file_is_served():
    """The static CSS file must be served at /static/style.css.

    Story F1: The application must mount /static and serve the CSS file
    so browsers can load the Solarized Dark theme.
    """
    client = _make_app()
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/css" or "text/css" in r.headers.get("content-type", "")


def test_base_html_links_stylesheet():
    """base.html must include a <link> to the stylesheet in <head>.

    Story F1: Every page gets the Solarized Dark theme via the stylesheet.
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    # The stylesheet link should appear in the HTML head
    assert '/static/style.css' in r.text
    assert '<link rel="stylesheet"' in r.text or 'rel="stylesheet"' in r.text


def test_base_html_has_container_div():
    """base.html must wrap {% block content %} in a <div class="container">.

    Story F1: A centred container provides the layout constraint (max-width 720px).
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="container"' in r.text
    # The container should be inside <body>, not inside the head
    body_start = r.text.index('<body')
    after_body = r.text[body_start:]
    assert 'class="container"' in after_body


# ── Story F2: Step Progress Bar ──


def test_translate_page_shows_step_bar():
    """The translate page must include the step progress bar with
    'Translate' as the active step and the rest as upcoming.

    Story F2: Visual progress bar shows which pipeline step the user is on.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    # Step bar must be present
    assert 'class="step-bar"' in r.text
    assert 'Translate' in r.text
    assert 'Image' in r.text
    assert 'Audio' in r.text
    # Translate should be the active step
    assert 'class="step active"' in r.text or 'step active' in r.text


def test_image_page_shows_step_bar():
    """The image page must include the step progress bar with
    'Translate' as done, 'Image' as active, and 'Audio' as upcoming.

    Story F2: Visual progress bar shows which pipeline step the user is on.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Trigger translation lookup, then select an entry to advance to image step
    client.get(f"/sessions/{session_id}/translate")
    r = client.post(
        f"/sessions/{session_id}/entries",
        json={"chinese": "你好"},
    )
    assert r.status_code == 200

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    # Step bar must be present
    assert 'class="step-bar"' in r.text
    # Translate should be done, Image active, Audio upcoming
    assert 'class="step done"' in r.text or 'step done' in r.text
    assert 'class="step active"' in r.text or 'step active' in r.text


def test_audio_page_shows_step_bar():
    """The audio page must include the step progress bar with
    'Translate' and 'Image' as done, 'Audio' as active.

    Story F2: Visual progress bar shows which pipeline step the user is on.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Advance through translate and image steps
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    # Step bar must be present
    assert 'class="step-bar"' in r.text
    # Translate and Image should be done, Audio active
    assert 'class="step active"' in r.text or 'step active' in r.text


def test_index_page_has_no_step_bar():
    """The index page must NOT include the step progress bar.

    Story F2: Step bar is only shown on translate, image, and audio pages.
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="step-bar"' not in r.text


def test_completion_page_has_no_step_bar():
    """The completion page must NOT include the step progress bar.

    Story F2: Step bar is only shown on translate, image, and audio pages.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    # Advance through the full pipeline to reach completion
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})
    # Confirm audio with Wiktionary to complete the word
    r = client.post(f"/audio/{session_id}", json={"source": "wiktionary"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("completed") is True

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert 'class="step-bar"' not in r.text


# ── Story F3: Index Page Redesign ──


def test_index_textarea_has_class():
    """The index page textarea must have the CSS class 'index-textarea'
    for styling with surface background, border, and rounded corners.

    Story F3: Textarea looks polished with Solarized Dark surface colours.
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="index-textarea"' in r.text
    assert 'id="words"' in r.text


def test_index_heading_has_class():
    """The index page heading must have the CSS class 'index-h1'
    for styling with text-highlight colour.

    Story F3: Headings use Solarized Dark text-highlight palette.
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="index-h1"' in r.text


def test_index_submit_button_has_primary_class():
    """The index page submit button must have the CSS class 'btn-primary'
    for styling with accent background and white text.

    Story F3: Primary button is visually prominent with accent colour.
    """
    client = _make_app()
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="btn-primary"' in r.text
    assert 'type="submit"' in r.text


def test_index_error_uses_error_box_class():
    """The index page error message must use the CSS class 'error-box'
    for styling with danger colour, border, and background.

    Story F3: Error messages are visually distinct with danger palette.
    """
    client = _make_app()
    # Submit empty form to trigger error
    r = client.post("/words", data={"words": ""})
    assert r.status_code == 200
    assert 'class="error-box"' in r.text


# ── Story F4: Translate Step Redesign ──


def test_translate_entry_has_card_class():
    """Each translation entry on the translate page must have the CSS class
    'entry-card' for styling with surface background and rounded corners.

    Story F4: Translation options presented as clear, tappable cards.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="entry-card"' in r.text


def test_translate_entry_shows_chinese_with_class():
    """Each translation entry must display Chinese characters using the
    'entry-chinese' class for large text-highlight styling.

    Story F4: Chinese characters are visually prominent.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="entry-chinese"' in r.text
    assert '你好' in r.text


def test_translate_entry_shows_jyutping_with_class():
    """Each translation entry must display Jyutping using the
    'entry-jyutping' class.

    Story F4: Jyutping is displayed with monospace font in standard text colour.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="entry-jyutping"' in r.text


def test_translate_entry_shows_definition_with_class():
    """Each translation entry must display the definition using the
    'entry-definition' class for smaller text styling.

    Story F4: Definition text is rendered smaller for visual hierarchy.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="entry-definition"' in r.text
    assert 'hello' in r.text


def test_translate_continue_button_is_primary():
    """The 'Continue to Images' button on the translate page must use the
    'btn-primary' class for accent styling.

    Story F4: Primary action button is visually prominent.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-primary"' in r.text
    assert 'Continue to Images' in r.text


def test_translate_skip_link_has_class():
    """The 'Skip this word' action on the translate page is now a button
    using the 'btn-skip' class for danger-colour styling.

    Story 5: Skip should look like a proper button.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-skip"' in r.text
    assert 'Skip this word' in r.text


def test_translate_pos_checkbox_has_class():
    """The 'Show part-of-speech hints' checkbox must use the
    'pos-checkbox' class for styled checkbox accent.

    Story F4: POS toggle is styled cleanly with accent colour.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]

    r = client.get(f"/translate/{session_id}")
    assert r.status_code == 200
    assert 'class="pos-checkbox"' in r.text


# ── Story F5: Image Step Redesign ──


def _advance_to_image_step(client, session_id):
    """Helper: advance a session from translate to image step."""
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})


def test_image_grid_has_class():
    """The image step page must wrap images in an element with the
    'image-grid' class for CSS grid layout.

    Story F5: Images displayed in a responsive CSS grid.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_image_step(client, session_id)

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert 'class="image-grid"' in r.text


def test_image_uses_card_class():
    """Each image on the image step page must be wrapped in an
    'image-card' element with surface background and rounded corners.

    Story F5: Images displayed in styled cards.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_image_step(client, session_id)

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert 'class="image-card"' in r.text


def test_image_thumb_has_class():
    """Each image must use the 'image-thumb' class for
    object-fit: cover and square aspect ratio styling.

    Story F5: Images constrained to equal aspect ratio squares.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_image_step(client, session_id)

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert 'class="image-thumb"' in r.text


def test_image_checkbox_has_class():
    """Each image checkbox must use the 'image-checkbox' class
    for positioning overlay on the image card.

    Story F5: Checkboxes styled as overlay on image cards.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_image_step(client, session_id)

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert 'class="image-checkbox"' in r.text


def test_image_continue_button_is_primary():
    """The 'Continue to Audio' button on the image page must use the
    'btn-primary' class for accent styling.

    Story F5: Primary action button is visually prominent.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_image_step(client, session_id)

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-primary"' in r.text
    assert 'Continue to Audio' in r.text


def test_image_skip_link_has_class():
    """The 'Skip this word' action on the image page is now a button
    using the 'btn-skip' class for danger-colour styling.

    Story 5: Skip should look like a proper button.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_image_step(client, session_id)

    r = client.get(f"/image/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-skip"' in r.text
    assert 'Skip this word' in r.text


# ── Story F6: Audio Step Redesign ──


def _advance_to_audio_step(client, session_id):
    """Helper: advance a session from start through to audio step."""
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})


def test_audio_jyutping_has_hero_class():
    """The audio step page must display jyutping using the
    'audio-jyutping' class for prominent hero styling with text-highlight.

    Story F6: Jyutping displayed as prominent hero element.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="audio-jyutping"' in r.text


def test_audio_pos_has_class():
    """The audio step page must display the part-of-speech hint using
    the 'audio-pos' class for cyan italic styling.

    Story F6: POS hint displayed below jyutping in cyan italic.
    """
    # Use a fixture entry that includes a POS prefix in the definition
    entries = [("好", "hou2", "adj. good; well; fine")]
    cantodict_path = _make_cantodict_fixture(entries)
    card_db_path = _make_card_store_fixture()
    from card_store import CardStore
    from cantodict_lookup import CantoneseDictionary
    from card_generator import CardGenerator
    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_db_path)
    card_generator = CardGenerator()
    wiktionary_client = _make_wiktionary_client()
    brave_client = _make_brave_client()
    audio_download_client = _make_audio_download_client()
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

    r = client.post("/sessions", json={"words": ["good"]})
    session_id = r.json()["session_id"]
    # Advance manually since chinese differs from default fixture
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="audio-pos"' in r.text


def test_audio_confirm_wiktionary_uses_success():
    """The 'Confirm Wiktionary audio' button must use the 'btn-success'
    class for green success-colour styling.

    Story F6: Confirm Wiktionary audio button in success green.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-success"' in r.text
    assert 'Confirm Wiktionary audio' in r.text


def test_audio_record_button_uses_magenta():
    """The Record button must use the 'btn-magenta' class for
    magenta-colour styling and include a microphone icon.

    Story F6: Record button in magenta with mic icon.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-magenta"' in r.text
    assert '&#x1F399;' in r.text or '🎙' in r.text


def test_audio_stop_button_uses_danger():
    """The Stop button must use the 'btn-danger' class for
    red danger-colour styling.

    Story F6: Stop button in danger colour.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-danger"' in r.text
    assert 'Stop' in r.text


def test_audio_recording_section_uses_card():
    """The recording section on the audio step page must use the
    'recording-card' class for surface-background card styling.

    Story F6: Recording section styled as a card with surface background.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="recording-section recording-card"' in r.text


def test_audio_preview_section_uses_card():
    """The recording preview section on the audio step page must use the
    'preview-card' class for card styling with success border.

    Story F6: Preview section styled as a card with green accent.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="recording-preview preview-card"' in r.text


def test_audio_skip_link_has_class():
    """The 'Skip this word' action on the audio page is now a button
    using the 'btn-skip' class for danger-colour styling.

    Story 5: Skip should look like a proper button.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_audio_step(client, session_id)

    r = client.get(f"/audio/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-skip"' in r.text
    assert 'Skip this word' in r.text


# ── Story F7: Completion Page Redesign ──


def _advance_to_completion(client, session_id):
    """Helper: advance a session through the full pipeline to completion."""
    client.get(f"/sessions/{session_id}/translate")
    client.post(f"/sessions/{session_id}/entries", json={"chinese": "你好"})
    client.post(f"/sessions/{session_id}/images", json={"result_index": 0})
    r = client.post(f"/audio/{session_id}", json={"source": "wiktionary"})
    return r.json()


def test_completion_success_banner():
    """The completion page must show a success banner with the
    'success-banner' class, 'All Done!' heading, and a checkmark.

    Story F7: Step bar replaced with a success banner.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_completion(client, session_id)

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert 'class="success-banner"' in r.text
    assert 'All Done' in r.text
    assert '&#10003;' in r.text


def test_completion_uses_table():
    """The completion page must render card summaries in a
    'completion-table' table with proper columns.

    Story F7: Card summary as a table.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_completion(client, session_id)

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert 'class="completion-table"' in r.text
    assert '<table' in r.text


def test_completion_table_has_columns():
    """The completion table must have columns for Cantonese, Jyutping,
    Part of Speech, and English.

    Story F7: Table columns for card data.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_completion(client, session_id)

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert 'Cantonese' in r.text
    assert 'Jyutping' in r.text
    assert 'Part of Speech' in r.text
    assert 'English' in r.text
    # Card data should also be present
    assert '你好' in r.text
    assert 'hello' in r.text


def test_completion_export_is_primary():
    """The Export .apkg link on the completion page must use the
    'btn-primary' class for prominent accent styling.

    Story F7: Export button as prominent primary button.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_completion(client, session_id)

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert 'class="btn-primary"' in r.text
    assert 'Export .apkg' in r.text


def test_completion_start_new_session_uses_text_link():
    """The 'Start New Session' link on the completion page must use the
    'text-link' class for secondary styling.

    Story F7: Start New Session as secondary link.
    """
    client = _make_app()
    r = client.post("/sessions", json={"words": ["hello"]})
    session_id = r.json()["session_id"]
    _advance_to_completion(client, session_id)

    r = client.get(f"/complete/{session_id}")
    assert r.status_code == 200
    assert 'class="text-link"' in r.text
    assert 'Start New Session' in r.text
