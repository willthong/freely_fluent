"""Tests for card_generator custom Anki model templates.

Story 7: The exported .apkg must use a custom note type with correct
Comprehension and Production templates matching the PRD specification.

These tests inspect the model metadata stored inside the .apkg to verify
that Anki will render cards with the correct templates.
"""

import json
import tempfile
import zipfile

from card_generator import CardGenerator
from card_store import Flashcard


def _get_model_from_apkg(flashcard: Flashcard) -> dict:
    """Generate an .apkg and return the model JSON dict from collection DB."""
    generator = CardGenerator()

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        path = tmp.name

    generator.generate_apkg([flashcard], path)

    with zipfile.ZipFile(path, "r") as z:
        tmp_dir = tempfile.mkdtemp()
        db_path = z.extract("collection.anki2", tmp_dir)

    import sqlite3
    conn = sqlite3.connect(db_path)

    col_row = conn.execute("SELECT models FROM col").fetchone()
    models_json = json.loads(col_row[0])

    mid = conn.execute("SELECT mid FROM notes LIMIT 1").fetchone()[0]
    model = models_json[str(mid)]

    conn.close()
    return model


# ── Note type identity ──


def test_note_type_name_is_freelyfluentcard():
    """The custom note type is named FreelyFluentCard, not the default."""
    fc = Flashcard(
        english_word="test", chinese_characters="測", jyutping="cek3",
        image_data=[b"\x89PNG"], audio_data=b"OggS",
    )
    model = _get_model_from_apkg(fc)
    assert model["name"] == "FreelyFluentCard"


# ── Fields ──


def test_model_has_four_fields():
    """Custom model has exactly 4 fields: Jyutping, Images, Audio, PartOfSpeech."""
    fc = Flashcard(
        english_word="test", chinese_characters="測", jyutping="cek3",
        image_data=[b"\x89PNG"], audio_data=b"OggS",
    )
    model = _get_model_from_apkg(fc)
    field_names = [f["name"] for f in model["flds"]]
    assert field_names == ["Jyutping", "Images", "Audio", "PartOfSpeech"]


# ── Comprehension template ──


def test_comprehension_template_qfmt():
    """Comprehension front: Audio, Jyutping, optional POS in italics brackets."""
    fc = Flashcard(
        english_word="run", chinese_characters="跑", jyutping="pou2",
        image_data=[b"\x89PNG"], audio_data=b"OggS", part_of_speech="v",
    )
    model = _get_model_from_apkg(fc)
    comp = model["tmpls"][0]
    assert comp["name"] == "Comprehension"
    assert comp["qfmt"] == "{{Audio}}<br>{{Jyutping}}{{#PartOfSpeech}} <em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}"


def test_comprehension_template_afmt():
    """Comprehension back: FrontSide + Images + Jyutping + optional POS + audio replay."""
    fc = Flashcard(
        english_word="run", chinese_characters="跑", jyutping="pou2",
        image_data=[b"\x89PNG"], audio_data=b"OggS", part_of_speech="v",
    )
    model = _get_model_from_apkg(fc)
    comp = model["tmpls"][0]
    assert comp["afmt"] == '{{FrontSide}}<hr id="answer">{{Images}}<br>{{Jyutping}}{{#PartOfSpeech}} <em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}<br><audio src="{{Audio}}"></audio>'


# ── Production template ──


def test_production_template_qfmt():
    """Production front: Images, optional POS on a new line in italics brackets."""
    fc = Flashcard(
        english_word="run", chinese_characters="跑", jyutping="pou2",
        image_data=[b"\x89PNG"], audio_data=b"OggS", part_of_speech="v",
    )
    model = _get_model_from_apkg(fc)
    prod = model["tmpls"][1]
    assert prod["name"] == "Production"
    assert prod["qfmt"] == "{{Images}}{{#PartOfSpeech}}<br><em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}"


def test_production_template_afmt():
    """Production back: FrontSide + Jyutping + optional POS + audio playback."""
    fc = Flashcard(
        english_word="run", chinese_characters="跑", jyutping="pou2",
        image_data=[b"\x89PNG"], audio_data=b"OggS", part_of_speech="v",
    )
    model = _get_model_from_apkg(fc)
    prod = model["tmpls"][1]
    assert prod["afmt"] == '{{FrontSide}}<hr id="answer">{{Jyutping}}{{#PartOfSpeech}} <em>({{PartOfSpeech}})</em>{{/PartOfSpeech}}<br><audio src="{{Audio}}"></audio>'


# ── CSS ──


def test_css_has_center_alignment():
    """Card CSS centres text for both templates."""
    fc = Flashcard(
        english_word="test", chinese_characters="測", jyutping="cek3",
        image_data=[b"\x89PNG"], audio_data=b"OggS",
    )
    model = _get_model_from_apkg(fc)
    assert "text-align: center" in model["css"]


def test_css_limits_image_dimensions():
    """CSS constrains image max dimensions to prevent oversized cards."""
    fc = Flashcard(
        english_word="test", chinese_characters="測", jyutping="cek3",
        image_data=[b"\x89PNG"], audio_data=b"OggS",
    )
    model = _get_model_from_apkg(fc)
    assert "max-width" in model["css"]
    assert "max-height" in model["css"]


def test_css_styles_em_for_pos():
    """CSS styles <em> elements for part-of-speech hints (grey, smaller)."""
    fc = Flashcard(
        english_word="test", chinese_characters="測", jyutping="cek3",
        image_data=[b"\x89PNG"], audio_data=b"OggS",
    )
    model = _get_model_from_apkg(fc)
    assert "em" in model["css"]
    assert "color: #666" in model["css"]


# ── English and Chinese excluded from templates ──


def test_templates_reference_no_english_or_chinese_fields():
    """Neither template qfmt nor afmt references English word or Chinese characters."""
    fc = Flashcard(
        english_word="hello", chinese_characters="你好", jyutping="nei5hou2",
        image_data=[b"\x89PNG"], audio_data=b"OggS",
    )
    model = _get_model_from_apkg(fc)
    for tmpl in model["tmpls"]:
        combined = tmpl["qfmt"] + tmpl["afmt"]
        assert "Front" not in combined or "{{FrontSide}}" in combined
        assert "english" not in combined.lower()
        assert "chinese" not in combined.lower()
        assert "{{EnglishWord}}" not in combined
        assert "{{ChineseCharacters}}" not in combined
