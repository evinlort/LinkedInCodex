from __future__ import annotations

import re
import unicodedata


def rule_normalize(text: str) -> str:
    """Normalize rule text without using it as the evidence surface."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def punctuation_heavy(text: str) -> bool:
    return any(char in text for char in ("+", "#", ".", "/", "-"))

