# Freely Fluent

A FastAPI/Python app to generate flashcards intended to help a language learner through
the [Fluent Forever method](https://www.amazon.com/Fluent-Forever-Learn-Read-Write/dp/0399577170) of learning.

## How It Works

For v1, this app only supports **Cantonese**. The learner enters a linebreak-separated list of
English words into a text box. Each represents a word they wish to learn.

The pipeline is:

1. **Translate** — Freely Fluent searches for Cantonese translations using [CantoDict](https://cantonese.sheik.co.uk) (derived from the [cantodict-archive](https://github.com/josephcooper/cantodict-archive), CC4.0). It returns each character entry with Jyutping romanisation and meaning.

2. **Select** — The learner picks the entry that best matches the intended word.

3. **Image** — A Brave image search is performed for the Chinese character, and the learner selects a memorable image (with pagination to load more).

4. **Audio** — The character is looked up on Wiktionary for audio. If no matching recording is found, the learner records a pronunciation themselves.

5. **Card** — A reversible flashcard is generated via genanki, with the image on one side and the audio on the other. Both sides show the Jyutping. Opus audio (e.g. from Wiktionary) is automatically re-encoded to Vorbis so that Anki's desktop player can play it.

6. **Export** — Throughout the app the learner can export cards generated so far as an `.apkg` file. Cards are persisted in a SQLite database.

## Setup

### Prerequisites

- **Python 3.14**
- **uv** package manager (`pip install uv`)
- **Brave Search API key** — [Sign up at Brave Search API](https://brave.com/search/api/) and get a free-tier key

### Brave Search API Key

Set the `BRAVE_SEARCH_API_KEY` environment variable before running:

```bash
export BRAVE_SEARCH_API_KEY="your-key-here"
```

Without this key the app will not be able to perform image searches and will raise an error on startup.

### Local Development

```bash
# Set your API key
export BRAVE_SEARCH_API_KEY="your-key-here"

# Build and run with Docker Compose
docker compose up --build
```

This builds the container and starts the app on port `8000`. The card database is persisted in a Docker volume.

### Docker Build Only

```bash
docker build -t freely-fluent .
docker run -p 8000:8000 -e BRAVE_SEARCH_API_KEY="your-key-here" freely-fluent
```

## Data

The CantoDict database in `data/cantodict.sqlite` is derived from the [cantodict-archive](https://github.com/josephcooper/cantodict-archive), released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## License

Freely Fluent is released under the MIT License. See `LICENSE` for details.
