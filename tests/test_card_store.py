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
            image_data=[b"img"],
            audio_data=b"ogg",
        )
    )
    assert fc.id is not None
    assert fc.id > 0
    assert fc.english_word == "hello"
    assert fc.chinese_characters == "\u4f60\u597d"
    assert fc.jyutping == "nei5 hou2"
    assert fc.image_data == [b"img"]
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
            image_data=[b"img"],
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
            image_data=[b"img1"],
            audio_data=b"ogg1",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="goodbye",
            chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3",
            image_data=[b"img2"],
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
            image_data=[b"img"],
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
    assert fc.image_data == []
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
            image_data=[b"img"],
            audio_data=b"ogg",
        )
    )
    fc2 = store.save_flashcard(
        Flashcard(
            english_word="goodbye",
            chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3",
            image_data=[b"img2"],
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
            image_data=[b"img"],
            audio_data=b"ogg",
        )
    )
    assert fc.id is not None
    assert fc.id > 0
    assert fc.english_word == "hello"
    assert fc.chinese_characters == "\u4f60\u597d"
    assert fc.jyutping == "nei5 hou2"
    assert fc.image_data == [b"img"]
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
        image_data=[b"img2"],
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
            image_data=[b"img"],
            audio_data=b"ogg",
        )
    )
    assert "T" in fc.created_at  # ISO format contains T separator
    assert "+00:00" in fc.created_at or "Z" in fc.created_at


# ── Session scoping ──

def test_save_flashcard_records_session_id():
    """When a Flashcard has a session_id, it is persisted and retrievable."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img"],
            audio_data=b"ogg",
            session_id="sess-abc",
        )
    )
    assert fc.session_id == "sess-abc"
    retrieved = store.get_flashcard(fc.id)
    assert retrieved is not None
    assert retrieved.session_id == "sess-abc"


def test_get_by_session_returns_only_matching_cards():
    """get_by_session returns only cards belonging to the given session."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img1"],
            audio_data=b"ogg1",
            session_id="sess-1",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="goodbye",
            chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3",
            image_data=[b"img2"],
            audio_data=b"ogg2",
            session_id="sess-2",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="thanks",
            chinese_characters="\u8b1d\u8b1d",
            jyutping="mei5 mei5",
            image_data=[b"img3"],
            audio_data=b"ogg3",
            session_id="sess-1",
        )
    )
    result = store.get_by_session("sess-1")
    assert len(result) == 2
    assert {fc.english_word for fc in result} == {"hello", "thanks"}


def test_get_by_session_returns_empty_for_unknown_session():
    """get_by_session returns empty list when no cards match."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img"],
            audio_data=b"ogg",
            session_id="sess-1",
        )
    )
    assert store.get_by_session("sess-999") == []


# ── Broken cards cleanup ──


def test_delete_broken_cards_removes_non_image_bytes():
    """delete_broken_cards removes cards whose image_data fails magic detection."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    # Good card (PNG magic bytes)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"\x89PNG\r\n\x1a\n good image"],
            audio_data=b"ogg",
        )
    )
    # Broken card (ASCII text instead of image)
    store.save_flashcard(
        Flashcard(
            english_word="world",
            chinese_characters="\u4e16\u754c",
            jyutping="sei3 gaai3",
            image_data=[b"HTTP Error 403 - Forbidden"],
            audio_data=b"ogg2",
        )
    )
    # Another broken card
    store.save_flashcard(
        Flashcard(
            english_word="test",
            chinese_characters="\u6e2c\u8a66",
            jyutping="cing3 sai3",
            image_data=[],
            audio_data=b"ogg3",
        )
    )
    assert len(store.get_all()) == 3
    deleted = store.delete_broken_cards()
    assert deleted == 2  # 2 broken cards removed
    remaining = store.get_all()
    assert len(remaining) == 1
    assert remaining[0].english_word == "hello"


def test_delete_broken_cards_no_op_when_all_good():
    """delete_broken_cards returns 0 when all cards have valid images."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"\x89PNG\r\n\x1a\n image data"],
            audio_data=b"ogg",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="goodbye",
            chinese_characters="\u518d\u89c1",
            jyutping="zaai6 gin3",
            image_data=[b"\xff\xd8\xff\xe0 JPEG image"],
            audio_data=b"ogg2",
        )
    )
    deleted = store.delete_broken_cards()
    assert deleted == 0
    assert len(store.get_all()) == 2


def test_delete_broken_cards_in_protocol():
    """delete_broken_cards is defined on CardStoreProtocol."""
    methods = {
        m: getattr(CardStoreProtocol, m)
        for m in dir(CardStoreProtocol)
        if not m.startswith("_")
    }
    assert "delete_broken_cards" in methods


def test_get_by_session_in_protocol():
    """get_by_session is defined on CardStoreProtocol."""
    import inspect
    methods = {
        m: getattr(CardStoreProtocol, m)
        for m in dir(CardStoreProtocol)
        if not m.startswith("_")
    }
    assert "get_by_session" in methods


def test_flashcard_defaults_session_id_empty():
    """Flashcard defaults session_id to empty string."""
    fc = Flashcard()
    assert fc.session_id == ""


# ── Multiple images via card_images table ──

def test_save_and_retrieve_multiple_images():
    """Saving a flashcard with multiple images and retrieving them
    round-trips through the card_images table."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[
                b"\x89PNG\r\n\x1a\n img1 data",
                b"\x89PNG\r\n\x1a\n img2 data",
                b"\xff\xd8\xff\xe0 img3 jpeg",
            ],
            audio_data=b"OggS audio",
        )
    )
    assert fc.id is not None
    retrieved = store.get_flashcard(fc.id)
    assert retrieved is not None
    assert len(retrieved.image_data) == 3
    assert retrieved.image_data[0] == b"\x89PNG\r\n\x1a\n img1 data"
    assert retrieved.image_data[1] == b"\x89PNG\r\n\x1a\n img2 data"
    assert retrieved.image_data[2] == b"\xff\xd8\xff\xe0 img3 jpeg"


def test_save_and_retrieve_empty_images():
    """Saving a flashcard with no images returns empty list."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="test",
            chinese_characters="\u6e2c\u8a66",
            jyutping="cing3 sai3",
            image_data=[],
            audio_data=b"OggS",
        )
    )
    retrieved = store.get_flashcard(fc.id)
    assert retrieved is not None
    assert retrieved.image_data == []


def test_images_preserved_after_upsert():
    """Re-saving with the same uniqueness key replaces images."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"\x89PNG old img"],
            audio_data=b"OggS old",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"\x89PNG new img1", b"\xff\xd8\xff new img2"],
            audio_data=b"OggS new",
        )
    )
    cards = store.get_all()
    assert len(cards) == 1
    assert len(cards[0].image_data) == 2
    assert cards[0].image_data[0] == b"\x89PNG new img1"
    assert cards[0].image_data[1] == b"\xff\xd8\xff new img2"


# ── Deduplication ──

def test_save_flashcard_deduplicates_by_uniqueness_key():
    """Saving the same (english_word, chinese_characters, jyutping) twice
    results in only one card in the store."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc1 = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img1"],
            audio_data=b"ogg1",
        )
    )
    fc2 = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img2"],
            audio_data=b"ogg2",
        )
    )
    assert len(store.get_all()) == 1
    assert fc1.id == fc2.id


def test_save_flashcard_upsert_updates_image_and_audio():
    """A second save with the same uniqueness key updates image_data and
    audio_data with the new values."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img1"],
            audio_data=b"ogg1",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img2"],
            audio_data=b"ogg2",
        )
    )
    cards = store.get_all()
    assert len(cards) == 1
    assert cards[0].image_data == [b"img2"]
    assert cards[0].audio_data == b"ogg2"


def test_save_flashcard_different_jyutping_is_separate_card():
    """Same word + characters but different jyutping creates a separate card."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="word",
            chinese_characters="\u8aaa",
            jyutping="joi1",
            image_data=[b"img1"],
            audio_data=b"ogg1",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="word",
            chinese_characters="\u8aaa",
            jyutping="joi2",
            image_data=[b"img2"],
            audio_data=b"ogg2",
        )
    )
    cards = store.get_all()
    assert len(cards) == 2


def test_save_flashcard_different_word_is_separate_card():
    """Different english_word creates a separate card even with same chars."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img1"],
            audio_data=b"ogg1",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="hi",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"img2"],
            audio_data=b"ogg2",
        )
    )
    cards = store.get_all()
    assert len(cards) == 2


# ── Part-of-speech field ──


def test_flashcard_defaults_part_of_speech_empty():
    """Flashcard defaults part_of_speech to empty string."""
    fc = Flashcard()
    assert fc.part_of_speech == ""


def test_save_and_retrieve_part_of_speech():
    """Saving a flashcard with part_of_speech round-trips through CardStore."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"\x89PNG img"],
            audio_data=b"ogg",
            part_of_speech="n",
        )
    )
    assert fc.part_of_speech == "n"
    retrieved = store.get_flashcard(fc.id)
    assert retrieved is not None
    assert retrieved.part_of_speech == "n"


def test_save_and_retrieve_empty_part_of_speech():
    """A flashcard with empty part_of_speech persists and returns empty."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="\u4f60\u597d",
            jyutping="nei5 hou2",
            image_data=[b"\x89PNG img"],
            audio_data=b"ogg",
            part_of_speech="",
        )
    )
    retrieved = store.get_flashcard(fc.id)
    assert retrieved is not None
    assert retrieved.part_of_speech == ""


def test_get_all_preserves_part_of_speech():
    """get_all returns flashcards with part_of_speech populated."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)
    store.save_flashcard(
        Flashcard(
            english_word="run",
            chinese_characters="\u8dd1",
            jyutping="pou2",
            image_data=[b"\x89PNG"],
            audio_data=b"ogg",
            part_of_speech="v",
        )
    )
    store.save_flashcard(
        Flashcard(
            english_word="big",
            chinese_characters="\u5927",
            jyutping="daai6",
            image_data=[b"\x89PNG"],
            audio_data=b"ogg2",
            part_of_speech="adj",
        )
    )
    cards = store.get_all()
    assert len(cards) == 2
    assert cards[0].part_of_speech == "v"
    assert cards[1].part_of_speech == "adj"
