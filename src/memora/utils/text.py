"""Text processing utilities."""

import re


def clean_text(text: str) -> str:
    """Normalize whitespace: collapse runs of whitespace into single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to max_length, appending suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
