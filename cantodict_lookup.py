"""Query the bundled cantodict-archive SQLite database by English word."""

from __future__ import annotations

import sqlite3
from typing import Any


class CantoneseDictionary:
    """Look up Cantonese entries by English word in a cantodict SQLite database."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def lookup(self, english_word: str) -> list[dict[str, Any]]:
        """Return entries whose definition contains *english_word*."""
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
            }
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()
