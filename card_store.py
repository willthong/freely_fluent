"""SQLite persistence for completed flashcards."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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

    @abstractmethod
    def get_by_session(self, session_id: str) -> list["Flashcard"]: ...

    @abstractmethod
    def save_images(self, card_id: int, images: list[bytes]) -> None: ...

    @abstractmethod
    def get_images(self, card_id: int) -> list[bytes]: ...

    @abstractmethod
    def delete_broken_cards(self) -> int: ...


@dataclass
class Flashcard:
    """One completed flashcard persisted to SQLite."""

    id: Optional[int] = None
    english_word: str = ""
    chinese_characters: str = ""
    jyutping: str = ""
    part_of_speech: str = ""
    image_data: list[bytes] = field(default_factory=list)
    audio_data: bytes = b""
    created_at: Optional[str] = None
    session_id: str = ""


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
                part_of_speech TEXT NOT NULL DEFAULT '',
                image_data BLOB NOT NULL,
                audio_data BLOB NOT NULL,
                created_at TIMESTAMP NOT NULL,
                session_id TEXT NOT NULL DEFAULT ''
            )
            """
        )
        # Migrate old databases that don\'t have session_id yet.
        # Silently ignore "duplicate column" for fresh databases.
        try:
            self._conn.execute(
                "ALTER TABLE cards ADD COLUMN session_id TEXT NOT NULL DEFAULT ''"
            )
        except sqlite3.OperationalError:
            pass
        # Migrate old databases that don\'t have part_of_speech yet.
        try:
            self._conn.execute(
                "ALTER TABLE cards ADD COLUMN part_of_speech TEXT NOT NULL DEFAULT ''"
            )
        except sqlite3.OperationalError:
            pass
        # Add uniqueness index.  For old databases that may already have
        # duplicate rows, clean up first (keep the most recent copy).
        try:
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_unique "
                "ON cards(english_word, chinese_characters, jyutping)"
            )
        except sqlite3.IntegrityError:
            # Old duplicates exist - delete all but the newest per key
            self._conn.execute(
                "DELETE FROM cards WHERE id NOT IN ("
                "  SELECT MAX(id) FROM cards "
                "  GROUP BY english_word, chinese_characters, jyutping"
                ")"
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_unique "
                "ON cards(english_word, chinese_characters, jyutping)"
            )
        # card_images table for multiple images per card.
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS card_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id),
                image_data BLOB NOT NULL,
                sort_order INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def save_flashcard(self, flashcard: Flashcard) -> Flashcard:
        now = datetime.now(timezone.utc).isoformat()
        # UPSERT: if a card with the same uniqueness key exists, update it
        # (preserving the original id).  Otherwise insert a new row.
        self._conn.execute(
            """
            INSERT INTO cards
                (english_word, chinese_characters, jyutping,
                 part_of_speech, image_data, audio_data, created_at, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(english_word, chinese_characters, jyutping)
            DO UPDATE SET
                part_of_speech = excluded.part_of_speech,
                image_data = excluded.image_data,
                audio_data = excluded.audio_data,
                created_at = excluded.created_at,
                session_id = excluded.session_id
            """,
            (
                flashcard.english_word,
                flashcard.chinese_characters,
                flashcard.jyutping,
                flashcard.part_of_speech,
                flashcard.image_data[0] if flashcard.image_data else b"",
                flashcard.audio_data,
                now,
                flashcard.session_id,
            ),
        )
        self._conn.commit()
        # Fetch the canonical row (existing or newly inserted) so we
        # always return the correct stable id.
        row = self._conn.execute(
            """
            SELECT * FROM cards
            WHERE english_word = ? AND chinese_characters = ? AND jyutping = ?
            """,
            (
                flashcard.english_word,
                flashcard.chinese_characters,
                flashcard.jyutping,
            ),
        ).fetchone()
        card_id = row["id"]  # type: ignore[index]
        # Persist all images via card_images table
        self.save_images(card_id, flashcard.image_data)
        row = self._conn.execute(
            "SELECT * FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        fc = self._row_to_flashcard(row)  # type: ignore[arg-type]
        fc.image_data = self.get_images(card_id)
        return fc

    def save_images(self, card_id: int, images: list[bytes]) -> None:
        """Save a list of image blobs for a card in the card_images table.

        Deletes any existing images for this card first (handles upsert).
        """
        self._conn.execute(
            "DELETE FROM card_images WHERE card_id = ?", (card_id,)
        )
        for order, img_data in enumerate(images):
            self._conn.execute(
                "INSERT INTO card_images (card_id, image_data, sort_order) VALUES (?, ?, ?)",
                (card_id, img_data, order),
            )
        self._conn.commit()

    def get_images(self, card_id: int) -> list[bytes]:
        """Load all image blobs for a card, ordered by sort_order."""
        rows = self._conn.execute(
            "SELECT image_data FROM card_images "
            "WHERE card_id = ? ORDER BY sort_order ASC",
            (card_id,),
        ).fetchall()
        return [row["image_data"] for row in rows]

    def get_flashcard(self, flashcard_id: int) -> Optional[Flashcard]:
        row = self._conn.execute(
            "SELECT * FROM cards WHERE id = ?", (flashcard_id,)
        ).fetchone()
        if row is None:
            return None
        fc = self._row_to_flashcard(row)
        fc.image_data = self.get_images(flashcard_id)
        return fc

    def get_all(self) -> list[Flashcard]:
        rows = self._conn.execute(
            "SELECT * FROM cards ORDER BY id ASC"
        ).fetchall()
        result: list[Flashcard] = []
        for row in rows:
            fc = self._row_to_flashcard(row)
            fc.image_data = self.get_images(row["id"])  # type: ignore[index]
            result.append(fc)
        return result

    def get_by_session(self, session_id: str) -> list["Flashcard"]:
        """Return all flashcards belonging to *session_id*."""
        rows = self._conn.execute(
            "SELECT * FROM cards WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        result: list[Flashcard] = []
        for row in rows:
            fc = self._row_to_flashcard(row)
            fc.image_data = self.get_images(row["id"])  # type: ignore[index]
            result.append(fc)
        return result

    def delete_broken_cards(self) -> int:
        """Remove cards whose image_data fails basic image magic detection.

        Checks for PNG (\\x89PNG), JPEG (\\xff\\xd8\\xff), or GIF (GIF) headers.
        Returns the number of cards deleted.
        """
        all_cards = self.get_all()
        broken_ids: list[int] = []
        for fc in all_cards:
            if fc.id is None:
                continue
            first_img = fc.image_data[0] if fc.image_data else b""
            if not self._looks_like_image(first_img):
                broken_ids.append(fc.id)
        if broken_ids:
            placeholders = ",".join("?" for _ in broken_ids)
            self._conn.execute(
                f"DELETE FROM card_images WHERE card_id IN ({placeholders})",
                broken_ids,
            )
            self._conn.execute(
                f"DELETE FROM cards WHERE id IN ({placeholders})",
                broken_ids,
            )
            self._conn.commit()
        return len(broken_ids)

    @staticmethod
    def _looks_like_image(data: bytes) -> bool:
        """Return True if *data* starts with a recognised image magic header."""
        if len(data) >= 4 and data[:4] == b"\x89PNG":
            return True
        if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
            return True
        if len(data) >= 4 and data[:4] == b"GIF8":
            return True
        if len(data) >= 6 and data[:6] in (b"\x00\x00\x01\x00\x00\x00", b"\x00\x00\x02\x00\x00\x00"):
            return True  # ICO
        return False

    def delete_flashcard(self, flashcard_id: int) -> None:
        self._conn.execute(
            "DELETE FROM card_images WHERE card_id = ?", (flashcard_id,)
        )
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
            part_of_speech=row["part_of_speech"],  # type: ignore[arg-type]
            image_data=[],  # populated by caller via get_images
            audio_data=row["audio_data"],
            created_at=row["created_at"],
            session_id=row["session_id"],
        )
