"""Plain-text (TXT / MD) extraction."""

from .base import make_result_template
from core.helpers import (
    estimate_pages_from_chars,
    extract_bib_info_from_text,
    safe_truncate,
    smart_word_count,
)


def extract_txt(txt_path: str) -> dict:
    """Extract text sample from a plain-text file (TXT or MD)."""
    result = make_result_template(txt_path)

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(txt_path, "r", encoding="gbk") as f:
                content = f.read()
        except Exception as e:
            result["note"] = f"Encoding error: {e}"
            return result
    except Exception as e:
        result["note"] = f"Read error: {e}"
        return result

    result["text_chars"] = len(content)
    result["word_count"] = smart_word_count(content)
    result["first_page_text"] = safe_truncate(content)
    result["pages"] = estimate_pages_from_chars(result["text_chars"])

    bib_info = extract_bib_info_from_text(content[:3000])
    result.update(bib_info)

    return result
