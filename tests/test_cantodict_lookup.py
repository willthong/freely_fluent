"""Tests for cantodict_lookup module."""

from __future__ import annotations

import sqlite3
import tempfile

from cantodict_lookup import CantoneseDictionary


def _make_fixture_db() -> str:
    """Create a small in-memory fixture DB mimicking cantodict.sqlite schema."""
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
    conn.execute("""
        INSERT INTO Entries (chinese, entry_type, cantodict_id, definition, jyutping)
        VALUES
            ('你好', 2, 100, 'hello; hi; how are you', 'nei5 hou2'),
            ('喂', 1, 101, 'hello (when answering the telephone)', 'wai3'),
            ('家', 1, 102, 'home; family; household', 'gaa1'),
            ('回家', 2, 103, 'go home; return home', 'wui4 gaa1'),
            ('水', 1, 104, 'water', 'seoi2'),
            ('多喝水', 2, 105, 'drink more water', 'do1 seoi2 seoi2')
    """)
    conn.commit()
    conn.close()
    return tmp.name


def test_lookup_returns_entries_for_matching_word():
    """Lookup returns entries when the English word matches a definition."""
    db_path = _make_fixture_db()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("hello")

    assert len(entries) == 2
    assert entries[0]["chinese"] == "你好"
    assert entries[0]["jyutping"] == "nei5 hou2"
    assert entries[0]["definition"] == "hello; hi; how are you"
    assert entries[1]["chinese"] == "喂"
    assert entries[1]["jyutping"] == "wai3"


def test_lookup_returns_empty_list_for_no_match():
    """Lookup returns an empty list when the word has no matching entries."""
    db_path = _make_fixture_db()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("xyz_nonexistent")

    assert entries == []


def test_lookup_matches_partial_word_in_definition():
    """Lookup matches words that appear as part of a longer definition."""
    db_path = _make_fixture_db()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("home")

    assert len(entries) == 2
    assert entries[0]["chinese"] == "家"
    assert entries[0]["jyutping"] == "gaa1"
    assert entries[1]["chinese"] == "回家"
    assert entries[1]["jyutping"] == "wui4 gaa1"


def test_lookup_matches_subword():
    """Lookup matches 'water' which also appears inside 'drink more water'."""
    db_path = _make_fixture_db()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("water")

    assert len(entries) == 2
    assert entries[0]["chinese"] == "水"
    assert entries[1]["chinese"] == "多喝水"
