# Graph Report - .  (2026-05-11)

## Corpus Check
- 28 files · ~89,307 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 302 nodes · 545 edges · 20 communities (11 shown, 9 thin omitted)
- Extraction: 68% EXTRACTED · 32% INFERRED · 0% AMBIGUOUS · INFERRED: 177 edges (avg confidence: 0.75)
- Token cost: 89,307 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_FastAPI App Routes|FastAPI App Routes]]
- [[_COMMUNITY_Session Manager Rationale|Session Manager Rationale]]
- [[_COMMUNITY_Card Store + App Tests|Card Store + App Tests]]
- [[_COMMUNITY_CantoDict Lookup|CantoDict Lookup]]
- [[_COMMUNITY_Domain Concepts & PRD|Domain Concepts & PRD]]
- [[_COMMUNITY_App Factory + Load More|App Factory + Load More]]
- [[_COMMUNITY_Card Persistence|Card Persistence]]
- [[_COMMUNITY_Wiktionary Audio Extraction|Wiktionary Audio Extraction]]
- [[_COMMUNITY_Card Store Tests|Card Store Tests]]
- [[_COMMUNITY_Session Properties|Session Properties]]
- [[_COMMUNITY_Card Generator|Card Generator]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]
- [[_COMMUNITY_Session Manager Detail|Session Manager Detail]]

## God Nodes (most connected - your core abstractions)
1. `CantoneseDictionary` - 37 edges
2. `CardStore` - 37 edges
3. `CardGenerator` - 36 edges
4. `SessionManager` - 32 edges
5. `create_app()` - 25 edges
6. `AudioService` - 17 edges
7. `_make_cantodict_fixture()` - 16 edges
8. `_make_card_store_fixture()` - 16 edges
9. `BraveImageSearch` - 15 edges
10. `_make_brave_client()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `README Card Flow Description` --semantically_similar_to--> `Card Creation Pipeline`  [INFERRED] [semantically similar]
  README.md → PRD.md
- `README Card Flow Description` --semantically_similar_to--> `Fluent Forever Method`  [INFERRED] [semantically similar]
  README.md → PRD.md
- `Jyutping Romanisation` --semantically_similar_to--> `LL-Q9186 Cantonese Audio Marker`  [INFERRED] [semantically similar]
  PRD.md → CONTEXT.md
- `SessionStartRequest` --uses--> `SessionManager`  [INFERRED]
  app.py → session_manager.py
- `EntrySelectRequest` --uses--> `SessionManager`  [INFERRED]
  app.py → session_manager.py

## Hyperedges (group relationships)
- **Card Creation Pipeline Flow** — PRD_Entry, PRD_ChosenAudio, PRD_Flashcard, PRD_Session, PRD_Pipeline [EXTRACTED 1.00]
- **Audio Source Options** — CONTEXT_LLQ9186, PRD_ChosenAudio, CONTEXT_WikiAudioResearch [EXTRACTED 0.90]
- **Domain Model Definitions** — PRD_DomainTerms, PRD_Entry, PRD_Flashcard, PRD_Session, PRD_ChosenAudio [EXTRACTED 1.00]

## Communities (20 total, 9 thin omitted)

### Community 0 - "FastAPI App Routes"
Cohesion: 0.05
Nodes (44): BaseModel, AudioSelectRequest, EntrySelectRequest, ImageAddRequest, FastAPI app wiring modules together.  REST-style routes for the card-creation pi, RecordingRequest, SessionStartRequest, AudioService (+36 more)

### Community 1 - "Session Manager Rationale"
Cohesion: 0.05
Nodes (41): Assemble card data from the current selections.          Returns None if require, Advance the image search offset by *batch_size*. Returns new offset., Move to the next word, resetting selections., Record the chosen Entry and advance to the image step., Add an image to the selection. Advances to audio step if not yet there., Record the chosen audio, save card data, and advance to next word.          If *, Track session state through the pipeline steps.      Manages the current word in, Store a browser recording for the current word. (+33 more)

### Community 2 - "Card Store + App Tests"
Cohesion: 0.1
Nodes (41): CardStore, Manages flashcard persistence in a SQLite database., _make_audio_download_client(), _make_brave_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_wiktionary_client(), Integration tests for the FastAPI app.  Uses TestClient to exercise the public H (+33 more)

### Community 3 - "CantoDict Lookup"
Cohesion: 0.09
Nodes (26): CantoneseDictionary, Query the bundled cantodict-archive SQLite database by English word., Look up Cantonese entries by English word in a cantodict SQLite database., Return entries whose definition contains *english_word*., _make_wiktionary_client_char(), Tests for Story 7: Wiktionary Cantonese pronunciation UI (audio step).  Follows, POST /audio/{id} with 'wiktionary' source confirms the audio,     saves the flas, POST /sessions/{id}/skip from audio step discards everything     and advances to (+18 more)

### Community 4 - "Domain Concepts & PRD"
Cohesion: 0.1
Nodes (26): LL-Q9186 Cantonese Audio Marker, Wiktionary Audio Research, Anki Flashcards, Basic Reversed Card Model, Chosen Audio, Docker Deployment, Domain Terminology, Entry (CantoDict result) (+18 more)

### Community 5 - "App Factory + Load More"
Cohesion: 0.17
Nodes (22): create_app(), Create a FastAPI app with injected dependencies., _make_audio_download_client(), _make_cantodict_fixture(), _make_card_store_fixture(), _make_multi_batch_brave_client(), _make_wiktionary_client(), Integration tests for the 'load more' images feature.  Story 6: As a language le (+14 more)

### Community 6 - "Card Persistence"
Cohesion: 0.15
Nodes (12): Flashcard, SQLite persistence for completed flashcards., One completed flashcard persisted to SQLite., _row_to_flashcard(), N flashcards produce N × 2 Anki cards., Card 1 (audio→image): front = audio + jyutping, back = image + jyutping     Card, One flashcard produces 2 Anki cards (reversed pair)., The exported .apkg file exists, is non-zero, and is a valid zip. (+4 more)

### Community 7 - "Wiktionary Audio Extraction"
Cohesion: 0.21
Nodes (11): fetch_audio_url(), Fetch Cantonese (Jyutping) audio URLs from Wiktionary.  Fetches the Wiktionary p, Fetch Wiktionary page for *character*, extract Cantonese OGG audio URL.      Ret, _make_client(), fetch_audio_url returns the Cantonese OGG URL for a character with audio., fetch_audio_url returns None for a character with no Cantonese audio., fetch_audio_url returns None when the page fails to load., Create an httpx client that serves a recorded Wiktionary HTML fixture. (+3 more)

### Community 8 - "Card Store Tests"
Cohesion: 0.25
Nodes (10): _make_store(), A saved flashcard can be retrieved by its id., get_all returns all saved flashcards in insertion order., Requesting a flashcard that doesn't exist returns None., A deleted flashcard can no longer be retrieved., Create an isolated CardStore backed by a temp SQLite file., test_delete_removes_flashcard(), test_get_all_returns_cards_in_insertion_order() (+2 more)

### Community 10 - "Card Generator"
Cohesion: 0.47
Nodes (4): _guess_audio_ext(), _guess_image_ext(), Build genanki reversed cards from flashcards., _write_media()

## Knowledge Gaps
- **131 isolated node(s):** `Search for images via the Brave Search API.  Calls Brave's image search endpoint`, `Search Brave for images matching a query.`, `Search for images matching *query*.          Returns a list of result dicts with`, `Clean up the httpx client if we own it.`, `Server-side session tracking for the card-creation pipeline.` (+126 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionManager` connect `Session Manager Rationale` to `FastAPI App Routes`, `Session Properties`?**
  _High betweenness centrality (0.309) - this node is a cross-community bridge._
- **Why does `CardStore` connect `Card Store + App Tests` to `FastAPI App Routes`, `CantoDict Lookup`, `App Factory + Load More`, `Card Persistence`, `Card Store Tests`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `CantoneseDictionary` (e.g. with `SessionStartRequest` and `EntrySelectRequest`) actually correct?**
  _`CantoneseDictionary` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `CardStore` (e.g. with `SessionStartRequest` and `EntrySelectRequest`) actually correct?**
  _`CardStore` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `CardGenerator` (e.g. with `Flashcard` and `SessionStartRequest`) actually correct?**
  _`CardGenerator` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `SessionManager` (e.g. with `SessionStartRequest` and `EntrySelectRequest`) actually correct?**
  _`SessionManager` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `create_app()` (e.g. with `test_load_more_returns_second_batch_of_images()` and `test_load_more_returns_empty_when_no_more_results()`) actually correct?**
  _`create_app()` has 23 INFERRED edges - model-reasoned connections that need verification._