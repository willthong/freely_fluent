"""FastAPI app wiring modules together.

REST-style routes for the card-creation pipeline.
All dependencies are injected via create_app factory for testability.
Pipeline step logic is delegated to PipelineOrchestrator (Story 20).
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import uuid

logger = logging.getLogger(__name__)

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from pipeline_orchestrator import PipelineOrchestrator
from brave_image_search import BraveImageSearch
from audio_service import AudioService
from card_generator import CardGenerator
from card_store import CardStore, CardStoreProtocol
from cantodict_lookup import CantoneseDictionary
from jyutping_format import format_jyutping
from session_manager import SessionManager
from wiktionary_audio import WiktionaryAudio


# ── Request Models ──

class SessionStartRequest(BaseModel):
    words: list[str]


class AudioSelectRequest(BaseModel):
    source: str
    jyutping: str | None = None


class RecordingRequest(BaseModel):
    recording: str


class EntrySelectRequest(BaseModel):
    chinese: str


class ImageSelectRequest(BaseModel):
    result_index: int


class PosToggleRequest(BaseModel):
    include_pos: bool


def create_app(
    cantodict: CantoneseDictionary | None = None,
    card_store: CardStore | None = None,
    card_generator: CardGenerator | None = None,
    wiktionary_client: httpx.Client | None = None,
    brave_client: httpx.Client | None = None,
    audio_download_client: httpx.Client | None = None,
    image_download_client: httpx.Client | None = None,
    api_key: str | None = None,
) -> FastAPI:
    """Create a FastAPI app with injected dependencies."""

    app = FastAPI(title="Freely Fluent")

    # Mount static files if the directory exists; warn if missing.
    static_dir = "static"
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    else:
        logger.warning("Static directory '%s' not found — skipping static file mount", static_dir)

    env = Environment(loader=FileSystemLoader("templates"), cache_size=0)
    env.filters["format_jyutping"] = format_jyutping
    templates = Jinja2Templates(env=env)

    # Prevent browser caching of HTML pages during development
    @app.middleware("http")
    async def add_no_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if "text/html" in response.headers.get("content-type", ""):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # In-memory session store scoped to this app instance
    _sessions: dict[str, SessionManager] = {}

    deps: dict[str, object] = {
        "cantodict": cantodict,
        "card_store": card_store,
        "card_generator": card_generator,
        "wiktionary_client": wiktionary_client,
        "brave_client": brave_client,
        "audio_download_client": audio_download_client,
        "api_key": api_key,
    }

    # ── Eager service creation for orchestrator ──

    if deps["cantodict"] is None:
        raise RuntimeError("cantodict not configured")

    wiktionary = WiktionaryAudio(client=deps["wiktionary_client"])
    audio_svc = AudioService(client=deps["audio_download_client"])
    brave = (
        BraveImageSearch(api_key=deps["api_key"], client=deps["brave_client"])
        if deps["api_key"]
        else None
    )
    if image_download_client is None:
        # Default: use audio_download_client for image resolution,
        # or create a real HTTP client if neither is provided.
        if audio_download_client is not None:
            image_download_client = audio_download_client
        else:
            image_download_client = httpx.Client(
                headers={"User-Agent": "Mozilla/5.0 (FreeLyFluent)"},
                timeout=15,
            )

    orchestrator = PipelineOrchestrator(
        cantodict=deps["cantodict"],
        brave=brave,
        wiktionary=wiktionary,
        audio_svc=audio_svc,
    )

    # ── Lazy getters ──

    def _get_cantodict():
        return deps["cantodict"]

    def _get_card_store():
        if deps["card_store"] is None:
            raise RuntimeError("card_store not configured")
        return deps["card_store"]

    def _get_card_store_or_none() -> "CardStoreProtocol | None":
        return deps["card_store"]

    def _get_image_download_client() -> httpx.Client:
        return image_download_client

    def _get_card_generator():
        if deps["card_generator"] is None:
            raise RuntimeError("card_generator not configured")
        return deps["card_generator"]

    def _get_audio_service():
        return audio_svc

    def _get_orchestrator():
        return orchestrator

    def _get_brave_search() -> BraveImageSearch:
        if deps["api_key"] is None or brave is None:
            raise RuntimeError("BRAVE_SEARCH_API_KEY not configured")
        return brave

    # ── Index (home page) ──

    @app.get("/", response_class=HTMLResponse)
    def index_page(request: Request, error: str | None = None):
        """Render the home page with a textarea for pasting words."""
        return templates.TemplateResponse(
            request,
            "index.html",
            {"error": error},
        )

    @app.post("/words")
    def submit_words(request: Request, words: str | None = Form(default=None)):
        """Accept pasted words, create a session, redirect to translate step."""
        word_list = [w.strip() for w in (words or "").splitlines() if w.strip()]
        if not word_list:
            return templates.TemplateResponse(
                request,
                "index.html",
                {"error": "No words entered. Paste a list and try again."},
            )
        session = SessionManager(
            word_list,
            card_store=_get_card_store_or_none(),
            http_client=_get_image_download_client(),
        )
        session_id = uuid.uuid4().hex
        session._session_id = session_id
        _sessions[session_id] = session
        return Response(status_code=303, headers={"Location": f"/translate/{session_id}"})

    # ── Session lifecycle ──

    @app.post("/sessions")
    def start_session(req: SessionStartRequest):
        session = SessionManager(
            req.words,
            card_store=_get_card_store_or_none(),
            http_client=_get_image_download_client(),
        )
        session_id = uuid.uuid4().hex
        session._session_id = session_id
        _sessions[session_id] = session
        return {
            "session_id": session_id,
            "current_word": session.current_word,
            "current_step": session.current_step,
        }

    @app.get("/sessions")
    def list_sessions():
        """Return summaries of all active sessions."""
        return [
            {
                "id": sid,
                "current_word": sm.current_word,
                "current_step": sm.current_step,
                "is_complete": sm.is_complete,
            }
            for sid, sm in _sessions.items()
        ]

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str):
        """Return full details of a single session."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        return {
            "id": session_id,
            "words": session._words,
            "current_word": session.current_word,
            "current_step": session.current_step,
            "is_complete": session.is_complete,
            "selected_characters": session.selected_characters,
            "selected_entry": session.selected_entry,
            "selected_images": session.selected_images,
            "image_offset": session.image_offset,
            "include_pos": session._include_pos,
        }

    @app.post("/sessions/{session_id}/pos-toggle")
    def toggle_pos(session_id: str, req: PosToggleRequest):
        """Toggle whether part-of-speech hints appear on cards."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        session.set_include_pos(req.include_pos)
        return {"include_pos": session._include_pos}

    @app.delete("/sessions/{session_id}")
    def delete_session(session_id: str):
        """Remove a session."""
        if session_id not in _sessions:
            return Response(status_code=404)
        del _sessions[session_id]
        return Response(status_code=204)

    # ── Translate step (HTML page) ──

    @app.get("/translate/{session_id}", response_class=HTMLResponse)
    def translate_step(request: Request, session_id: str):
        """Render the translate step page with Cantonese entries."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        if session.current_word is None:
            return Response(status_code=404)
        if session.current_step != "translate":
            return Response(status_code=400)
        entries = _get_orchestrator().lookup_translations(session, session.current_word)
        return templates.TemplateResponse(
            request,
            "translate_step.html",
            {
                "session_id": session_id,
                "english_word": session.current_word,
                "entries": entries,
                "include_pos": session._include_pos,
                "current_step": session.current_step,
                "words": session.words,
                "word_index": session._word_index,
            },
        )

    @app.post("/translate/{session_id}/select")
    def select_translation(session_id: str, chinese: str = Form(default="")):
        """Select a translation entry and redirect to image step."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        entries = _get_orchestrator().lookup_translations(session, session.current_word)
        entry = next((e for e in entries if e.get("chinese") == chinese), None)
        if entry is None:
            return Response(status_code=404)
        session.select_entry(entry)
        return Response(status_code=303, headers={"Location": f"/image/{session_id}"})

    # ── Translate (programmatic) ──

    @app.get("/sessions/{session_id}/translate")
    def get_translations(session_id: str):
        session = _sessions.get(session_id)
        if session is None or session.current_word is None:
            return Response(status_code=404)
        if session.current_step != "translate":
            return {"error": "not on translate step"}
        entries = _get_orchestrator().lookup_translations(session, session.current_word)
        if not entries:
            word = session.current_word
            session.skip()
            return {
                "entries": [],
                "message": f"No results found for {word}",
                "current_word": session.current_word,
                "current_step": session.current_step,
                "completed": session.is_complete,
            }
        return {"entries": entries, "current_word": session.current_word}

    @app.post("/sessions/{session_id}/entries")
    def select_entry(session_id: str, req: EntrySelectRequest):
        session = _sessions.get(session_id)
        if session is None or session.current_word is None:
            return Response(status_code=404)
        entries = _get_orchestrator().lookup_translations(session, session.current_word)
        entry = next((e for e in entries if e.get("chinese") == req.chinese), None)
        if entry is None:
            return Response(status_code=404)
        session.select_entry(entry)
        return {"current_step": session.current_step, "current_word": session.current_word}

    # ── Images (programmatic) ──

    @app.get("/sessions/{session_id}/images")
    def get_images(session_id: str):
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return {"error": "no entry selected"}
        results = _get_orchestrator().search_images(session)
        session.store_image_results(results)
        return {"results": results}

    @app.post("/sessions/{session_id}/images")
    def add_image(session_id: str, req: ImageSelectRequest):
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return {"error": "no entry selected"}
        results = session.all_image_results or _get_orchestrator().search_images(session)
        if req.result_index < 0 or req.result_index >= len(results):
            return Response(status_code=404)
        session.add_image(results[req.result_index])
        return {"current_step": session.current_step, "current_word": session.current_word}

    # ── Images (load more) ──

    @app.get("/sessions/{session_id}/images/load-more")
    def load_more_images(session_id: str):
        """Fetch the next batch of image results and append to accumulated results."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return {"error": "no entry selected"}
        offset = session.load_more_images()
        results = _get_orchestrator().search_images(session, offset=offset)
        session.store_image_results(results)
        return {"results": results}

    # ── Wiktionary Audio ──

    @app.get("/sessions/{session_id}/wiktionary-audio")
    def get_wiktionary_audio(session_id: str):
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return Response(status_code=400)
        url = _get_orchestrator().fetch_wiktionary_audio_url(session)
        if url is None:
            return Response(status_code=404)
        return {"url": url}

    # ── Audio (play) ──

    @app.get("/sessions/{session_id}/audio")
    def play_audio(session_id: str):
        """Download Wiktionary audio and stream it for playback."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return Response(status_code=400)
        url = _get_orchestrator().fetch_wiktionary_audio_url(session)
        if url is None:
            return Response(status_code=404)
        audio_bytes = _get_orchestrator().play_audio(session, url)
        if audio_bytes is None:
            return Response(status_code=404)
        return Response(content=audio_bytes, media_type="audio/ogg")

    # ── Audio (recording submit) ──

    @app.post("/sessions/{session_id}/recording")
    def submit_recording(session_id: str, req: RecordingRequest, request: Request):
        """Accept a base64-encoded browser recording and save to the session."""
        logger.info(f"submit_recording called: session_id={session_id}, recording_len={len(req.recording)}")
        session = _sessions.get(session_id)
        if session is None:
            logger.warning(f"submit_recording: session {session_id} not found")
            return Response(status_code=404)
        audio_bytes = base64.b64decode(req.recording)
        session.save_recording(audio_bytes)
        logger.info(f"submit_recording: saved {len(audio_bytes)} bytes for session {session_id}")
        return {"status": "saved"}

    # ── Audio (recording playback) ──

    @app.get("/sessions/{session_id}/recording")
    def play_recording(session_id: str):
        """Stream back the saved recording for preview."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        recording = session.get_recording()
        if recording is None:
            return Response(status_code=404)
        return Response(content=recording, media_type="audio/webm")

    # ── Audio (select/confirm) ──

    @app.post("/sessions/{session_id}/audio")
    def select_audio(session_id: str, req: AudioSelectRequest):
        """Confirm audio choice, save card, advance to next word."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return {"error": "no entry selected"}
        result = _get_orchestrator().confirm_audio(session, req.source, jyutping=req.jyutping)
        if result is None:
            return {"error": "audio confirmation failed, check entry and images"}
        return {
            "completed": session.is_complete,
            "current_word": session.current_word,
            "current_step": session.current_step,
        }

    # ── Audio step (HTML page) ──

    @app.get("/audio/{session_id}", response_class=HTMLResponse)
    def audio_step(request: Request, session_id: str):
        """Render the audio step page with Wiktionary audio player, Jyutping,
        and confirm/skip buttons."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return Response(status_code=400)
        if session.current_step != "audio":
            return Response(status_code=400)
        jyutping = session.selected_entry.get("jyutping", "")
        part_of_speech = session.selected_entry.get("part_of_speech", "")
        url = _get_orchestrator().fetch_wiktionary_audio_url(session)
        return templates.TemplateResponse(
            request,
            "audio_step.html",
            {
                "session_id": session_id,
                "characters": characters,
                "jyutping": jyutping,
                "audio_url": url,
                "part_of_speech": part_of_speech,
                "current_step": session.current_step,
            },
        )

    @app.post("/audio/{session_id}")
    def confirm_audio_step(session_id: str, req: AudioSelectRequest):
        """Confirm audio choice from the audio step page.

        Returns JSON with completed status. HTMX frontend handles
        redirect to completion page when completed=True.
        """
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return {"error": "no entry selected"}
        result = _get_orchestrator().confirm_audio(session, req.source, jyutping=req.jyutping)
        if result is None:
            return {"error": "audio confirmation failed, check entry and images"}
        return {
            "completed": session.is_complete,
            "current_word": session.current_word,
            "current_step": session.current_step,
        }

    # ── Image step (HTML page) ──

    @app.get("/image/{session_id}", response_class=HTMLResponse)
    def image_step(request: Request, session_id: str):
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return Response(status_code=400)
        if session.current_step != "image":
            return Response(status_code=400)
        results = _get_orchestrator().search_images(session)
        session.store_image_results(results)
        return templates.TemplateResponse(
            request,
            "image_step.html",
            {
                "session_id": session_id,
                "results": results,
                "current_step": session.current_step,
                "image_offset": session.image_offset,
                "all_result_count": len(session.all_image_results),
            },
        )

    @app.get("/image/{session_id}/load-more")
    def load_more_image_cards(request: Request, session_id: str):
        """HTMX endpoint: fetch next batch of images and return card HTML."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return Response(status_code=400)
        if session.current_step != "image":
            return Response(status_code=400)
        offset = session.load_more_images()
        results = _get_orchestrator().search_images(session, offset=offset)
        session.store_image_results(results)
        return templates.TemplateResponse(
            request,
            "_image_cards.html",
            {
                "results": results,
                "image_offset": session.image_offset,
            },
        )

    @app.post("/image/{session_id}")
    def submit_images(session_id: str, images: list[str] | None = Form(default=None)):
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        characters = session.selected_characters
        if not characters:
            return Response(status_code=400)
        results = session.all_image_results or _get_orchestrator().search_images(session)
        for idx_str in images or []:
            idx = int(idx_str)
            if 0 <= idx < len(results):
                session.add_image(results[idx])
        if not session.selected_images:
            return RedirectResponse(url=f"/image/{session_id}", status_code=303)
        return RedirectResponse(url=f"/audio/{session_id}", status_code=303)

    # ── Skip ──

    @app.api_route("/sessions/{session_id}/skip", methods=["GET", "POST"])
    def skip_word(request: Request, session_id: str):
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        session.skip()
        if request.method == "GET":
            # Template <a href> links send GET — redirect to next page
            if session.is_complete:
                return RedirectResponse(
                    url=f"/complete/{session_id}", status_code=303
                )
            return RedirectResponse(
                url=f"/translate/{session_id}", status_code=303
            )
        # POST — return JSON for API clients (existing contract)
        return {
            "current_word": session.current_word,
            "current_step": session.current_step,
            "completed": session.is_complete,
        }

    # ── Remove word ──

    @app.post("/sessions/{session_id}/words/{word_index:int}/remove")
    def remove_word(session_id: str, word_index: int):
        """Remove a word from the session's word list."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        try:
            session.remove_word_at(word_index)
        except IndexError:
            return Response(status_code=404)
        return {
            "words": session.words,
            "current_word": session.current_word,
            "current_step": session.current_step,
            "is_complete": session.is_complete,
        }

    # ── Export ──

    @app.get("/export")
    def export_apkg(request: Request):
        store = _get_card_store()
        session_id = request.query_params.get("session_id")
        if session_id:
            flashcards = store.get_by_session(session_id)
        else:
            flashcards = store.get_all()
        generator = _get_card_generator()
        tmp = tempfile.NamedTemporaryFile(suffix=".apkg", delete=False)
        tmp_path = tmp.name
        tmp.close()
        generator.generate_apkg(flashcards, tmp_path)
        try:
            with open(tmp_path, "rb") as f:
                data = f.read()
        finally:
            os.unlink(tmp_path)
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="cantonese_words.apkg"'},
        )

    # ── Completion step (HTML page) ──

    @app.get("/complete/{session_id}", response_class=HTMLResponse)
    def completion_step(request: Request, session_id: str):
        """Render the completion screen with card summary and export link."""
        session = _sessions.get(session_id)
        if session is None:
            return Response(status_code=404)
        store = _get_card_store()
        session_key = session._session_id or session_id
        cards = store.get_by_session(session_key)
        return templates.TemplateResponse(
            request,
            "completion.html",
            {
                "cards": cards,
                "card_count": len(cards),
                "export_url": f"/export?session_id={session_key}",
            },
        )

    # ── Health ──

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app


# ── Dev server entry point ──

if __name__ == "__main__":
    import uvicorn

    cantodict_path = os.environ.get("CANTODICT_PATH")
    cd = CantoneseDictionary(cantodict_path) if cantodict_path else None
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    app = create_app(cantodict=cd, api_key=api_key)
    uvicorn.run(app, host="0.0.0.0", port=8000)
