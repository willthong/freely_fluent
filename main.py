"""Application entry point.

Wires up the FastAPI app from environment variables and default paths.
Used as the uvicorn target in Docker and for local development.
"""

from __future__ import annotations

import os

from app import create_app
from brave_image_search import BraveImageSearch
from audio_service import AudioService
from card_generator import CardGenerator
from card_store import CardStore
from cantodict_lookup import CantoneseDictionary


# Default paths — overridden by env vars
_DEFAULT_CANTODICT_DB = "data/cantodict.sqlite"
_DEFAULT_CARD_STORE_DB = "data/cards.db"
_DEFAULT_PORT = 8000


def create_app_from_env() -> object:
    """Create a FastAPI app wired from environment variables.

    Reads:
      BRAVE_SEARCH_API_KEY (required) — key for Brave Search API
      CANTODICT_DB (optional) — path to cantodict.sqlite (default: data/cantodict.sqlite)
      CARD_STORE_DB (optional) — path to cards.db (default: data/cards.db)

    Raises RuntimeError if BRAVE_SEARCH_API_KEY is not set.
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise RuntimeError(
            "BRAVE_SEARCH_API_KEY environment variable is required. "
            "Get one at https://brave.com/search/api/ and set it before running."
        )

    cantodict_path = os.environ.get("CANTODICT_DB", _DEFAULT_CANTODICT_DB)
    card_store_path = os.environ.get("CARD_STORE_DB", _DEFAULT_CARD_STORE_DB)

    cantodict = CantoneseDictionary(cantodict_path)
    card_store = CardStore(card_store_path)
    card_generator = CardGenerator()

    return create_app(
        cantodict=cantodict,
        card_store=card_store,
        card_generator=card_generator,
        api_key=api_key,
    )


def main() -> None:
    """Start the application server using uvicorn."""
    import uvicorn

    app = create_app_from_env()
    port = int(os.environ.get("APP_PORT", _DEFAULT_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
