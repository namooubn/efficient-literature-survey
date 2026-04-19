"""EPUB metadata and text extraction."""

from .base import make_result_template
from core.config import EPUB_BIB_SAMPLE_CHARS, EPUB_DOCUMENT_SAMPLE_COUNT
from core.helpers import (
    estimate_pages_from_chars,
    extract_bib_info_from_text,
    safe_truncate,
    smart_word_count,
)

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    ebooklib = None  # type: ignore[misc, assignment]
    epub = None  # type: ignore[misc, assignment]
    BeautifulSoup = None  # type: ignore[misc, assignment]


def extract_epub(epub_path: str) -> dict:
    """Extract metadata and text sample from an EPUB file."""
    result = make_result_template(epub_path)
    result["format"] = "epub"

    if ebooklib is None or epub is None or BeautifulSoup is None:
        result["note"] = "Missing dependency: pip install ebooklib beautifulsoup4"
        return result

    try:
        book = epub.read_epub(epub_path)

        title_list = book.get_metadata("DC", "title")
        if title_list:
            result["title_from_meta"] = str(title_list[0][0])
        creator_list = book.get_metadata("DC", "creator")
        if creator_list:
            result["author_from_meta"] = str(creator_list[0][0])

        all_texts = []
        count = 0
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                if text:
                    all_texts.append(text)
                    count += 1
                if count >= EPUB_DOCUMENT_SAMPLE_COUNT:
                    break

        full_text = "\n".join(all_texts)
        result["text_chars"] = len(full_text)
        result["word_count"] = smart_word_count(full_text)
        result["first_page_text"] = safe_truncate(full_text)
        result["pages"] = estimate_pages_from_chars(result["text_chars"])

        bib_info = extract_bib_info_from_text(full_text[:EPUB_BIB_SAMPLE_CHARS])
        result.update(bib_info)

    except Exception as e:
        result["note"] = f"EPUB extraction error: {e}"

    return result
