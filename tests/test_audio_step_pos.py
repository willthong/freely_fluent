"""Tests for part-of-speech display on the audio step page.

PRD app.py + Templates section: Show part-of-speech alongside Jyutping,
formatted with <em>.
"""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from jyutping_format import format_jyutping


def _env():
    env = Environment(loader=FileSystemLoader("templates"), cache_size=0)
    env.filters["format_jyutping"] = format_jyutping
    return env


def test_template_shows_pos_when_present():
    """audio_step.html shows POS in <em> when part_of_speech is passed."""
    env = _env()
    template = env.get_template("audio_step.html")
    html = template.render(
        session_id="abc123",
        characters="\u8dd1",
        jyutping="pou2",
        audio_url="http://example.com/audio.ogg",
        part_of_speech="v",
    )
    assert "<em>(v)</em>" in html


def test_template_no_pos_when_empty():
    """audio_step.html does not show POS when part_of_speech is empty."""
    env = _env()
    template = env.get_template("audio_step.html")
    html = template.render(
        session_id="abc123",
        characters="\u4f60\u597d",
        jyutping="nei5 hou2",
        audio_url="http://example.com/audio.ogg",
        part_of_speech="",
    )
    assert "<em>(v)</em>" not in html
    assert "<em>(n)</em>" not in html


def _build_app_with_mock(cantodict, capture):
    """Create an app with mocked orchestrator and templates.

    Returns (app, capture_dict). capture["context"] receives the
    template context for each TemplateResponse call.
    """
    import tempfile
    from card_store import CardStore

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)

    mock_orchestrator = Mock(spec=["lookup_translations", "search_images",
                                    "fetch_wiktionary_audio_url", "confirm_audio"])
    mock_orchestrator.lookup_translations = cantodict.lookup
    mock_orchestrator.search_images.return_value = [{"url": "http://example.com/img.jpg"}]
    mock_orchestrator.fetch_wiktionary_audio_url.return_value = "http://example.com/audio.ogg"
    mock_orchestrator.confirm_audio.return_value = True

    mock_templates = Mock(spec=["TemplateResponse"])

    def capture_template_response(request, name, context):
        capture["context"] = context
        return HTMLResponse(content="<html></html>")

    mock_templates.TemplateResponse.side_effect = capture_template_response

    with patch("app.Jinja2Templates", return_value=mock_templates):
        with patch("app.PipelineOrchestrator", return_value=mock_orchestrator):
            with patch("app.WiktionaryAudio"):
                with patch("app.AudioService"):
                    with patch("app.BraveImageSearch"):
                        from app import create_app
                        app = create_app(
                            cantodict=cantodict,
                            card_store=store,
                            api_key="test",
                        )

    return app


def test_app_passes_pos_to_template():
    """app.py audio_step endpoint passes part_of_speech to template context."""
    mock_cantodict = Mock()
    mock_cantodict.lookup = Mock(return_value=[{
        "chinese": "\u8dd1",
        "jyutping": "pou2",
        "definition": "v. to run",
        "part_of_speech": "v",
    }])

    capture = {"context": None}
    app = _build_app_with_mock(mock_cantodict, capture)
    client = TestClient(app)

    resp = client.post("/sessions", json={"words": ["run"]})
    sid = resp.json()["session_id"]
    client.post(f"/sessions/{sid}/entries", json={"chinese": "\u8dd1"})
    client.post(f"/sessions/{sid}/images", json={"result_index": 0})

    page = client.get(f"/audio/{sid}")
    assert page.status_code == 200

    assert capture["context"].get("part_of_speech") == "v"


def test_app_passes_empty_pos_when_entry_has_none():
    """app.py passes empty part_of_speech when entry has no POS."""
    mock_cantodict = Mock()
    mock_cantodict.lookup = Mock(return_value=[{
        "chinese": "\u4f60\u597d",
        "jyutping": "nei5 hou2",
        "definition": "hello; hi",
        # No part_of_speech
    }])

    capture = {"context": None}
    app = _build_app_with_mock(mock_cantodict, capture)
    client = TestClient(app)

    resp = client.post("/sessions", json={"words": ["hello"]})
    sid = resp.json()["session_id"]
    client.post(f"/sessions/{sid}/entries", json={"chinese": "\u4f60\u597d"})
    client.post(f"/sessions/{sid}/images", json={"result_index": 0})

    page = client.get(f"/audio/{sid}")
    assert page.status_code == 200

    assert capture["context"].get("part_of_speech") == ""
