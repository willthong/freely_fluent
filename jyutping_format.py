"""Format raw Jyutping strings for HTML display.

Converts tone numbers to HTML superscript tags. Handles asterisk notation
by keeping the first number before `*` and discarding `*` and the number after.
"""

from __future__ import annotations

import re
from markupsafe import Markup


def clean_jyutping(raw: str) -> str:
    """Strip non-alphabetic characters from each syllable's text part,
    preserving tone numbers and whitespace.

    This is a server-side validation to ensure only a-zA-Z characters
    survive in the romanization text portion of a Jyutping string.

    Examples:
        "nei5!! hou2???" → "nei5 hou2"
        "neoi5 ho3"      → "neoi5 ho3"  (unchanged)
        "123 nei5"       → "nei5"        (bare numbers dropped)
    """
    parts = raw.split()
    cleaned_parts = []
    for part in parts:
        # Strip all non-alpha-numeric first, preserving order
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', part)
        # Extract alpha prefix and digit suffix
        m = re.match(r'([a-zA-Z]*)(\d*)$', cleaned)
        if m:
            text, tone = m.groups()
            # Only keep if there's at least text or tone
            if text or tone:
                cleaned_parts.append(text + tone)
    return ' '.join(cleaned_parts)


def format_jyutping(raw: str) -> Markup:
    """Format a Jyutping string for HTML display.

    - Tone numbers become <sup>n</sup> HTML superscripts.
    - If an asterisk is present, the asterisk and the number immediately
      following it are removed (alternative tone discarded), keeping the
      first number before the asterisk.

    Examples:
        "nei5hou2"   → "nei<sup>5</sup>hou<sup>2</sup>"
        "nei5*3hou2" → "nei<sup>5</sup>hou<sup>2</sup>"
    """
    # Strip asterisk + alternative number (e.g. "nei5*3hou2" → "nei5hou2")
    text = re.sub(r"\*\d", "", raw)
    # Convert remaining numbers to superscript
    return Markup(re.sub(r"\d", r"<sup>\g<0></sup>", text))
