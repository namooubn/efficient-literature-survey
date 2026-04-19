"""PDF metadata and text extraction with scanned-image detection."""

import re

from .base import make_result_template
from core.config import PDF_FALLBACK_TEXT_CHARS
from core.helpers import (
    detect_scanned_pdf,
    extract_bib_info_from_text,
    extract_meta_fallback_from_text,
    get_pdf_read_pages,
    safe_truncate,
    smart_word_count,
)

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[misc, assignment]

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore[misc, assignment]


def extract_pdf(pdf_path: str, max_pages: int = 0) -> dict:
    """Extract metadata and text sample from a single PDF."""
    result = make_result_template(pdf_path)
    result["format"] = "pdf"
    read_page_texts: list[str] = []
    total_text = ""

    if PdfReader is None:
        result["note"] = "PyPDF2 not installed. Run: pip install PyPDF2"
        result["is_scanned"] = False
        return result

    try:
        reader = PdfReader(pdf_path)
        result["pages"] = len(reader.pages)

        # Check encryption
        if getattr(reader, "is_encrypted", False):
            result["is_encrypted"] = True
            try:
                reader.decrypt("")
                result["note"] += "PDF is encrypted; attempted decrypt with empty password. "
            except Exception:
                result["note"] += "PDF is encrypted and cannot be decrypted automatically. "
                result["is_scanned"] = False
                return result

        meta = reader.metadata
        if meta:
            result["author_from_meta"] = str(meta.get("/Author", ""))
            result["title_from_meta"] = str(meta.get("/Title", ""))
            creation_date = str(meta.get("/CreationDate", ""))
            m = re.search(r"D:(\d{4})", creation_date)
            if m:
                result["year"] = m.group(1)

        read_pages = get_pdf_read_pages(result["pages"], max_pages)
        for i in read_pages:
            try:
                page = reader.pages[i]
                txt = page.extract_text() or ""
                read_page_texts.append(txt)
                total_text += txt
                if i == 0:
                    result["first_page_text"] = safe_truncate(txt)
            except Exception as e:
                if not result["note"]:
                    result["note"] = ""
                result["note"] += f"Page {i} extract error: {type(e).__name__}; "
        result["text_chars"] = len(total_text)
    except Exception as e:
        read_page_texts = []
        if not result["note"]:
            result["note"] = ""
        result["note"] += f"PyPDF2 error: {type(e).__name__}: {e}; "
        # If PyPDF2 completely fails, zero out pages so fallback can try
        if result["pages"] == 0:
            result["pages"] = 0

    # Fallback to pdfplumber if PyPDF2 extracted very little text
    if result["text_chars"] < PDF_FALLBACK_TEXT_CHARS and result["pages"] > 0 and pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["pages"] = len(pdf.pages)
                read_pages = get_pdf_read_pages(result["pages"], max_pages)
                read_page_texts = []
                total_text = ""
                for i in read_pages:
                    txt = pdf.pages[i].extract_text() or ""
                    read_page_texts.append(txt)
                    total_text += txt
                    if i == 0:
                        result["first_page_text"] = safe_truncate(txt)
                result["text_chars"] = len(total_text)
        except Exception as e:
            if not result["note"]:
                result["note"] = ""
            result["note"] += f"pdfplumber fallback error: {type(e).__name__}: {e}; "

    result["word_count"] = smart_word_count(total_text) if result["text_chars"] > 0 else 0

    # Extract bibliographic info from first-page text
    bib_info = extract_bib_info_from_text(result["first_page_text"])
    result.update(bib_info)

    # Fallback: extract title/author/year from first-page text when metadata is empty
    if not result.get("title_from_meta") or not result.get("author_from_meta") or not result.get("year"):
        fallback = extract_meta_fallback_from_text(result["first_page_text"])
        if not result.get("title_from_meta"):
            result["title_from_meta"] = fallback["title"]
        if not result.get("author_from_meta"):
            result["author_from_meta"] = fallback["author"]
        if not result.get("year"):
            result["year"] = fallback["year"]

    # Fallback: extract year from filename if still not found
    if not result.get("year"):
        m = re.search(r"\b(19|20)\d{2}\b", result["filename"])
        if m:
            result["year"] = m.group(0)

    result["is_scanned"] = detect_scanned_pdf(read_page_texts, result["pages"])

    return result
