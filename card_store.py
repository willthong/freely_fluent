"""SQLite persistence for completed flashcards."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Protocol


class CardStoreProtocol(ABC):
    """Abstract interface for flashcard persistence stores.

    Defines the contract any CardStore implementation must satisfy.
    Enables dependency injection and testing with alternate stores.
    """

    @abstractmethod
    def save_flashcard(self, flashcard: "Flashcard") -> "Flashcard": ...

    @abstractmethod
    def get_flashcard(self, flashcard_id: int) -> Optional["Flashcard"]: ...

    @abstractmethod
    def get_all(self) -> list["Flashcard"]: ...

    @abstractmethod
    def delete_flashcard(self, flashcard_id: int) -> None: ...


@dataclass
class Flashcard:
    """One completed flashcard persisted to SQLite."""

    id: Optional[int] = None
    english_word: str = ""
    chinese_characters: str = ""
    jyutping: str = ""
    image_data: bytes = b""
    audio_data: bytes = b""
    created_at: Optional[str] = None


class CardStore(CardStoreProtocol):
    """Manages flashcard persistence in a SQLite database."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english_word TEXT NOT NULL,
                chinese_characters TEXT NOT NULL,
                jyutping TEXT NOT NULL,
                image_data BLOB NOT NULL,
                audio_data BLOB NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """
        )
        self._conn.commit()

    def save_flashcard(self, flashcard: Flashcard) -> Flashcard:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT INTO cards (english_word, chinese_characters, jyutping, image_data, audio_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                flashcard.english_word,
                flashcard.chinese_characters,
                flashcard.jyutping,
                flashcard.image_data,
                flashcard.audio_data,
                now,
            ),
        )
        self._conn.commit()
        return Flashcard(
            id=cursor.lastrowid,
            english_word=flashcard.english_word,
            chinese_characters=flashcard.chinese_characters,
            jyutping=flashcard.jyutping,
            image_data=flashcard.image_data,
            audio_data=flashcard.audio_data,
            created_at=now,
        )

    def get_flashcard(self, flashcard_id: int) -> Optional[Flashcard]:
        row = self._conn.execute(
            "SELECT * FROM cards WHERE id = ?", (flashcard_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_flashcard(row)

    def get_all(self) -> list[Flashcard]:
        rows = self._conn.execute(
            "SELECT * FROM cards ORDER BY id ASC"
        ).fetchall()
        return [self._row_to_flashcard(row) for row in rows]

    def delete_flashcard(self, flashcard_id: int) -> None:
        self._conn.execute(
            "DELETE FROM cards WHERE id = ?", (flashcard_id,)
        )
        self._conn.commit()

    @staticmethod
    def _row_to_flashcard(row: sqlite3.Row) -> Flashcard:
        return Flashcard(
            id=row["id"],
            english_word=row["english_word"],
            chinese_characters=row["chinese_characters"],
            jyutping=row["jyutping"],
            image_data=row["image_data"],
            audio_data=row["audio_data"],
            created_at=row["created_at"],
        )
