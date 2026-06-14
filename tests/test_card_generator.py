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
        image_data=[b"iVBOR"],
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
        image_data=[b"iVBOR"],
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

        # Check that Jyutping field (fields[0]) has superscript formatting
        assert "nei<sup>5</sup>hou<sup>2</sup>" in fields[0]

        # Check that Audio field (fields[2]) has Anki [sound:] syntax
        # and Images field (fields[1]) has img tags
        assert "<img src=" in fields[1]  # Images field
        # Audio field uses Anki's [sound:filename] syntax for playback
        assert fields[2].startswith("[sound:")  # Audio field has Anki sound tag
        assert fields[2].endswith("]")

        conn.close()


def test_export_produces_valid_apkg():
    """The exported .apkg file exists, is non-zero, and is a valid zip."""
    import zipfile

    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="bye",
        chinese_characters="再見",
        jyutping="zoii3gin3",
        image_data=[b"\x89PNG\r\n"],
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


def test_multiple_images_per_flashcard_all_written():
    """When a flashcard has multiple images, all are written to media
    and appear on the card (first image on one side, rest on the other)."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="\u4f60\u597d",
        jyutping="nei5hou2",
        image_data=[
            b"\x89PNG\r\n\x1a\n first image",
            b"\xff\xd8\xff\xe0 second image",
            b"\x89PNG\r\n\x1a\n third image",
        ],
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    with zipfile.ZipFile(path, "r") as z:
        # Media files are stored as numbered entries in the zip
        # (genanki renames them). Check we have the right count:
        # 1 audio + 3 images = 4 media files + 2 dummy entries
        media_entries = [n for n in z.namelist()
                         if n not in ("collection.anki2", "media")]
        assert len(media_entries) == 4

        # Check that card fields reference multiple images
        db_path = z.extract("collection.anki2", tempfile.mkdtemp())
        conn = sqlite3.connect(db_path)
        notes = conn.execute("SELECT flds FROM notes").fetchone()
        fields = notes[0].split("\x1f")
        combined = " ".join(fields)
        # Should see img tags for all 3 images across both fields
        img_count = combined.count("<img src=")
        assert img_count >= 3, f"Expected 3 img tags, got {img_count}"
        conn.close()


def test_multiple_flashcards_produce_correct_card_count():
    """N flashcards produce N × 2 Anki cards."""
    import zipfile
    import sqlite3

    generator = CardGenerator()
    flashcards = [
        Flashcard(english_word="hello", chinese_characters="你好", jyutping="nei5hou2", image_data=[b"img1"], audio_data=b"aud1"),
        Flashcard(english_word="bye", chinese_characters="再見", jyutping="zoii3gin3", image_data=[b"img2"], audio_data=b"aud2"),
        Flashcard(english_word="thanks", chinese_characters="多謝", jyutping="do1ze6", image_data=[b"img3"], audio_data=b"aud3"),
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
        image_data=[b"iVBOR"],
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

        # Jyutping field (fields[0]) must have superscript formatting
        expected = "nei<sup>5</sup>hou<sup>2</sup>"
        assert expected in fields[0]

        conn.close()


def test_card_fields_handle_jyutping_asterisk():
    """Jyutping with asterisk: card fields show the first number, not the one after *."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="test",
        chinese_characters="測",
        jyutping="cek3*1",
        image_data=[b"iVBOR"],
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
        # The asterisk and alternative number should NOT appear in the Jyutping field
        assert "*1" not in fields[0]

        conn.close()


def test_part_of_speech_appears_on_cards_when_set():
    """When part_of_speech is set, it appears in the PartOfSpeech field
    and is rendered with <em>() tags in card templates."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="run",
        chinese_characters="\u8dd1",
        jyutping="pou2",
        image_data=[b"\x89PNG"],
        audio_data=b"OggS",
        part_of_speech="v",
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

        # PartOfSpeech field (fields[3]) contains the POS value
        assert fields[3] == "v"

        conn.close()


def test_part_of_speech_empty_when_not_set():
    """When part_of_speech is empty string, the PartOfSpeech field is empty,
    and Anki's {{#PartOfSpeech}}...{{/PartOfSpeech}} conditional hides it."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="\u4f60\u597d",
        jyutping="nei5hou2",
        image_data=[b"\x89PNG"],
        audio_data=b"OggS",
        part_of_speech="",
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

        # PartOfSpeech field (fields[3]) is empty
        assert fields[3] == ""

        conn.close()


def test_deck_name_is_cantonese():
    """The generated .apkg contains a deck named 'Cantonese'.

    Story: When the user exports cards to AnkiDroid, the deck name
    must be 'Cantonese' so imports land in the correct deck.
    """
    import zipfile
    import sqlite3
    import json

    from card_generator import CardGenerator, _DECK_ID
    from card_store import Flashcard

    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="\u4f60\u597d",
        jyutping="nei5hou2",
        image_data=[b"\x89PNG"],
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)
        conn = sqlite3.connect(db_path)

        decks_json = conn.execute("SELECT decks FROM col").fetchone()[0]
        decks = json.loads(decks_json)
        deck = decks[str(_DECK_ID)]
        assert deck["name"] == "Cantonese", f"Expected deck name 'Cantonese', got '{deck['name']}'"

        conn.close()


def test_card_uses_custom_model_not_basic_reversed():
    """The .apkg should use the custom FreelyFluentCard model with 4 fields,
    not genanki's BASIC_AND_REVERSED_CARD_MODEL which has 2 fields."""
    generator = CardGenerator()
    flashcard = Flashcard(
        english_word="test",
        chinese_characters="\u6e2c",
        jyutping="cek3",
        image_data=[b"\x89PNG"],
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)
        conn = sqlite3.connect(db_path)

        # Check the notes table has 4 fields (Jyutping, Images, Audio, PartOfSpeech)
        # Basic reversed model only has 2 fields (Front, Back)
        notes = conn.execute("SELECT flds FROM notes").fetchone()
        fields = notes[0].split("\x1f")
        assert len(fields) == 4

        conn.close()


# ── Image downscale tests ──


def _make_large_png(width: int = 2000, height: int = 1500) -> bytes:
    """Create a PNG image of the given dimensions."""
    from PIL import Image
    import io
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_small_png(width: int = 400, height: int = 300) -> bytes:
    """Create a small PNG image."""
    from PIL import Image
    import io
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _extract_image_from_apkg(apkg_path: str) -> bytes | None:
    """Extract the first non-media-file image from the apkg zip.

    In genanki packages, media files are stored as numbered files
    (e.g. "0", "1") in the zip root. The "media" file maps numbers
    to filenames. We skip "collection.anki2" and "media".
    """
    import zipfile
    import json
    with zipfile.ZipFile(apkg_path, "r") as z:
        # Load media mapping to find image files
        media = json.loads(z.read("media")) if "media" in z.namelist() else {}
        for name in z.namelist():
            if name in ("collection.anki2", "media"):
                continue
            # Check if it's listed in media with an image extension
            fname = media.get(name, name)
            if fname.endswith(".png") or fname.endswith(".jpg") or fname.endswith(".jpeg"):
                return z.read(name)
    return None


def test_large_image_is_downscaled_at_generation():
    """Images larger than max_image_width are downscaled."""
    generator = CardGenerator()
    large_png = _make_large_png(2000, 1500)

    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="你好",
        jyutping="nei5hou2",
        image_data=[large_png],
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    # Extract image from apkg and check dimensions
    img_data = _extract_image_from_apkg(path)
    assert img_data is not None, "Should have extracted an image"

    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_data))
    w, h = img.size
    max_dim = max(w, h)
    assert max_dim <= 800, f"Image too large: {w}x{h}, max dim {max_dim} > 800"
    # Aspect ratio should be preserved (2000:1500 = 4:3)
    ratio = w / h
    assert abs(ratio - 4/3) < 0.05, f"Aspect ratio changed: {w}/{h} = {ratio}"


def test_small_image_not_upscaled():
    """Images smaller than max_image_width are NOT upscaled."""
    generator = CardGenerator()
    small_png = _make_small_png(400, 300)

    flashcard = Flashcard(
        english_word="hello",
        chinese_characters="你好",
        jyutping="nei5hou2",
        image_data=[small_png],
        audio_data=b"OggS",
    )

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    img_data = _extract_image_from_apkg(path)
    assert img_data is not None

    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_data))
    w, h = img.size
    assert w == 400, f"Small image was upscaled to {w}"
    assert h == 300, f"Small image was upscaled to {h}"
