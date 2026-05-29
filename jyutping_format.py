"""Format raw Jyutping strings for HTML display.

Converts tone numbers to HTML superscript tags. Handles asterisk notation
by keeping the first number before `*` and discarding `*` and the number after.
"""

from __future__ import annotations

import re
from markupsafe import Markup


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
