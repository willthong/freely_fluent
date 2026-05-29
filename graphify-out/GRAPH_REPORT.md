# Graph Report - .  (2026-05-29)

## Corpus Check
- 53 files · ~107,401 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 942 nodes · 1625 edges · 76 communities (39 shown, 37 thin omitted)
- Extraction: 69% EXTRACTED · 31% INFERRED · 0% AMBIGUOUS · INFERRED: 496 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_App Factory & Integration|App Factory & Integration]]
- [[_COMMUNITY_Domain Model Concepts|Domain Model Concepts]]
- [[_COMMUNITY_CardStore Tests (Persistence)|CardStore Tests (Persistence)]]
- [[_COMMUNITY_Flask App Routes|Flask App Routes]]
- [[_COMMUNITY_CantoDict Lookup + Tests|CantoDict Lookup + Tests]]
- [[_COMMUNITY_Wiktionary Audio Lookup|Wiktionary Audio Lookup]]
- [[_COMMUNITY_CardGenerator Tests (Opus)|CardGenerator Tests (Opus)]]
- [[_COMMUNITY_Audio Service|Audio Service]]
- [[_COMMUNITY_SessionManager (State Logic)|SessionManager (State Logic)]]
- [[_COMMUNITY_SessionManager Tests (Persistence)|SessionManager Tests (Persistence)]]
- [[_COMMUNITY_SessionManager Tests (CantoDict)|SessionManager Tests (CantoDict)]]
- [[_COMMUNITY_Card Generator (.apkg)|Card Generator (.apkg)]]
- [[_COMMUNITY_POS Toggle Tests|POS Toggle Tests]]
- [[_COMMUNITY_CardStore Tests (Images)|CardStore Tests (Images)]]
- [[_COMMUNITY_CardStore (SQLite)|CardStore (SQLite)]]
- [[_COMMUNITY_Card Templates Tests|Card Templates Tests]]
- [[_COMMUNITY_Index Step Tests|Index Step Tests]]
- [[_COMMUNITY_App Session Lifecycle Tests|App Session Lifecycle Tests]]
- [[_COMMUNITY_SessionManager POS Tests|SessionManager POS Tests]]
- [[_COMMUNITY_CardGenerator Tests (Main)|CardGenerator Tests (Main)]]
- [[_COMMUNITY_Translate Step Tests|Translate Step Tests]]
- [[_COMMUNITY_Dockerfile Tests|Dockerfile Tests]]
- [[_COMMUNITY_Completion Step Tests|Completion Step Tests]]
- [[_COMMUNITY_SessionManager (Advance Word)|SessionManager (Advance Word)]]
- [[_COMMUNITY_Brave Image Search Tests|Brave Image Search Tests]]
- [[_COMMUNITY_Session Isolation Tests|Session Isolation Tests]]
- [[_COMMUNITY_Pipeline Orchestrator Tests|Pipeline Orchestrator Tests]]
- [[_COMMUNITY_CardStore Image Tests|CardStore Image Tests]]
- [[_COMMUNITY_Audio Step POS Tests|Audio Step POS Tests]]
- [[_COMMUNITY_SessionManager (Accessors)|SessionManager (Accessors)]]
- [[_COMMUNITY_Audio Persistence Tests|Audio Persistence Tests]]
- [[_COMMUNITY_README Tests|README Tests]]
- [[_COMMUNITY_Main Entry Tests|Main Entry Tests]]
- [[_COMMUNITY_Completion POS Tests|Completion POS Tests]]
- [[_COMMUNITY_Opus E2E Tests|Opus E2E Tests]]
- [[_COMMUNITY_SessionManager HTTP Tests|SessionManager HTTP Tests]]
- [[_COMMUNITY_Wiktionary Audio (Parsing)|Wiktionary Audio (Parsing)]]
- [[_COMMUNITY_Wiktionary Audio (HTTP)|Wiktionary Audio (HTTP)]]
- [[_COMMUNITY_Deployment Config|Deployment Config]]
- [[_COMMUNITY_Session Skip Tests|Session Skip Tests]]
- [[_COMMUNITY_Image Resolve Fail Tests|Image Resolve Fail Tests]]
- [[_COMMUNITY_Session Init Tests|Session Init Tests]]
- [[_COMMUNITY_Audio Missing Entry Tests|Audio Missing Entry Tests]]
- [[_COMMUNITY_Image LoadMore Tests|Image LoadMore Tests]]
- [[_COMMUNITY_Audio Missing Images Tests|Audio Missing Images Tests]]
- [[_COMMUNITY_Skip Reset Tests|Skip Reset Tests]]
- [[_COMMUNITY_Step Progression Tests|Step Progression Tests]]
- [[_COMMUNITY_Session Complete Tests|Session Complete Tests]]
- [[_COMMUNITY_Audio Select Tests|Audio Select Tests]]
- [[_COMMUNITY_Full Pipeline Tests|Full Pipeline Tests]]
- [[_COMMUNITY_Audio Missing Audio Tests|Audio Missing Audio Tests]]
- [[_COMMUNITY_Brave Redirect Tests|Brave Redirect Tests]]
- [[_COMMUNITY_Image Resolve Error Tests|Image Resolve Error Tests]]
- [[_COMMUNITY_Recording Default Tests|Recording Default Tests]]
- [[_COMMUNITY_Multi-Image Tests|Multi-Image Tests]]
- [[_COMMUNITY_Audio Backward Compat Tests|Audio Backward Compat Tests]]
- [[_COMMUNITY_Redirect Malformed Tests|Redirect Malformed Tests]]
- [[_COMMUNITY_CardStore Multi-Save Tests|CardStore Multi-Save Tests]]
- [[_COMMUNITY_CardStore GetAll Tests|CardStore GetAll Tests]]
- [[_COMMUNITY_Session Rationale 45|Session Rationale 45]]
- [[_COMMUNITY_Session Rationale 50|Session Rationale 50]]
- [[_COMMUNITY_Session Rationale 57|Session Rationale 57]]
- [[_COMMUNITY_Session Rationale 62|Session Rationale 62]]
- [[_COMMUNITY_Session Rationale 67|Session Rationale 67]]
- [[_COMMUNITY_Session Rationale 72|Session Rationale 72]]
- [[_COMMUNITY_Session Rationale 77|Session Rationale 77]]
- [[_COMMUNITY_Session Rationale 240|Session Rationale 240]]
- [[_COMMUNITY_CardGenerator Rationale 136|CardGenerator Rationale 136]]
- [[_COMMUNITY_CardGenerator Rationale 141|CardGenerator Rationale 141]]
- [[_COMMUNITY_CardGenerator Rationale 149|CardGenerator Rationale 149]]
- [[_COMMUNITY_CardGenerator Rationale 164|CardGenerator Rationale 164]]
- [[_COMMUNITY_CardGenerator Rationale 174|CardGenerator Rationale 174]]
- [[_COMMUNITY_CardStore Rationale 273|CardStore Rationale 273]]
- [[_COMMUNITY_Python 3.14 Requirement|Python 3.14 Requirement]]
- [[_COMMUNITY_uv Package Manager|uv Package Manager]]
- [[_COMMUNITY_CardGenerator Rationale 174|CardGenerator Rationale 174]]

## God Nodes (most connected - your core abstractions)
1. `CardStore` - 99 edges
2. `SessionManager` - 91 edges
3. `CardGenerator` - 66 edges
4. `CantoneseDictionary` - 62 edges
5. `Flashcard` - 62 edges
6. `create_app()` - 52 edges
7. `WiktionaryAudio` - 31 edges
8. `AudioService` - 28 edges
9. `PipelineOrchestrator` - 26 edges
10. `BraveImageSearch` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Brave Image Search (Step 3)` --conceptually_related_to--> `BraveImageSearch`  [INFERRED]
  README.md → brave_image_search.py
- `Session (Domain Concept)` --conceptually_related_to--> `SessionManager`  [INFERRED]
  CONTEXT.md → session_manager.py
- `genanki Flashcard Generation` --conceptually_related_to--> `CardGenerator`  [INFERRED]
  README.md → card_generator.py
- `.apkg Export Link` --conceptually_related_to--> `CardGenerator`  [INFERRED]
  templates/completion.html → card_generator.py
- `card_data Docker Volume` --conceptually_related_to--> `CardStore`  [INFERRED]
  docker-compose.yml → card_store.py

## Hyperedges (group relationships)
- **Card Creation Pipeline Flow** — CONTEXT_EnglishWord, CONTEXT_Entry, CONTEXT_ChosenAudio, CONTEXT_Flashcard [EXTRACTED 1.00]
- **UI Template Inheritance Chain** — TEMPLATE_base_htmx, TEMPLATE_index_wordInput, TEMPLATE_translate_radioSelect, TEMPLATE_image_checkboxSelect, TEMPLATE_audio_wiktionaryBtn, TEMPLATE_completion_cardSummary [INFERRED 0.85]
- **Dual Audio Source Paths** — CONTEXT_ChosenAudio, TEMPLATE_audio_wiktionaryBtn, TEMPLATE_audio_recording [EXTRACTED 0.95]

## Communities (76 total, 37 thin omitted)

### Community 0 - "App Factory & Integration"
Cohesion: 0.05
Nodes (104): Opus/Vorbis Anki Compatibility, Opus->Vorbis Re-encoding, SQLite Card Persistence, create_app(), Create a FastAPI app with injected dependencies., CantoneseDictionary, Look up Cantonese entries by English word in a cantodict SQLite database., CardGenerator (+96 more)

### Community 1 - "Domain Model Concepts"
Cohesion: 0.05
Nodes (47): Card Face Design (No Characters), Chosen Audio (Domain Concept), English Word (Domain Concept), Entry (Domain Concept), Flashcard (Domain Concept), LL-Q9186 Cantonese Audio Pattern, Pipeline Step (Domain Concept), Session (Domain Concept) (+39 more)

### Community 2 - "CardStore Tests (Persistence)"
Cohesion: 0.05
Nodes (39): Unit tests for CardStore.  Story 21: Extract CardStore into an ABC (CardStorePro, delete_flashcard on non-existent id does not raise., CardStore must be recognised as implementing CardStoreProtocol., CardStoreProtocol defines the expected method signatures., Multiple saves get incrementing ids., save_flashcard accepts a single Flashcard dataclass instead of 5 args., save_flashcard returns a Flashcard with auto-generated id., created_at is set to a UTC ISO timestamp. (+31 more)

### Community 3 - "Flask App Routes"
Cohesion: 0.09
Nodes (23): BaseModel, AudioSelectRequest, EntrySelectRequest, ImageSelectRequest, PosToggleRequest, FastAPI app wiring modules together.  REST-style routes for the card-creation pi, RecordingRequest, SessionStartRequest (+15 more)

### Community 4 - "CantoDict Lookup + Tests"
Cohesion: 0.08
Nodes (31): extract_pos(), Query the bundled cantodict-archive SQLite database by English word.  CantoDict, Extract a part-of-speech abbreviation from the start of a definition.      Canto, Return entries whose definition contains *english_word*.          Each returned, _make_fixture_db(), _make_fixture_db_pos(), Tests for cantodict_lookup module., extract_pos strips the 'n.' prefix and returns 'n'. (+23 more)

### Community 5 - "Wiktionary Audio Lookup"
Cohesion: 0.09
Nodes (32): Fetch and parse Cantonese audio URLs from Wiktionary.      Accepts an injected h, WiktionaryAudio, _make_client(), WiktionaryAudio.parse_html returns None for HTML with no Cantonese audio., WiktionaryAudio.parse_html matches LL-Q9186 Cantonese recordings., WiktionaryAudio.fetch_audio_url composes fetch_html and parse_html., WiktionaryAudio.fetch_audio_url returns None when page has no Cantonese audio., WiktionaryAudio.fetch_audio_url returns None when the page fails to load. (+24 more)

### Community 6 - "CardGenerator Tests (Opus)"
Cohesion: 0.06
Nodes (33): Opus detection and Vorbis re-encoding in CardGenerator., OGG audio that is already Vorbis is written as-is without conversion., Unknown audio bytes default to webm extension., Unknown image bytes default to png extension., WebM Opus detection: RIFF header + OpusHead is recognised as WebM/Opus., WebM Opus detection: WebM without OpusHead is not treated as Opus., WebM Opus detection: non-RIFF data is not treated as WebM/Opus., When ffmpeg converts WebM/Opus successfully, returns Vorbis data with 'ogg' ext. (+25 more)

### Community 7 - "Audio Service"
Cohesion: 0.07
Nodes (30): _mock_cantodict(), Unit tests for SessionManager.  Story 21: SessionManager accepts CardStore, comp, get_recording returns None if no recording saved., skip discards current word and moves to next., Complete pipeline for two words in sequence., STEPS constant defines the pipeline order., _decode_brave_redirect_url decodes a known Brave redirect to original URL., Brave redirect: decoded original URL downloads successfully → return its bytes. (+22 more)

### Community 8 - "SessionManager (State Logic)"
Cohesion: 0.06
Nodes (24): Store a browser recording for the current word., Retrieve the saved browser recording, or None., Set whether part-of-speech hints should appear on cards., Track session state through the pipeline steps.      Manages the current word in, Advance the image search offset by *batch_size*. Returns new offset., Record the chosen Entry and advance to the image step., Add an image to the selection. Advances to audio step if not yet there., SessionManager (+16 more)

### Community 9 - "SessionManager Tests (Persistence)"
Cohesion: 0.07
Nodes (30): _make_store(), When httpx raises RequestError, image can't be resolved.     select_audio return, When image is a URL string and no HTTP client is injected,     select_audio retu, Create a fresh CardStore backed by a temp file., SessionManager accepts a CardStoreProtocol at construction., When card_store is injected, select_audio saves the Flashcard., Saved Flashcard image_data includes all selected images., When fields are missing, select_audio returns None and does not save. (+22 more)

### Community 10 - "SessionManager Tests (CantoDict)"
Cohesion: 0.1
Nodes (25): _convert_to_vorbis(), _guess_audio_ext(), _guess_image_ext(), _is_opus(), _is_webm_opus(), _opus_to_vorbis(), Build genanki reversed cards from flashcards.  Custom note type with 4 fields (J, _webm_opus_to_vorbis() (+17 more)

### Community 11 - "Card Generator (.apkg)"
Cohesion: 0.1
Nodes (27): _make_app(), _make_audio_download_client(), _make_brave_client(), _make_cantodict_db(), _make_wiktionary_client(), Tests for the POS toggle feature (Story 4).  User can toggle part-of-speech hint, POST /sessions/{id}/pos-toggle with include_pos=false     toggles the session pr, POST /sessions/{id}/pos-toggle with include_pos=true     toggles the session pre (+19 more)

### Community 12 - "POS Toggle Tests"
Cohesion: 0.08
Nodes (26): Flashcard, One completed flashcard persisted to SQLite., A card saved via Flashcard object round-trips through get_flashcard., When a Flashcard has a session_id, it is persisted and retrievable., get_by_session returns only cards belonging to the given session., get_flashcard retrieves card by id., Saving a flashcard with no images returns empty list., Re-saving with the same uniqueness key replaces images. (+18 more)

### Community 13 - "CardStore Tests (Images)"
Cohesion: 0.1
Nodes (8): ABC, _looks_like_image(), SQLite persistence for completed flashcards., Save a list of image blobs for a card in the card_images table.          Deletes, Load all image blobs for a card, ordered by sort_order., Return all flashcards belonging to *session_id*., Remove cards whose image_data fails basic image magic detection.          Checks, _row_to_flashcard()

### Community 14 - "CardStore (SQLite)"
Cohesion: 0.12
Nodes (23): _get_model_from_apkg(), Tests for card_generator custom Anki model templates.  Story 7: The exported .ap, Production front: Images, optional POS on a new line in italics brackets., Production back: FrontSide + Jyutping + optional POS + audio playback., Card CSS centres text for both templates., CSS constrains image max dimensions to prevent oversized cards., CSS styles <em> elements for part-of-speech hints (grey, smaller)., Neither template qfmt nor afmt references English word or Chinese characters. (+15 more)

### Community 15 - "Card Templates Tests"
Cohesion: 0.12
Nodes (17): BraveImageSearch, Search for images via the Brave Search API.  Calls Brave's image search endpoint, Search Brave for images matching a query., Search for images matching *query*.          Returns a list of result dicts with, Clean up the httpx client if we own it., _make_client(), search returns thumbnail URLs for each result in a valid API response., search returns an empty list when the API returns an HTTP error. (+9 more)

### Community 16 - "Index Step Tests"
Cohesion: 0.13
Nodes (21): _make_app(), _make_audio_download_client(), _make_brave_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_wiktionary_client(), Integration tests for the index (home) page.  Story 1: I want to paste a list of, Create a fully configured app with all dependencies injected. (+13 more)

### Community 17 - "App Session Lifecycle Tests"
Cohesion: 0.14
Nodes (21): _make_app(), _make_audio_download_client(), _make_brave_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_wiktionary_client(), Integration tests for session lifecycle endpoints.  Story 23: Add HTTP endpoints, GET /sessions returns empty list when no sessions exist. (+13 more)

### Community 18 - "SessionManager POS Tests"
Cohesion: 0.11
Nodes (21): _make_store(), Tests for part-of-speech propagation through SessionManager.  Covers PRD stories, By default, include_pos is True — POS is included on cards., set_include_pos changes the preference., Without card_store, card_data dict includes part_of_speech., Without card_store, include_pos=False suppresses POS in card_data dict., Create a fresh CardStore backed by a temp file., When the selected entry has part_of_speech, it flows through     _build_card_dat (+13 more)

### Community 19 - "CardGenerator Tests (Main)"
Cohesion: 0.1
Nodes (20): One flashcard produces 2 Anki cards (reversed pair)., When a flashcard has multiple images, all are written to media     and appear on, N flashcards produce N × 2 Anki cards., Jyutping tone numbers in card fields are formatted as HTML superscripts., Jyutping with asterisk: card fields show the first number, not the one after *., When part_of_speech is set, it appears in the PartOfSpeech field     and is rend, When part_of_speech is empty string, the PartOfSpeech field is empty,     and An, Card 1 (audio→image): front = audio + jyutping, back = image + jyutping     Card (+12 more)

### Community 20 - "Translate Step Tests"
Cohesion: 0.18
Nodes (17): _make_app(), _make_audio_download_client(), _make_brave_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_wiktionary_client(), Integration tests for the translate step page.  Story 2: I want to see Cantonese, GET /translate/{id} renders HTML page with Cantonese translation options.      S (+9 more)

### Community 21 - "Dockerfile Tests"
Cohesion: 0.11
Nodes (17): Smoke tests for Docker packaging.  Verifies the Dockerfile and docker-compose.ym, Dockerfile must exist at the project root., Dockerfile must use a Python 3.14 base image., Dockerfile must copy application source, templates, and data., Dockerfile must install Python dependencies via uv., Dockerfile must EXPOSE the application port (default 8000)., Dockerfile must set CMD or ENTRYPOINT to run the app., docker-compose.yml must exist at the project root. (+9 more)

### Community 22 - "Completion Step Tests"
Cohesion: 0.23
Nodes (15): _make_app(), _make_audio_download_client(), _make_brave_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_wiktionary_client(), Integration tests for the completion screen.  Story 15: I want to see a completi, GET /complete/{id} renders the completion screen with a success message.      St (+7 more)

### Community 23 - "SessionManager (Advance Word)"
Cohesion: 0.14
Nodes (7): Discard the current word and advance to the next., Build a Flashcard dataclass from card data dict and pre-resolved image bytes lis, Decode the original image URL from a Brave redirect proxy URL.          Brave re, Resolve an image reference to actual image bytes.          If *image_url* is byt, Assemble card data from the current selections.          Returns None if require, Move to the next word, resetting selections., Record the chosen audio, optionally save to CardStore, advance.          If *aud

### Community 24 - "Brave Image Search Tests"
Cohesion: 0.14
Nodes (13): Test that AudioService has one responsibility — downloading audio.  Story 25: Re, AudioService must not have a save_recording method.     Recording management is, AudioService must not have a get_recording method.     Recording management is t, download_audio must still work with injected client., download_audio returns None on network failure., close() must exist for client cleanup., Public API should be: download_audio, close — nothing more., test_audio_service_close_cleanup() (+5 more)

### Community 25 - "Session Isolation Tests"
Cohesion: 0.24
Nodes (12): _make_app(), _make_audio_download_client(), _make_brave_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_wiktionary_client(), Test that _sessions is scoped inside create_app, not module-level.  Story 24: Mo, Two create_app() calls must have independent session stores.     A session creat (+4 more)

### Community 26 - "Pipeline Orchestrator Tests"
Cohesion: 0.26
Nodes (11): _make_audio_download_client(), _make_brave_client(), _make_wiktionary_client(), Tracer-bullet test for Story 20: Extract PipelineOrchestrator from app.py.  One, httpx client serving the Wiktionary HTML fixture for 你., Orchestrator + SessionManager process two words in sequence.      After confirmi, httpx client returning mock Brave image search results., httpx client returning mock audio bytes for any URL. (+3 more)

### Community 27 - "CardStore Image Tests"
Cohesion: 0.17
Nodes (11): Tests for CardStoreProtocol image methods.  PRD specifies get_images(card_id) an, CardStoreProtocol defines get_images., CardStoreProtocol defines save_images., Images saved via save_images() round-trip through get_images()., A second save_images() replaces all previous images for the card., get_images returns empty list when no images stored for a card., test_get_images_empty_for_no_images(), test_protocol_has_get_images() (+3 more)

### Community 28 - "Audio Step POS Tests"
Cohesion: 0.22
Nodes (10): _env(), Tests for part-of-speech display on the audio step page.  PRD app.py + Templates, app.py passes empty part_of_speech when entry has no POS., audio_step.html shows POS in <em> when part_of_speech is passed., audio_step.html does not show POS when part_of_speech is empty., app.py audio_step endpoint passes part_of_speech to template context., test_app_passes_empty_pos_when_entry_has_none(), test_app_passes_pos_to_template() (+2 more)

### Community 30 - "Audio Persistence Tests"
Cohesion: 0.22
Nodes (9): _make_httpx_client(), download_audio returns raw audio bytes from a working OGG URL., download_audio returns None when the server returns an error., fetch_audio_url + download_audio work end-to-end for a character with Cantonese, download_audio returns None on network/request errors., test_download_audio_returns_bytes_from_url(), test_download_audio_returns_none_on_http_error(), test_download_audio_returns_none_on_request_error() (+1 more)

### Community 31 - "README Tests"
Cohesion: 0.29
Nodes (9): _make_card_download_client(), _make_wiktionary_audio_client(), Tests for audio persistence fix.  play_audio downloads audio bytes but must pers, WiktionaryAudio client serving the 你 fixture., httpx client for image/card downloads (used by SessionManager)., After play_audio downloads bytes, session.selected_audio must hold     those byt, When confirm_audio is called after play_audio, it must reuse the     persisted b, test_confirm_reuses_played_audio_without_redownload() (+1 more)

### Community 32 - "Main Entry Tests"
Cohesion: 0.2
Nodes (9): Tests for README.md completeness.  Ensures the README contains the deployment in, README must explain how to build and run the Docker image., README must include attribution for cantodict-archive data (CC4.0)., README must describe the basic workflow: paste words, select translation, image,, README must explain how to get and set BRAVE_SEARCH_API_KEY., test_readme_has_brave_api_key_instructions(), test_readme_has_cantodict_attribution(), test_readme_has_docker_build_instructions() (+1 more)

### Community 33 - "Completion POS Tests"
Cohesion: 0.2
Nodes (9): Tests for main.py — the application entry point.  Verifies that create_app_from_, create_app_from_env respects the APP_PORT env var, defaulting to 8000.     (We v, When BRAVE_SEARCH_API_KEY is set, create_app_from_env returns a working     Fast, When BRAVE_SEARCH_API_KEY is not set, create_app_from_env raises     a RuntimeEr, When CARD_STORE_DB and CANTODICT_DB env vars are set, create_app_from_env     us, test_create_app_from_env_custom_db_path(), test_create_app_from_env_default_port(), test_create_app_from_env_no_brave_key_raises() (+1 more)

### Community 34 - "Opus E2E Tests"
Cohesion: 0.33
Nodes (9): _make_store(), _mock_cantodict(), Tests for part-of-speech display on the completion page.  PRD Story 9: completio, Completion page shows part-of-speech for cards that have it., POS is rendered with <em> tags for visual distinction., When part_of_speech is empty, no POS hint appears in the summary., test_completion_no_pos_shown_when_empty(), test_completion_pos_shown_with_italics() (+1 more)

### Community 35 - "SessionManager HTTP Tests"
Cohesion: 0.38
Nodes (6): End-to-end: generate_apkg() with Opus audio produces a playable card.  Exercises, Read a media file from the .apkg by its basename.      genanki 0.13.1 stores med, Opus audio in a Flashcard is re-encoded to Vorbis during generate_apkg(),     pr, _read_media(), _sha1(), test_generate_apkg_with_opus_audio_produces_playable_card()

### Community 36 - "Wiktionary Audio (Parsing)"
Cohesion: 0.33
Nodes (6): _mock_http_client(), Build a fake httpx client for testing._http_client., When the HTTP client returns 403, image can't be resolved.     select_audio retu, When the HTTP client returns 200, image bytes are saved to Flashcard., test_select_audio_download_200_saves_real_bytes(), test_select_audio_download_403_no_save()

### Community 37 - "Wiktionary Audio (HTTP)"
Cohesion: 0.33
Nodes (4): fetch_audio_url(), Fetch Cantonese (Jyutping) audio URLs from Wiktionary.  Fetches the Wiktionary p, Clean up the httpx client if we own it., Fetch Wiktionary page for *character*, extract Cantonese OGG audio URL.      Bac

### Community 38 - "Deployment Config"
Cohesion: 0.33
Nodes (3): Fetch the Wiktionary page for *character* and return raw HTML.          Returns, Parse Wiktionary HTML and extract the Cantonese OGG audio URL.          Looks fo, Fetch and parse Wiktionary for *character*, return Cantonese OGG URL.          C

### Community 39 - "Session Skip Tests"
Cohesion: 0.4
Nodes (5): BRAVE_SEARCH_API_KEY, Docker Compose Setup, Docker Compose Configuration, card_data Docker Volume, Port 8000 Mapping

## Knowledge Gaps
- **436 isolated node(s):** `Orchestrate the card-creation pipeline.  Concentrates pipeline step logic (trans`, `Coordinate pipeline step logic across services and SessionManager.      Accepts`, `Look up Cantonese entries for *word* via CantoDict.`, `Search for images matching the session's selected characters.          Uses the`, `Fetch the Cantonese OGG audio URL for the session's character.` (+431 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CardStore` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 9`, `Community 11`, `Community 12`, `Community 13`, `Community 16`, `Community 17`, `Community 18`, `Community 20`, `Community 22`, `Community 25`, `Community 26`, `Community 27`, `Community 31`, `Community 34`, `Community 39`, `Community 57`?**
  _High betweenness centrality (0.246) - this node is a cross-community bridge._
- **Why does `SessionManager` connect `Community 8` to `Community 1`, `Community 3`, `Community 7`, `Community 9`, `Community 12`, `Community 18`, `Community 23`, `Community 26`, `Community 29`, `Community 31`, `Community 36`, `Community 40`, `Community 41`, `Community 42`, `Community 43`, `Community 44`, `Community 45`, `Community 46`, `Community 47`, `Community 48`, `Community 49`, `Community 50`, `Community 51`, `Community 52`, `Community 53`, `Community 54`, `Community 55`, `Community 56`?**
  _High betweenness centrality (0.242) - this node is a cross-community bridge._
- **Why does `CardGenerator` connect `Community 0` to `Community 1`, `Community 3`, `Community 35`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 14`, `Community 16`, `Community 17`, `Community 19`, `Community 20`, `Community 22`, `Community 25`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 86 inferred relationships involving `CardStore` (e.g. with `SessionStartRequest` and `AudioSelectRequest`) actually correct?**
  _`CardStore` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 75 inferred relationships involving `SessionManager` (e.g. with `PipelineOrchestrator` and `CardStoreProtocol`) actually correct?**
  _`SessionManager` has 75 INFERRED edges - model-reasoned connections that need verification._
- **Are the 63 inferred relationships involving `CardGenerator` (e.g. with `Flashcard` and `SessionStartRequest`) actually correct?**
  _`CardGenerator` has 63 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `CantoneseDictionary` (e.g. with `PipelineOrchestrator` and `SessionStartRequest`) actually correct?**
  _`CantoneseDictionary` has 57 INFERRED edges - model-reasoned connections that need verification._