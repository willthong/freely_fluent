"""Query the bundled cantodict-archive SQLite database by English word.

CantoDict definitions typically start with a part-of-speech abbreviation
(e.g. "n.", "v.", "adj.").  These are extracted and made available on every
lookup result so the pipeline can attach POS hints to flashcards.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

# POS abbreviations found at the start of CantoDict definitions.
# Matched longest-first so "adj." wins over a hypothetical "a." prefix.
_POS_PREFIX_RE = re.compile(r"^(adj|adv|conj|interj|n|num|prep|pron|v|aux\.v)\.", re.IGNORECASE)

# Some definitions use bracket format, e.g. "[1] [n] orange" or
# "[ 粵 ] [1] [v] eat; have a meal".  Match [pos] anywhere in the string.
_POS_BRACKET_RE = re.compile(r"\[(adj|adv|conj|interj|n|num|prep|pron|v|aux\.v)\]", re.IGNORECASE)


def extract_pos(definition: str) -> str:
    """Extract a part-of-speech abbreviation from a CantoDict definition.

    Supports two formats:
    1. Prefix format: ``n. hello; hi`` — tag at the start followed by a dot.
    2. Bracket format: ``[1] [n] orange`` — ``[pos]`` anywhere in the string.

    The trailing punctuation is stripped so the returned value is a clean
    label (e.g. ``"n"`` not ``"n."``).

    Returns ``""`` when no recognised abbreviation is found.
    """
    # Try prefix format first: "n. ...", "v. ..." at the start
    m = _POS_PREFIX_RE.match(definition)
    if m:
        return m.group(1).lower()
    # Fall back to bracket format: "[n]", "[v]" anywhere
    m = _POS_BRACKET_RE.search(definition)
    if m:
        return m.group(1).lower()
    return ""


class CantoneseDictionary:
    """Look up Cantonese entries by English word in a cantodict SQLite database."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def lookup(self, english_word: str) -> list[dict[str, Any]]:
        """Return entries whose definition contains *english_word*.

        Results are sorted with exact/standalone matches first:
        entries where *english_word* appears as a standalone token
        (preceded by start-of-string, space, punctuation, or bracket)
        rank highest, then all remaining LIKE substring matches.

        Each returned dict includes a ``part_of_speech`` key extracted from
        the definition text.
        """
        pattern = f"%{english_word}%"
        rows = self._conn.execute(
            "SELECT chinese, jyutping, definition FROM Entries WHERE definition LIKE ?",
            (pattern,),
        ).fetchall()
        entries = [
            {
                "chinese": row["chinese"],
                "jyutping": row["jyutping"],
                "definition": row["definition"],
                "part_of_speech": extract_pos(row["definition"]),
            }
            for row in rows
        ]
        # Sort: standalone-token matches first, substring-only matches last
        # The word must appear as a standalone token (preceded by start-of-string,
        # space, punctuation, or bracket; followed by same or end-of-string).
        escaped = re.escape(english_word)
        boundary_re = re.compile(
            r'(?:^|[\s\[\]\(\)\{\}.,;:!?"\'/\\-])'
            + escaped
            + r'(?:$|[\s\[\]\(\)\{\}.,;:!?"\'/\\-])',
            re.IGNORECASE,
        )
        entries.sort(key=lambda e: 0 if boundary_re.search(e["definition"]) else 1)
        return entries

    def close(self) -> None:
        self._conn.close()
