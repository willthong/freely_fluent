# Freely Fluent — PRD

## Problem

A native Cantonese speaker following the Fluent Forever method needs image-based, audio-backed Anki flashcards. Manually searching for translations, finding images, sourcing pronunciations, and assembling cards breaks study flow.

## Solution

A FastAPI/Python web app guiding the user through a structured pipeline: paste English words → pick Cantonese translation → select image → source audio → generate reversible Anki flashcard. Cards persist to SQLite and export as `.apkg`. Docker-deployed.

## Architecture

- **Backend**: FastAPI + HTMX/Jinja2
- **Sessions**: Server-side state machine (translate → image → audio)
- **Deployment**: Docker
- **Tooling**: uv, ruff, ty

### Modules

| Module                  | Responsibility |
|-------------------------|----------------|
| `pipeline_orchestrator` | Concentrates Pipeline Step logic behind a deep seam |
| `cantodict_lookup`      | Bundled SQLite lookup by English word → entries |
| `brave_image_search`    | Brave Search API (image thumbnails with pagination) |
| `wiktionary_audio`      | Refactored to `WiktionaryAudio` class with injected client, fetch/parse split  |
| `card_generator`        | genanki reversed cards → self-contained `.apkg` |
| `audio_service`         | `download_audio()` only — one method  |
| `card_store`            | `save_flashcard(flashcard: Flashcard)` — interface deepened  |
| `session_manager`       | Accepts `CardStore` adapter, completes save-advance internally  |
| `app`                   | Thin route pass-throughs calling orchestrator  |

### Pipeline Steps (per word)

1. **Translate**: Query cantodict SQLite, show entries with select/skip
2. **Image**: Brave thumbnails with checkboxes, "load more" for pagination
3. **Audio**: Wiktionary playback or browser recording
4. **Save**: Persist card to SQLite, advance to next word

A skip button is available at every step.

### Card Design

- **Model**: Basic Reversed (audio→images and images→audio)
- Jyutping on both sides of every card direction
- English word and Chinese characters excluded from card face
- **Deck**: `cantonese_words`
- **Export**: `cantonese_words.apkg`

### Configuration

- `BRAVE_SEARCH_API_KEY` (env var, free tier)
- Wiktionary: hardcoded (no auth)
- `cantodict.sqlite`: bundled under `data/` (CC4.0)
- Image batch size: 12 (default)

## User Stories

### Core Pipeline (1–19) ✅

All implemented and verified (95+ tests, TDD).

### Architecture Deepening (20–25)

| # | Story | Status |
|---|-------|--------|
| 24 | Move `_sessions` into app factory | ✅ Complete — inside `create_app()`, tests verify isolation |
| 25 | Remove dead code from `AudioService` | ✅ Complete — one method (`download_audio`) |
| 22 | Deepen `CardStore.save_flashcard()` interface | ✅ Complete — accepts `Flashcard` dataclass |
| 21 | `SessionManager` accepts `CardStore`, completes save-advance | ✅ Complete — injected at constructor, save in `select_audio` |
| 23 | Refactor `wiktionary_audio` into class with fetch/parse split | ✅ Done — `WiktionaryAudio` class with injected httpx client, fetch/parse split, LL-Q9186 support |
| 20 | Extract `PipelineOrchestrator` from `app.py` | ✅ — new module concentrating pipeline step logic |

## Out of Scope

- Languages other than Cantonese (v1)
- Anki deck syncing (manual `.apkg` export)
- Multi-user support
- Advanced SRS logic (Anki's job)
- Image quality filtering, audio duration constraints
- PWA features, API authentication

## Notes

- CantoDict data from [cantodict-archive](https://github.com/awong-dev/cantodict-archive) (CC4.0)
- Chinese characters used as internal lookup key only, never on card face
- Audio stored in original format (WebM from browser, OGG/MP3 from Wiktionary)
- genanki regenerates full `.apkg` from SQLite on each export
- Single user working through a word list in focused session

## Architecture Deepening Rationale

The graphify knowledge graph (302 nodes, 545 edges, 20 communities) identifies `SessionManager` and `CardStore` as cross-community bridges, and `app.py` as the most connected community (44 nodes). The six deepening opportunities concentrate behaviour behind deeper seams, turning scattered inline logic into testable modules with clear interfaces.
