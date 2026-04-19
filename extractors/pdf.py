"""PDF metadata and text extraction with scanned-image detection."""

import logging
import re

from .base import make_result_template
from core.config import (
    MONOGRAPH_MIN_PAGES,
    PDF_FALLBACK_TEXT_CHARS,
    PDFPLUMBER_WORDS_SAMPLE_CHARS,
)
from core.helpers import (
    detect_scanned_pdf,
    extract_bib_info_from_text,
    extract_meta_fallback_from_text,
    extract_meta_fallback_from_text_enhanced,
    extract_toc_from_pdf,
    get_pdf_read_pages,
    match_chapters_by_keywords,
    safe_truncate,
    smart_word_count,
    strip_cnki_watermarks,
)

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[misc, assignment]

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore[misc, assignment]


def extract_pdf(pdf_path: str, max_pages: int = 0, keywords: str = "") -> dict:
    """Extract metadata and text sample from a single PDF."""
    result = make_result_template(pdf_path)
    result["format"] = "pdf"
    read_page_texts: list[str] = []
    total_text = ""
    words_data: list | None = None

    if PdfReader is None:
        result["note"] = "PyPDF2 not installed. Run: pip install PyPDF2"
        result["is_scanned"] = False
        return result

    # ------------------------------------------------------------------
    # Phase 1: PyPDF2 pass
    # ------------------------------------------------------------------
    try:
        reader = PdfReader(pdf_path)
        result["pages"] = len(reader.pages)

        # Encryption check with tiered handling
        if getattr(reader, "is_encrypted", False):
            result["is_encrypted"] = True
            try:
                reader.decrypt("")
                result["encryption_level"] = "light"
                result["note"] += "轻度加密，已自动解密。 "
            except Exception:
                result["encryption_level"] = "full"
                result["note"] += "完全加密，需手动解密。 "
                result["is_scanned"] = False
                return result

        meta = reader.metadata
        if meta:
            author = str(meta.get("/Author", "")).strip()
            # Filter known garbage author values from PDF metadata
            if author.lower() in ("cnki", "cnki数据库", "知网", "how to cite this article", "author", "authors"):
                author = ""
            result["author_from_meta"] = author
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
        if result["pages"] == 0:
            result["pages"] = 0

    # ------------------------------------------------------------------
    # Phase 2: pdfplumber (always run if available for layout + TOC)
    # ------------------------------------------------------------------
    if pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["pages"] = len(pdf.pages)

                # Determine whether we need a full text fallback
                need_text_fallback = (
                    result["text_chars"] < PDF_FALLBACK_TEXT_CHARS
                    and result["pages"] > 0
                )

                if need_text_fallback:
                    read_pages = get_pdf_read_pages(result["pages"], max_pages)
                    read_page_texts = []
                    total_text = ""
                    for i in read_pages:
                        try:
                            txt = pdf.pages[i].extract_text() or ""
                            read_page_texts.append(txt)
                            total_text += txt
                            if i == 0:
                                result["first_page_text"] = safe_truncate(txt)
                        except Exception:
                            continue
                    result["text_chars"] = len(total_text)

                # Layout analysis on first page for enhanced metadata
                try:
                    first_page = pdf.pages[0]
                    # Try to get words with font info
                    raw_words = first_page.extract_words(
                        extra_attrs=["fontname", "size"]
                    )
                    words_data = [
                        {"text": w["text"], "top": w.get("top", 0),
                         "fontname": w.get("fontname", ""), "size": w.get("size", 0)}
                        for w in raw_words
                    ]
                    # If first_page_text is empty/short, re-extract via pdfplumber
                    if not result["first_page_text"]:
                        fp_text = first_page.extract_text() or ""
                        result["first_page_text"] = safe_truncate(
                            strip_cnki_watermarks(fp_text)
                        )
                except Exception:
                    pass

                # Monograph TOC extraction
                if result["pages"] > MONOGRAPH_MIN_PAGES:
                    try:
                        toc = extract_toc_from_pdf(pdf, result["pages"])
                        result["toc"] = toc
                        if keywords and toc:
                            matched = match_chapters_by_keywords(toc, keywords)
                            result["matched_chapters"] = matched
                            if matched:
                                result["note"] += (
                                    f"检测到{len(matched)}个匹配章节；"
                                )
                    except Exception:
                        pass

                # Confirm light encryption if pdfplumber can read it
                if result["is_encrypted"] and result["encryption_level"] == "light":
                    try:
                        _ = pdf.pages[0].extract_text()
                        # pdfplumber can read — keep light
                    except Exception:
                        # pdfplumber also failed — upgrade to full
                        result["encryption_level"] = "full"
                        result["note"] += "pdfplumber也无法读取，判定为完全加密。 "

        except Exception as e:
            if not result["note"]:
                result["note"] = ""
            result["note"] += f"pdfplumber error: {type(e).__name__}: {e}; "

    result["word_count"] = smart_word_count(total_text) if result["text_chars"] > 0 else 0

    # Strip CNKI watermarks before further processing
    if result["first_page_text"]:
        clean_first = strip_cnki_watermarks(result["first_page_text"])
        # Only update if stripping actually changed something
        if clean_first != result["first_page_text"]:
            result["first_page_text"] = safe_truncate(clean_first)

    # Extract bibliographic info
    bib_info = extract_bib_info_from_text(result["first_page_text"])
    result.update(bib_info)

    # ------------------------------------------------------------------
    # Author: prefer filename extraction; skip unreliable text fallback
    # ------------------------------------------------------------------
    if not result.get("author_from_meta"):
        author_from_fn = _extract_author_from_filename(result["filename"])
        if author_from_fn:
            result["author_from_meta"] = author_from_fn

    # ------------------------------------------------------------------
    # Title / year fallback from first-page text (author left empty if
    # neither metadata nor filename yielded a value)
    # ------------------------------------------------------------------
    has_meta_gap = (
        not result.get("title_from_meta")
        or not result.get("year")
    )
    if has_meta_gap:
        if words_data:
            fallback = extract_meta_fallback_from_text_enhanced(
                result["first_page_text"], words_data
            )
            result["title_confidence"] = "high"
        else:
            fallback = extract_meta_fallback_from_text(result["first_page_text"])
            result["title_confidence"] = "medium"

        if not result.get("title_from_meta"):
            result["title_from_meta"] = fallback["title"]
        if not result.get("year"):
            result["year"] = fallback["year"]

    # Year from filename as last resort
    if not result.get("year"):
        m = re.search(r"\b(19|20)\d{2}\b", result["filename"])
        if m:
            result["year"] = m.group(0)

    result["is_scanned"] = detect_scanned_pdf(read_page_texts, result["pages"])

    return result


def _extract_author_from_filename(filename: str) -> str:
    """Heuristic author extraction from filename before first period."""
    from pathlib import Path

    stem = Path(filename).stem
    parts = stem.split(".", 1)
    if len(parts) < 2:
        return ""
    author_part = parts[0].strip()
    words = author_part.split()
    capitalized = [w for w in words if w and w[0].isupper()]
    if len(capitalized) >= 2 and 5 <= len(author_part) <= 80:
        return author_part
    return ""
