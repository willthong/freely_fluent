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


def _make_fixture_db_pos() -> str:
    """Create a fixture DB with POS-prefixed definitions."""
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
            ('你好', 2, 100, 'n. hello; hi; how are you', 'nei5 hou2'),
            ('喂', 1, 101, 'v. hello (when answering the telephone)', 'wai3'),
            ('家', 1, 102, 'adj. domestic; family-related', 'gaa1')
    """)
    conn.commit()
    conn.close()
    return tmp.name


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


def test_extract_pos_parses_noun_prefix():
    """extract_pos strips the 'n.' prefix and returns 'n'."""
    from cantodict_lookup import extract_pos

    assert extract_pos("n. hello; hi; how are you") == "n"


def test_extract_pos_parses_verb_prefix():
    """extract_pos strips the 'v.' prefix and returns 'v'."""
    from cantodict_lookup import extract_pos

    assert extract_pos("v. to go; to move") == "v"


def test_extract_pos_parses_adjective_prefix():
    """extract_pos strips the 'adj.' prefix and returns 'adj'."""
    from cantodict_lookup import extract_pos

    assert extract_pos("adj. big; large") == "adj"


def test_extract_pos_returns_empty_when_no_prefix():
    """extract_pos returns '' when the definition has no POS prefix."""
    from cantodict_lookup import extract_pos

    assert extract_pos("hello; hi; how are you") == ""


def test_extract_pos_returns_empty_for_empty_definition():
    """extract_pos returns '' for an empty definition string."""
    from cantodict_lookup import extract_pos

    assert extract_pos("") == ""


def test_lookup_includes_part_of_speech_in_entries():
    """lookup() returns entries with a 'part_of_speech' key."""
    db_path = _make_fixture_db()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("hello")

    for entry in entries:
        assert "part_of_speech" in entry


def test_lookup_propagates_extracted_pos():
    """lookup() extracts POS into _cantodict_pos; part_of_speech starts blank."""
    db_path = _make_fixture_db_pos()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("hello")

    # Entry with "n." prefix
    noun_entry = next(e for e in entries if e["chinese"] == "你好")
    assert noun_entry["_cantodict_pos"] == "n"
    assert noun_entry["part_of_speech"] == ""

    # Entry with "v." prefix
    verb_entry = next(e for e in entries if e["chinese"] == "喂")
    assert verb_entry["_cantodict_pos"] == "v"
    assert verb_entry["part_of_speech"] == ""


def test_lookup_matches_subword():
    """Lookup matches 'water' which also appears inside 'drink more water'."""
    db_path = _make_fixture_db()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("water")

    assert len(entries) == 2
    assert entries[0]["chinese"] == "水"
    assert entries[1]["chinese"] == "多喝水"


def _make_fixture_db_exact_vs_substring() -> str:
    """Create a fixture DB with entries for exact-match-first sorting.

    - "actor" appears as an exact standalone word in one entry
    - "actor" appears inside "tractor" in another entry
    """
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
            ('演員', 2, 200, 'actor; performer', 'jin4 jyun4'),
            ('拖拉機', 2, 201, 'tractor (agricultural vehicle)', 'to1 laa1 gei1'),
            ('歌星', 2, 202, 'singer; vocalist; also actor', 'go1 sing1')
    """)
    conn.commit()
    conn.close()
    return tmp.name


def test_lookup_exact_matches_sorted_before_substring():
    """Exact-match entries (word as standalone token in definition)
    sort before substring-only entries.

    Searching 'actor' should return:
      1. '演員' (definition starts with 'actor')
      2. '歌星' (definition contains 'actor' as a standalone token: ', also actor')
      3. '拖拉機' (definition contains 'tractor' — only a substring match)
    """
    db_path = _make_fixture_db_exact_vs_substring()
    dic = CantoneseDictionary(db_path)

    entries = dic.lookup("actor")

    assert len(entries) == 3
    # Exact matches (standalone tokens) come first
    assert entries[0]["chinese"] == "演員"
    assert entries[1]["chinese"] == "歌星"
    # Substring-only match comes last
    assert entries[2]["chinese"] == "拖拉機"


def test_extract_pos_parses_bracket_format():
    """extract_pos also handles POS in bracket format [n], [v], [adj] etc.
    used by the real CantoDict database (e.g. "[1] [n] orange")."""
    from cantodict_lookup import extract_pos

    assert extract_pos("[1] [n] orange (tree and fruit)") == "n"
    assert extract_pos("[1] [v] eat; have a meal") == "v"
    assert extract_pos("[1] [adj] happy; joyful") == "adj"
    assert extract_pos("[1] [adv] quickly; fast") == "adv"
    assert extract_pos("[ 粵 ] sik6 | [ 國 ] shi2 [1] [v] eat; have a meal") == "v"
    assert extract_pos("[1] [conj] and; also") == "conj"
    assert extract_pos("[1] [pron] I; me") == "pron"
    assert extract_pos("[1] [prep] in; at") == "prep"
