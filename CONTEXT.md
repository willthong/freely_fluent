# Freely Fluent

A single-user app that automates the Fluent Forever flashcard creation pipeline for Cantonese. The user pastes a list of English words and walks through each one — picking a translation, an image, and audio — until a reversible Anki flashcard is produced.

## Quick start for AI assistants

A previous run of the **graphify** skill has already produced a knowledge graph of this codebase. Load `graphify-out/GRAPH_REPORT.md` into your context for a ready-made architectural overview (302 nodes, 545 edges, 20 communities).

## Python tooling

**Always use `uv`** when running any Python commands — `uv run pytest`, `uv run python`, `uv pip install`, etc. Do not invoke `pytest`, `python`, or `pip` directly.

## Key takeaways from the graph report

**God nodes** (core abstractions by connectivity):
1. `CantoneseDictionary` — 37 edges (CantoDict SQLite lookup)
2. `CardStore` — 37 edges (flashcard persistence)
3. `CardGenerator` — 36 edges (genanki reversed cards)
4. `SessionManager` — 32 edges (pipeline state machine)
5. `create_app()` — 25 edges (FastAPI dependency injection)
6. `AudioService` — 17 edges
7. `BraveImageSearch` — 15 edges

**20 communities** cover: FastAPI routes, session management, CantoDict lookup, domain concepts, card persistence, Wiktionary audio extraction, card generation, and tests.

**Cross-community bridges** (high betweenness): `SessionManager`, `CardStore` — these connect multiple subsystems.

If the codebase has changed significantly since the report date (`2026-05-11`), consider re-running graphify. Otherwise, the report is your fastest path to architectural understanding.

## Language

**Session**:
A batch of English words the user wants to learn, processed sequentially.

**English Word**:
One line of user input — the starting point for card creation.

**Entry**:
A result from the bundled cantodict-archive SQLite database for an English word — a Cantonese form (one or more characters) with a Jyutping reading and an English definition. The user selects exactly one Entry per English word, or skips.
_Avoid_: Translation, character, lexeme

**Chosen Audio**:
The audio asset for a Flashcard — either a Wiktionary native recording or the user's own recording. Exactly one per card. The user is a native Cantonese speaker and may record their own pronunciation when the Wiktionary option is unsatisfactory.
_Avoid_: Pronunciation, recording, audio clip

**Flashcard**:
A reversible Anki card for one English word → Entry pairing. Two directions: audio→images and images→audio. One or more images may be attached. Jyutping appears on both the front and back of every direction. English words and Chinese characters are excluded from both sides.
_Avoid_: Card, flashcard pair, note

**Pipeline Step**:
One stage of card creation for the current English word — Translate, Image, or Audio. The user progresses sequentially through steps. They can skip from any step to discard the current word and move to the next. They can also go back: going back to step N resets step N and all subsequent steps, preserving steps before N.

**Part of Speech (POS)**:
A grammatical label (e.g. "n", "v", "adj") that appears on a Flashcard as supplementary context. The user manually sets it per-word using a dropdown on the Translate step. CantoDict may suggest a value, but the suggestion is never auto-committed — the card only gets a POS when the user explicitly picks one. If the user never touches the dropdown, the card has no POS.
_Avoid_: Tag, label, grammatical category

## Relationships

- A **Session** contains one or more **English Words**
- An **English Word** produces zero or more **Entries** (from the bundled cantodict-archive SQLite); the user picks one or skips
- One selected **Entry** (with an explicitly-set **Part of Speech**) + one or more images + one **Chosen Audio** → one **Flashcard**
- A **Flashcard** is saved to SQLite and included in `.apkg` export
- Skipping from any **Pipeline Step** discards the current word and advances to the next **English Word**
- Going back from step N to step M (M < N) resets steps M through N. The **English Word** is always preserved. Selecting a different **Entry** on going back to Translate discards images and audio tied to the old characters.

## CI / CD pipeline

Merging to `dev` or `main` triggers `.github/workflows/build.yaml`, which:

1. **Tests** — `uv run pytest` (Python 3.14)
2. **Builds & pushes** a container image to `ghcr.io` (tagged `:main`, `:latest`, and a semver on `main`; `:dev` and `:${{ github.sha }}` on `dev`)
3. **Deploys** via SSH (`appleboy/ssh-action@v1.2.2`) — `docker compose pull && docker compose up -d`
   - **`dev`** → target directory `/sharedfolders/AppData/fluent_forever_dev`
   - **`main`** → target directory `/sharedfolders/AppData/fluent_forever`

### No extra secrets needed

The deploy job runs directly on the GitHub runner (self-hosted or with the shared folders mounted), so no SSH configuration is required. The runner just needs Docker and access to the target directories.

### Docker Compose

`docker-compose.yml` references the pre-built `ghcr.io` image via `image: ghcr.io/earendil-works/freely-fluent:${TAG:-latest}` instead of a local build. The compose files at the deploy paths should be kept in sync with the repo.

## Example dialogue

> **Dev:** "When the user skips at the Image step, what happens to the Entry they already picked?"
> **Domain expert:** "Everything is discarded — the Entry, any image loaded, anything. We move straight to the next English Word in the Session."

> **Dev:** "Do characters ever appear on the card itself?"
> **Domain expert:** "No. They're used internally to look up images and audio, but the card face is clean — image(s) only on front, audio only on back."

> **Dev:** "If CantoDict suggests 'n' for a word and the user never touches the POS dropdown, does the card get 'n'?"
> **Domain expert:** "No. The suggestion is informational only. No explicit pick = no POS on the card."

> **Dev:** "Can the user type a custom POS like 'classifier'?"
> **Domain expert:** "Yes — the dropdown has an 'Other…' option that reveals a free-text input. Whatever they type becomes the POS on the card."

## Flagged ambiguities

- "characters" were initially treated as something the user might need to learn. Resolved: characters are an internal lookup key only, never shown on the card face.
- Audio format mixing (WebM vs OGG/MP3) — user doesn't care so long as Anki plays it. Opus OGG audio is re-encoded to Vorbis in `CardGenerator._write_media()` because Anki's Qt 5 can't play Opus.
- Image quality — Brave Search thumbnails are sufficient for flashcard recognition. No follow-to-original needed.
- Confirm step removed — not needed. The Audio step is the final step before saving.
- POS toggle removed — the global "Show part-of-speech hints" checkbox was replaced with a per-word dropdown on the Translate step. Default is no POS; each word gets POS only if the user explicitly sets it.
- Image selection is multi-select, accumulating across standard Brave search and custom search in a single pass. No separate "confirm images" step — the user moves to Audio when ready.
- Back navigation: going back to step N resets step N and all subsequent steps. Steps before N are preserved. Implemented in SessionManager.go_back().
- Image downscaling at card generation time: max 800px on longest dimension, configurable as max_image_width (default 800). Only downscale, never upscale.
- Image preview on hover/long-press shows the thumbnail at its correct aspect ratio (no crop). No need to fetch the original image — old "no follow-to-original" decision stands.

## Wiktionary Audio Research Notes

> Findings from HTML analysis of Wiktionary pages (e.g. `家庭`):

**Lookup key**: Chinese characters from the Entry (e.g. `家`, `你好`, `家庭`)

**Cantonese audio file naming** (Wikimedia Commons):
- Pattern: `LL-Q9186-{username}-{characters}.wav`
- Q9186 = Cantonese language code on Wikimedia
- The `LL-Q9186-` prefix is the reliable selector for Cantonese recordings

**Audio HTML structure**:
```html
<audio data-mwtitle="LL-Q9186-Luilui6666-家庭.wav">
  <source src="//upload.wikimedia.org/.../LL-Q9186-Luilui6666-家庭.wav.ogg" type="audio/ogg" />
  <source src="//upload.wikimedia.org/.../LL-Q9186-Luilui6666-家庭.wav.mp3" type="audio/mpeg" />
</audio>
```

**Mandarin audio** (distinct, should be skipped):
- Pattern: `zh-jiātíng.ogg` (uses Pinyin in filename, no Cantonese marker)

**Coverage**: Not all characters have Cantonese audio. Must handle gracefully (return `None`).

**Implementation approach** (planned, pending TDD approval):
- Separate concerns: `fetch_html()` handles HTTP, `parse_html()` accepts raw strings
- Inject HTTP client into constructor, no internal instantiation
- Test parsing with static HTML fixtures, no network in tests
