"""Base utilities shared by all format extractors."""

import os
from pathlib import Path


def make_result_template(file_path: str) -> dict:
    """Return a fresh result dict with all standard fields initialized."""
    return {
        "filename": os.path.basename(file_path),
        "relative_path": "",
        "format": Path(file_path).suffix.lower().lstrip("."),
        "pages": 0,
        "word_count": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
        "year": "",
        "journal": "",
        "publisher": "",
        "volume": "",
        "issue": "",
        "page_range": "",
        "doi": "",
        "is_encrypted": False,
        "note": "",
    }
