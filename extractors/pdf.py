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
    extract_chapter_text,
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

                # Monograph TOC extraction + chapter text extraction
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
                                # Extract text from top-3 matched chapters
                                # for LLM semantic re-ranking in Stage 2/3
                                chapter_texts = []
                                for ch in matched[:3]:
                                    try:
                                        ch_text = extract_chapter_text(
                                            pdf, ch, max_chars=8000
                                        )
                                        if ch_text:
                                            chapter_texts.append(
                                                {
                                                    "chapter": ch["chapter"],
                                                    "page_start": ch["page_start"],
                                                    "page_end": ch["page_end"],
                                                    "text_preview": ch_text[:1500],
                                                    "text_full": ch_text,
                                                }
                                            )
                                    except Exception:
                                        continue
                                if chapter_texts:
                                    result["chapter_texts"] = chapter_texts
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

    # Extract bibliographic info from first page
    bib_info = extract_bib_info_from_text(result["first_page_text"])
    result.update(bib_info)

    # Fallback: scan all extracted text for missing bib fields
    # (journal info sometimes appears in headers/footers of later pages)
    if not all(result.get(k) for k in ["journal", "volume", "issue", "page_range"]):
        full_bib = extract_bib_info_from_text(total_text)
        for key in ["journal", "volume", "issue", "page_range", "doi"]:
            if not result.get(key) and full_bib.get(key):
                result[key] = full_bib[key]

    # ------------------------------------------------------------------
    # Filename fallback: parse author, title, year from filename
    # ------------------------------------------------------------------
    fn_meta = _parse_filename_metadata(result["filename"])
    if not result.get("author_from_meta") and fn_meta["author"]:
        result["author_from_meta"] = fn_meta["author"]
    if not result.get("title_from_meta") and fn_meta["title"]:
        result["title_from_meta"] = fn_meta["title"]
    if not result.get("year") and fn_meta["year"]:
        result["year"] = fn_meta["year"]

    # ------------------------------------------------------------------
    # Title / year fallback from first-page text
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
        m = re.search(r"(?:^|[^0-9])(19\d{2}|20\d{2})(?:[^0-9]|$)", result["filename"])
        if m:
            result["year"] = m.group(1)

    result["is_scanned"] = detect_scanned_pdf(read_page_texts, result["pages"])

    return result


def _parse_filename_metadata(filename: str) -> dict:
    """
    Parse author, title and year from academic paper filename.

    Supports Chinese and English naming conventions:
      - Chinese: 张三_人工智能伦理研究.pdf, 张三、李四_深度学习.pdf
      - English: Smith_Deep_Learning.pdf, Smith_et_al_2020.pdf
      - Mixed:  Zhang_人工智能研究_2020.pdf, 2020_张三_深度学习.pdf
      - Citation-style: Van Dijck J, Poell T. Understanding social media logic[J]. ...pdf

    Returns {"author": str, "title": str, "year": str}.
    """
    from pathlib import Path

    result = {"author": "", "title": "", "year": ""}
    stem = Path(filename).stem

    # Strip citation markers like [J]. [M]. [C]. that sometimes appear in filenames
    stem_clean = re.sub(r"\[[JMCD]\]\.?", "", stem)

    # Extract year first (anywhere in filename)
    # Use non-digit boundaries because underscore is a \w char and breaks \b
    year_match = re.search(r"(?:^|[^0-9])(19\d{2}|20\d{2})(?:[^0-9]|$)", stem_clean)
    if year_match:
        result["year"] = year_match.group(1)

    # --- Pattern 0: Citation-style filenames with explicit author-title boundary ---
    # e.g. "Van Dijck J, Poell T. Understanding social media logic..."
    # The first period (followed by capital letter) separates author from title
    citation_match = re.match(
        r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+[A-Z](?:,\s*[A-Z][a-zA-Z]+\s+[A-Z])*)\.\s*(.+)$",
        stem_clean,
    )
    if citation_match:
        result["author"] = citation_match.group(1).strip()
        raw_title = citation_match.group(2).strip()
        # Truncate at second period if it looks like a journal/publisher divider
        raw_title = re.split(r"\.\s*(?=[A-Z])", raw_title, 1)[0]
        result["title"] = raw_title
        return result

    # Split by common separators: _, -, ——, space, ·
    # BUT: keep space-separated English names together when possible
    separators = r"[_\-——·]+"
    parts = re.split(separators, stem_clean)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return result

    # Identify author part
    author_idx = -1
    for i, part in enumerate(parts):
        # Pattern A: Pure Chinese name (2-4 hanzi)
        if re.match(r"^[\u4e00-\u9fff]{2,4}$", part):
            author_idx = i
            result["author"] = part
            break

        # Pattern B: Multiple Chinese names separated by 、，,
        if re.match(r"^[\u4e00-\u9fff]{2,4}(?:[、，,][\u4e00-\u9fff]{2,4})+$", part):
            author_idx = i
            result["author"] = part.replace("，", "、").replace(",", "、")
            break

        # Pattern C: English name(s) with comma separation (e.g. "Van Dijck J, Poell T")
        # Treat the whole part before first period as author block
        if re.match(r"^[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+[A-Z](?:,\s*[A-Z][a-zA-Z]+\s+[A-Z])*$", part):
            author_idx = i
            result["author"] = part
            break

        # Pattern D: English name with initial cap (single surname)
        if (
            re.match(r"^[A-Z][a-zA-Z]+(?:_[A-Z][a-zA-Z]+)*$", part)
            and len(part) >= 2
        ):
            author_idx = i
            result["author"] = part.replace("_", " ")
            break

        # Pattern E: English name with et al / et_al marker
        if re.match(r"^[A-Z][a-zA-Z]*(?:\s+et\s+al|\s+et_al|_et_al)$", part, re.I):
            author_idx = i
            result["author"] = part.replace("_", " ")
            break

    # Build title from remaining parts
    if author_idx >= 0:
        other_parts = [
            p for j, p in enumerate(parts) if j != author_idx
        ]
        # Filter out year-only parts
        other_parts = [
            p for p in other_parts if not re.match(r"^(19|20)\d{2}$", p)
        ]
        result["title"] = " ".join(other_parts)
    else:
        # No author identified — treat everything as title (minus year)
        non_year_parts = [
            p for p in parts if not re.match(r"^(19|20)\d{2}$", p)
        ]
        result["title"] = " ".join(non_year_parts)

    if result["title"]:
        result["title"] = re.sub(r"[_\-——\s·]+", " ", result["title"]).strip()

    return result
