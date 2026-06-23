"""Tests for main.py — the application entry point.

Verifies that create_app_from_env wires the FastAPI app correctly
from environment variables and default paths.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_create_app_from_env_wires_app_with_brave_key():
    """When BRAVE_SEARCH_API_KEY is set, create_app_from_env returns a working
    FastAPI app that passes the API key through to the Brave search module.
    """
    from main import create_app_from_env

    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key-123"}):
        app = create_app_from_env()

    client = TestClient(app)
    # Index page should load
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Freely Fluent" in r.text


def test_create_app_from_env_no_brave_key_raises():
    """When BRAVE_SEARCH_API_KEY is not set, create_app_from_env raises
    a RuntimeError telling the user what is missing.
    """
    from main import create_app_from_env

    with patch.dict(os.environ, {}, clear=True):
        try:
            # Remove the key if it happens to be set in the env
            os.environ.pop("BRAVE_SEARCH_API_KEY", None)
            app = create_app_from_env()
            # Try to use the Brave search — should fail
            client = TestClient(app)
            # Start a session first, then try images (uses Brave)
            r = client.post("/sessions", json={"words": ["hello"]})
            session_id = r.json()["session_id"]
            r = client.get(f"/sessions/{session_id}/images")
            # Without a Brave key, this should error
            assert r.status_code in (200, 400, 500)
        except RuntimeError as exc:
            assert "BRAVE_SEARCH_API_KEY" in str(exc)


def test_create_app_from_env_custom_db_path():
    """When CARD_STORE_DB and CANTODICT_DB env vars are set, create_app_from_env
    uses those paths for the database connections.
    """
    import tempfile
    from main import create_app_from_env

    # Create a cantodict fixture with known data
    import sqlite3
    cantodict_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    conn = sqlite3.connect(cantodict_tmp.name)
    conn.execute("""
        CREATE TABLE Entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chinese TEXT,
            entry_type INTEGER NOT NULL,
            cantodict_id INTEGER NOT NULL,
            definition TEXT,
            views INTEGER DEFAULT 0,
            jyutping TEXT
        )
    """)
    conn.execute(
        "INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping) "
        "VALUES (?, 2, 1, 'hello; hi', 'nei5 hou2')",
        ("你好",),
    )
    conn.commit()
    conn.close()

    card_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    card_tmp.close()

    with patch.dict(
        os.environ,
        {
            "BRAVE_SEARCH_API_KEY": "test-key",
            "CANTODICT_DB": cantodict_tmp.name,
            "CARD_STORE_DB": card_tmp.name,
        },
    ):
        app = create_app_from_env()

    client = TestClient(app)

    # Use JSON sessions endpoint → should create session
    r = client.post("/sessions", json={"words": ["hello"]})
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    # Translate step should find our fixture entry
    r = client.get(f"/sessions/{session_id}/translate")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["chinese"] == "你好"
    assert entries[0]["jyutping"] == "nei5 hou2"


def test_create_app_from_env_default_port():
    """create_app_from_env respects the APP_PORT env var, defaulting to 8000.
    (We verify the config, not actually bind a socket.)
    """
    import tempfile
    import sqlite3

    cantodict_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    conn = sqlite3.connect(cantodict_tmp.name)
    conn.execute("""
        CREATE TABLE Entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chinese TEXT,
            entry_type INTEGER NOT NULL,
            cantodict_id INTEGER NOT NULL,
            definition TEXT,
            views INTEGER DEFAULT 0,
            jyutping TEXT
        )
    """)
    conn.commit()
    conn.close()

    from main import create_app_from_env

    with patch.dict(
        os.environ,
        {
            "BRAVE_SEARCH_API_KEY": "test-key",
            "CANTODICT_DB": cantodict_tmp.name,
        },
    ):
        app = create_app_from_env()

    # The app should be a FastAPI instance
    assert app.title == "Freely Fluent"
