"""Tests for Jyutping formatting — numbers to HTML superscript, asterisk handling."""

from jyutping_format import clean_jyutping, format_jyutping


def test_basic_jyutping_numbers_become_superscript():
    """Tone numbers in Jyutping are formatted as HTML superscripts."""
    assert format_jyutping("nei5hou2") == "nei<sup>5</sup>hou<sup>2</sup>"


def test_asterisk_keeps_first_number_drops_alternative():
    """When an asterisk appears, keep the first number before it and discard the asterisk and the number after."""
    assert format_jyutping("nei5*3hou2") == "nei<sup>5</sup>hou<sup>2</sup>"


def test_single_syllable():
    """A single-syllable Jyutping with one tone number is superscripted."""
    assert format_jyutping("aa1") == "aa<sup>1</sup>"


def test_multiple_syllables():
    """A multi-syllable Jyutping with several tone numbers is fully superscripted."""
    assert format_jyutping("zoii3gin3") == "zoii<sup>3</sup>gin<sup>3</sup>"


def test_multiple_asterisks():
    """Each asterisk and its following number is removed, keeping the preceding number."""
    assert format_jyutping("dou6*1ze6*2") == "dou<sup>6</sup>ze<sup>6</sup>"


def test_asterisk_at_end():
    """An asterisk at the end with a trailing number is simply stripped."""
    assert format_jyutping("lou6*2") == "lou<sup>6</sup>"


def test_clean_jyutping_removes_non_alpha():
    """Non-alphabetic characters in syllable text are stripped."""
    assert clean_jyutping("nei5!! hou2???") == "nei5 hou2"


def test_clean_jyutping_preserves_valid():
    """Valid jyutping passes through unchanged."""
    assert clean_jyutping("nei5 hou2") == "nei5 hou2"


def test_clean_jyutping_empty_string():
    """Empty input returns empty string."""
    assert clean_jyutping("") == ""


def test_clean_jyutping_only_garbage():
    """Input with no valid syllable text returns empty."""
    assert clean_jyutping("!!! ???") == ""


def test_clean_jyutping_mixed_with_valid():
    """Mixed garbled input still preserves valid parts."""
    assert clean_jyutping("nei5!! hou2") == "nei5 hou2"



