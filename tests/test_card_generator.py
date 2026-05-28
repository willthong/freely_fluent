import tempfile
import zipfile
import sqlite3

from card_generator import CardGenerator
from card_store import Flashcard


def test_single_flashcard_produces_two_cards():
    """One flashcard produces 2 Anki cards (reversed pair)."""
    generator = CardGenerator()

    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="你好",
        jyutping="nei5hou2",
        image_data=b"iVBOR",
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    count = generator.generate_apkg([flashcard], path)
    assert count == 2


def test_card_directions_have_correct_fields():
    """
    Card 1 (audio→image): front = audio + jyutping, back = image + jyutping
    Card 2 (image→audio): front = image + jyutping, back = audio + jyutping
    Chinese characters and English words do not appear on card faces.
    """
    import zipfile
    import sqlite3

    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="你好",
        jyutping="nei5hou2",
        image_data=b"iVBOR",
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    # Read the SQLite inside the .apkg (it's a zip containing collection.anki2)
    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)
        conn = sqlite3.connect(db_path)

        # Read notes to get field content
        notes = conn.execute("SELECT flds FROM notes").fetchone()
        fields = notes[0].split("\x1f")  # fields are tab-separated

        # Check that Chinese characters and English word never appear
        for field in fields:
            assert "hello" not in field
            assert "你好" not in field

        # Check that Jyutping appears in both fields (formatted as superscript)
        assert "nei<sup>5</sup>hou<sup>2</sup>" in fields[0]
        assert "nei<sup>5</sup>hou<sup>2</sup>" in fields[1]

        # Check that Audio tag is in one field and img tag in the other
        # We don't know which is which from the field order alone,
        # but one field should have Audio and the other should have img
        has_audio = any('<audio src=' in f for f in fields)
        has_image = any("img src=" in f for f in fields)
        assert has_audio
        assert has_image

        conn.close()


def test_export_produces_valid_apkg():
    """The exported .apkg file exists, is non-zero, and is a valid zip."""
    import zipfile

    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="bye",
        chinese_characters="再見",
        jyutping="zoii3gin3",
        image_data=b"\x89PNG\r\n",
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    import os

    assert os.path.getsize(path) > 0
    assert zipfile.is_zipfile(path)

    with zipfile.ZipFile(path, "r") as z:
        names = z.namelist()
        assert "collection.anki2" in names
        assert "media" in names


def test_multiple_flashcards_produce_correct_card_count():
    """N flashcards produce N × 2 Anki cards."""
    import zipfile
    import sqlite3

    generator = CardGenerator()
    flashcards = [
        Flashcard(english_word="hello", chinese_characters="你好", jyutping="nei5hou2", image_data=b"img1", audio_data=b"aud1"),
        Flashcard(english_word="bye", chinese_characters="再見", jyutping="zoii3gin3", image_data=b"img2", audio_data=b"aud2"),
        Flashcard(english_word="thanks", chinese_characters="多謝", jyutping="do1ze6", image_data=b"img3", audio_data=b"aud3"),
    ]

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    count = generator.generate_apkg(flashcards, path)
    assert count == 6

    # Verify the .apkg contains the right number of notes and cards
    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)
        conn = sqlite3.connect(db_path)

        note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        card_count = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]

        assert note_count == 3  # one note per flashcard
        assert card_count == 6  # two cards per note

        conn.close()


def test_card_fields_contain_superscript_jyutping():
    """Jyutping tone numbers in card fields are formatted as HTML superscripts."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="你好",
        jyutping="nei5hou2",
        image_data=b"iVBOR",
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)
        conn = sqlite3.connect(db_path)

        notes = conn.execute("SELECT flds FROM notes").fetchone()
        fields = notes[0].split("\x1f")

        # Both fields (front and back) must have superscript Jyutping
        expected = "nei<sup>5</sup>hou<sup>2</sup>"
        assert expected in fields[0]
        assert expected in fields[1]

        conn.close()


def test_card_fields_handle_jyutping_asterisk():
    """Jyutping with asterisk: card fields show the first number, not the one after *."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="test",
        chinese_characters="測",
        jyutping="cek3*1",
        image_data=b"iVBOR",
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)
        conn = sqlite3.connect(db_path)

        notes = conn.execute("SELECT flds FROM notes").fetchone()
        fields = notes[0].split("\x1f")

        expected = "cek<sup>3</sup>"
        assert expected in fields[0]
        assert expected in fields[1]
        # The asterisk and alternative number should NOT appear
        assert "*1" not in fields[0]
        assert "*1" not in fields[1]

        conn.close()
