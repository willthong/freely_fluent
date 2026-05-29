"""Tests for CardStoreProtocol image methods.

PRD specifies get_images(card_id) and save_images(card_id, images) as
public protocol methods for multi-image persistence.
"""

import tempfile

from card_store import CardStore, CardStoreProtocol, Flashcard


def test_protocol_has_get_images():
    """CardStoreProtocol defines get_images."""
    methods = {
        m for m in dir(CardStoreProtocol) if not m.startswith("_")
    }
    assert "get_images" in methods


def test_protocol_has_save_images():
    """CardStoreProtocol defines save_images."""
    methods = {
        m for m in dir(CardStoreProtocol) if not m.startswith("_")
    }
    assert "save_images" in methods


def test_save_images_then_get_images_round_trips():
    """Images saved via save_images() round-trip through get_images()."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)

    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="你好",
            jyutping="nei5hou2",
            audio_data=b"ogg",
        )
    )

    images = [
        b"\x89PNG\r\n\x1a\n image1",
        b"\xff\xd8\xff\xe0 image2",
    ]
    store.save_images(fc.id, images)

    retrieved = store.get_images(fc.id)
    assert len(retrieved) == 2
    assert retrieved[0] == images[0]
    assert retrieved[1] == images[1]


def test_save_images_overwrites_existing():
    """A second save_images() replaces all previous images for the card."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)

    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="你好",
            jyutping="nei5hou2",
            image_data=[b"\x89PNG old"],
            audio_data=b"ogg",
        )
    )

    # Overwrite with new images
    store.save_images(fc.id, [b"\xff\xd8\xff new1", b"\x89PNG new2"])
    retrieved = store.get_images(fc.id)
    assert len(retrieved) == 2
    assert retrieved[0] == b"\xff\xd8\xff new1"
    assert retrieved[1] == b"\x89PNG new2"


def test_get_images_empty_for_no_images():
    """get_images returns empty list when no images stored for a card."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    store = CardStore(tmp.name)

    fc = store.save_flashcard(
        Flashcard(
            english_word="hello",
            chinese_characters="你好",
            jyutping="nei5hou2",
            image_data=[],
            audio_data=b"ogg",
        )
    )

    retrieved = store.get_images(fc.id)
    assert retrieved == []
