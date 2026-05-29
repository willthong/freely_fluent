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


def extract_pos(definition: str) -> str:
    """Extract a part-of-speech abbreviation from the start of a definition.

    CantoDict definitions typically begin with a tag such as ``n.``, ``v.``,
    ``adj.``, etc.  The trailing punctuation is stripped so the returned value
    is a clean label (e.g. ``"n"`` not ``"n."``).

    Returns ``""`` when no recognised prefix is found.
    """
    m = _POS_PREFIX_RE.match(definition)
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

        Each returned dict includes a ``part_of_speech`` key extracted from
        the definition text.
        """
        pattern = f"%{english_word}%"
        rows = self._conn.execute(
            "SELECT chinese, jyutping, definition FROM Entries WHERE definition LIKE ?",
            (pattern,),
        ).fetchall()
        return [
            {
                "chinese": row["chinese"],
                "jyutping": row["jyutping"],
                "definition": row["definition"],
                "part_of_speech": extract_pos(row["definition"]),
            }
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()
