"""Unit tests for CardStore.

Story 21: Extract CardStore into an ABC (CardStoreProtocol) and add
unit tests covering save, get, get_all, delete, and the ABC contract.
"""

import tempfile

from card_store import CardStore, CardStoreProtocol, Flashcard


def test_card_store_is_instance_of_protocol():
    """CardStore must be recognised as implementing CardStoreProtocol."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    assert isinstance(store, CardStoreProtocol)


def test_save_flashcard_returns_flashcard_with_id():
    """save_flashcard returns a Flashcard with auto-generated id."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img",
            audio_data=b"ogg",
        )
    )
    assert fc.id is not None
    assert fc.id > 0
    assert fc.english_word == "hello"
    assert fc.chinese_characters == "\u4f60\u597d"
    assert fc.jyutping == "nei5 hou2"
    assert fc.image_data == b"img"
    assert fc.audio_data == b"ogg"
    assert fc.created_at is not None


def test_get_flashcard_by_id():
    """get_flashcard retrieves card by id."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img",
            audio_data=b"ogg",
        )
    )
    result = store.get_flashcard(fc.id)
    assert result is not None
    assert result.id == fc.id
    assert result.english_word == "hello"


def test_get_flashcard_returns_none_for_missing_id():
    """get_flashcard returns None for non-existent id."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    result = store.get_flashcard(9999)
    assert result is None


def test_get_all_empty():
    """get_all returns empty list on fresh store."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    assert store.get_all() == []


def test_get_all_returns_all_cards():
    """get_all returns all saved cards in insertion order."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img1",
            audio_data=b"ogg1",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="goodbye",
            chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3",
            image_data=b"img2",
            audio_data=b"ogg2",
        )
    )
    cards = store.get_all()
    assert len(cards) == 2
    assert cards[0].english_word == "hello"
    assert cards[1].english_word == "goodbye"


def test_delete_flashcard():
    """delete_flashcard removes a card."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img",
            audio_data=b"ogg",
        )
    )
    store.delete_flashcard(fc.id)
    assert store.get_flashcard(fc.id) is None
    assert len(store.get_all()) == 0


def test_delete_nonexistent_flashcard_no_error():
    """delete_flashcard on non-existent id does not raise."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.delete_flashcard(9999)  # no error


def test_flashcard_dataclass_defaults():
    """Flashcard dataclass has sensible defaults."""
    fc = Flashcard()
    assert fc.id is None
    assert fc.english_word == ""
    assert fc.chinese_characters == ""
    assert fc.jyutping == ""
    assert fc.image_data == b""
    assert fc.audio_data == b""
    assert fc.created_at is None


def test_card_store_protocol_has_methods():
    """CardStoreProtocol defines the expected method signatures."""
    import inspect
    methods = {m: getattr(CardStoreProtocol, m) for m in dir(CardStoreProtocol) if not m.startswith("_")}
    assert "save_flashcard" in methods
    assert "get_flashcard" in methods
    assert "get_all" in methods
    assert "delete_flashcard" in methods


def test_multiple_saves_increment_ids():
    """Multiple saves get incrementing ids."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc1 = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img",
            audio_data=b"ogg",
        )
    )
    fc2 = store.save_flashcard(
        Flashcard(
            english_word="goodbye",
            chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3",
            image_data=b"img2",
            audio_data=b"ogg2",
        )
    )
    assert fc2.id > fc1.id


def test_save_flashcard_accepts_flashcard_object():
    """save_flashcard accepts a single Flashcard dataclass instead of 5 args."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img",
            audio_data=b"ogg",
        )
    )
    assert fc.id is not None
    assert fc.id > 0
    assert fc.english_word == "hello"
    assert fc.chinese_characters == "\u4f60\u597d"
    assert fc.jyutping == "nei5 hou2"
    assert fc.image_data == b"img"
    assert fc.audio_data == b"ogg"
    assert fc.created_at is not None


def test_save_flashcard_round_trips_through_get():
    """A card saved via Flashcard object round-trips through get_flashcard."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    original = Flashcard(
        english_word="goodbye",
        chinese_characters="\u518d\u89c1",
        jyutping="zaai6 gin3",
        image_data=b"img2",
        audio_data=b"ogg2",
    )
    saved = store.save_flashcard(original)
    retrieved = store.get_flashcard(saved.id)
    assert retrieved is not None
    assert retrieved.english_word == original.english_word
    assert retrieved.chinese_characters == original.chinese_characters
    assert retrieved.jyutping == original.jyutping
    assert retrieved.image_data == original.image_data
    assert retrieved.audio_data == original.audio_data


def test_card_store_created_at_has_timestamp():
    """created_at is set to a UTC ISO timestamp."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=b"img",
            audio_data=b"ogg",
        )
    )
    assert "T" in fc.created_at  # ISO format contains T separator
    assert "+00:00" in fc.created_at or "Z" in fc.created_at
