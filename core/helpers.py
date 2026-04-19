"""Shared helper functions used across extractors and report generation."""

import difflib
import hashlib
import logging
import math
import re
from pathlib import Path

from .constants import _COMPOUND_SURNAMES
from .config import (
    BIB_TEXT_SCAN_LINES,
    CHARS_PER_PAGE,
    CNKI_WATERMARK_KEYWORDS,
    DOCX_SAMPLE_CHARS,
    DOCX_TABLE_SAMPLE_COUNT,
    EPUB_BIB_SAMPLE_CHARS,
    EPUB_DOCUMENT_SAMPLE_COUNT,
    LONG_DOC_HEAD_PAGES,
    LONG_DOC_TAIL_PAGES,
    META_TITLE_CANDIDATE_LINES,
    META_TITLE_MAX_LEN,
    META_TITLE_MIN_LEN,
    MONOGRAPH_KEYWORD_MATCH_MIN_PAGES,
    MONOGRAPH_MIN_PAGES,
    MONOGRAPH_TOC_SCAN_PAGES,
    PDF_FALLBACK_TEXT_CHARS,
    PDFPLUMBER_FONT_DIFF_THRESHOLD,
    PDFPLUMBER_MIN_FONT_FOR_TITLE,
    SCANNED_DENSITY_THRESHOLD,
    SCANNED_EMPTY_RATIO,
    SCANNED_MIN_CHARS_PAGE,
    SCANNED_TOTAL_CHARS_HARD,
    SCANNED_TOTAL_CHARS_MAX,
    SHORT_DOC_THRESHOLD,
    TEXT_TRUNCATE_LIMIT,
    TXT_BIB_SAMPLE_CHARS,
)


# ---------------------------------------------------------------------------
# String / text utilities
# ---------------------------------------------------------------------------


def safe_truncate(text: str, limit: int = TEXT_TRUNCATE_LIMIT) -> str:
    return text[:limit] if text else ""


def smart_word_count(text: str) -> int:
    """Estimate word count for mixed Chinese/English text."""
    if not text:
        return 0
    cn_chars = re.findall(
        r"[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002b73f]",
        text,
    )
    en_tokens = re.findall(r"\b[a-zA-Z]+\b", text)
    if len(cn_chars) == 0:
        return len(text.split())
    return len(cn_chars) + len(en_tokens)


# ---------------------------------------------------------------------------
# Metadata extraction fallback from first-page text
# ---------------------------------------------------------------------------


def extract_meta_fallback_from_text(text: str) -> dict:
    """
    Attempt to extract title and author from the first-page / front-matter text
    when document metadata fields are empty.

    Returns {"title": "", "author": "", "year": ""}.
    """
    result = {"title": "", "author": "", "year": ""}
    if not text:
        return result

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return result

    # Title heuristic: pick the longest line among the first few that
    # falls inside the allowed length window and isn't pure numeric.
    candidates = []
    for ln in lines[:META_TITLE_CANDIDATE_LINES]:
        ln_stripped = ln.replace(" ", "").replace("\t", "")
        if (
            META_TITLE_MIN_LEN <= len(ln_stripped) <= META_TITLE_MAX_LEN
            and not ln_stripped.isdigit()
        ):
            candidates.append(ln)
    if candidates:
        # Prefer the longest candidate as the title
        result["title"] = max(candidates, key=len)

    # Author heuristic: look for explicit markers
    author_patterns = [
        r"(?:作者|Author|Authors)[:： \t]+([^\n]{2,80})",
        r"(?:著者|Writer|by)[:： \t]+([^\n]{2,80})",
    ]
    for pat in author_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["author"] = m.group(1).strip()
            break

    # Filter known garbage author values from fallback extraction
    if result["author"].lower() in (
        "how to cite this article",
        "cnki",
        "cnki数据库",
        "知网",
        "author",
        "authors",
    ):
        result["author"] = ""

    # Year heuristic: try to extract a 4-digit year from text
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        result["year"] = year_match.group(0)

    return result


# ---------------------------------------------------------------------------
# Name handling
# ---------------------------------------------------------------------------


def split_chinese_name(name: str) -> tuple[str, str]:
    """Split a Chinese name into surname and given name, handling compound surnames."""
    name = name.strip().replace(" ", "")
    if not name:
        return ("", "")
    for cs in _COMPOUND_SURNAMES:
        if name.startswith(cs):
            return (cs, name[len(cs) :])
    return (name[0], name[1:])


# ---------------------------------------------------------------------------
# Page / document utilities
# ---------------------------------------------------------------------------


def estimate_pages_from_chars(
    char_count: int, chars_per_page: int = CHARS_PER_PAGE
) -> int:
    """Estimate page count for text-based files where true pagination is unknown."""
    return max(1, math.ceil(char_count / chars_per_page))


def get_pdf_read_pages(total_pages: int, max_pages: int = 0) -> list[int]:
    """
    Decide which pages to read based on document length.

    - Short docs (<= SHORT_DOC_THRESHOLD pages): read all pages.
    - Long docs (> SHORT_DOC_THRESHOLD pages): read first LONG_DOC_HEAD_PAGES
      + last LONG_DOC_TAIL_PAGES pages.
    - max_pages > 0 overrides the heuristic.
    """
    if max_pages > 0:
        return list(range(min(total_pages, max_pages)))
    if total_pages <= SHORT_DOC_THRESHOLD:
        return list(range(total_pages))
    pages = list(range(min(LONG_DOC_HEAD_PAGES, total_pages)))
    pages.extend(range(max(0, total_pages - LONG_DOC_TAIL_PAGES), total_pages))
    return sorted(set(pages))


# ---------------------------------------------------------------------------
# Scanned PDF detection
# ---------------------------------------------------------------------------


def detect_scanned_pdf(read_page_texts: list[str], total_pages: int) -> bool:
    """
    Multi-page sampling heuristic for scanned/image-based PDF detection.
    Only considers pages that were actually read.
    """
    if total_pages <= 1 or not read_page_texts:
        return False

    total_chars = sum(len(t) for t in read_page_texts)
    if total_chars > SCANNED_TOTAL_CHARS_MAX:
        return False

    read_count = len(read_page_texts)
    indices = [0]
    if read_count > 3:
        mid = read_count // 2
        if mid > 0:
            indices.append(mid)
    if read_count > 5:
        end = read_count - 1
        if end not in indices:
            indices.append(end)

    sampled = [read_page_texts[i] for i in indices if i < read_count]
    empty_samples = sum(1 for t in sampled if len(t.strip()) < SCANNED_MIN_CHARS_PAGE)
    if len(sampled) >= 2 and empty_samples / len(sampled) >= SCANNED_EMPTY_RATIO:
        return True

    density = total_chars / read_count if read_count > 0 else 0
    if density < SCANNED_DENSITY_THRESHOLD and read_count > 3:
        return True

    if total_chars < SCANNED_TOTAL_CHARS_HARD:
        return True

    return False


# ---------------------------------------------------------------------------
# Bibliographic metadata extraction from text
# ---------------------------------------------------------------------------


def extract_bib_info_from_text(text: str) -> dict:
    """
    Attempt to extract journal/publisher/volume/issue/pages/year/DOI from
    the first page / front matter text using heuristic regexes.
    """
    info = {
        "journal": "",
        "publisher": "",
        "volume": "",
        "issue": "",
        "page_range": "",
        "doi": "",
    }
    if not text:
        return info

    # DOI
    doi_match = re.search(
        r'\b(10\.\d{4,}(?:\.\d+)*/[^\s"<>]+)', text, re.IGNORECASE
    )
    if doi_match:
        info["doi"] = doi_match.group(1)

    # Volume / Issue – English patterns
    vol_match = re.search(
        r"(?:Vol\.?|Volume)\s*(\d+)(?:\s*[,:\s]*(?:No\.?|Issue|#)\s*(\d+))?",
        text,
        re.IGNORECASE,
    )
    if vol_match:
        info["volume"] = vol_match.group(1)
        if vol_match.group(2):
            info["issue"] = vol_match.group(2)

    # Pages – English patterns: pp. 123-145, p. 123, 123–145
    page_match = re.search(r"(?:pp?\.?\s*)?(\d+)[\s–—-]+(\d+)", text)
    if page_match:
        info["page_range"] = f"{page_match.group(1)}-{page_match.group(2)}"

    # Volume / Issue / Pages – Chinese patterns
    cn_vol = re.search(r"第\s*(\d+)\s*卷", text)
    cn_issue = re.search(r"第\s*(\d+)\s*期", text)
    cn_page = re.search(r"第\s*(\d+)\s*[—–~\-]\s*(\d+)\s*页", text)
    if cn_vol:
        info["volume"] = cn_vol.group(1)
    if cn_issue:
        info["issue"] = cn_issue.group(1)
    if cn_page:
        info["page_range"] = f"{cn_page.group(1)}-{cn_page.group(2)}"

    # Journal / Publisher heuristics
    cn_journal = re.search(r"《([^》]{3,50})》", text)
    if cn_journal:
        info["journal"] = cn_journal.group(1).strip()

    for line in text.splitlines()[:BIB_TEXT_SCAN_LINES]:
        line = line.strip()
        if 10 < len(line) < 80 and line.isupper() and line.replace(" ", "").isalpha():
            if not info["journal"]:
                info["journal"] = line.title()
            break

    return info


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def find_duplicates(results: list[dict], threshold: float = 0.80) -> dict[str, list[str]]:
    """
    Detect duplicate references by title similarity (SequenceMatcher).
    Returns {filename: [list of duplicate filenames]}.
    """
    dups: dict[str, list[str]] = {}
    n = len(results)
    for i in range(n):
        title_i = (
            results[i].get("title_from_meta") or results[i]["filename"]
        ).lower().strip()
        if not title_i:
            continue
        for j in range(i + 1, n):
            title_j = (
                results[j].get("title_from_meta") or results[j]["filename"]
            ).lower().strip()
            if not title_j:
                continue
            ratio = difflib.SequenceMatcher(None, title_i, title_j).ratio()
            if ratio >= threshold:
                fi = results[i]["filename"]
                fj = results[j]["filename"]
                dups.setdefault(fi, []).append(f"{fj} (相似度 {ratio:.0%})")
                dups.setdefault(fj, []).append(f"{fi} (相似度 {ratio:.0%})")
    for k in dups:
        seen = set()
        uniq = []
        for v in dups[k]:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        dups[k] = uniq
    return dups


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------


def file_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file for cache invalidation."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


# ---------------------------------------------------------------------------
# CNKI watermark filtering
# ---------------------------------------------------------------------------


def strip_cnki_watermarks(text: str) -> str:
    """Remove lines containing CNKI watermark keywords."""
    if not text:
        return text
    lines = text.splitlines()
    filtered = []
    for ln in lines:
        if any(kw in ln for kw in CNKI_WATERMARK_KEYWORDS):
            continue
        filtered.append(ln)
    return "\n".join(filtered)


# ---------------------------------------------------------------------------
# Monograph TOC extraction
# ---------------------------------------------------------------------------


def extract_toc_from_pdf(pdf, total_pages: int) -> list[dict]:
    """
    Scan the first MONOGRAPH_TOC_SCAN_PAGES of a pdfplumber PDF for a
    table of contents.  Returns a list of dicts:
        [{"chapter": str, "page_start": int, "page_end": int}, ...]
    """
    toc: list[dict] = []
    scan_limit = min(MONOGRAPH_TOC_SCAN_PAGES, total_pages)

    # Try multiple TOC patterns
    toc_patterns = [
        # English: "Chapter 1  Introduction .................. 23"
        r"(?:Chapter|Ch\.?|Part|Section)\s*[\dIVX]+[\s.]+(.+?)[\s.]+(\d+)",
        # Chinese: "第一章 绪论........................23" or "第1章 绪论 .... 23"
        r"第[\s]*([一二三四五六七八九十\d]+)[\s]*章[\s]+(.+?)[\s.]+(\d+)",
        # Chinese alt: "一、绪论 .... 23"
        r"([一二三四五六七八九十][、\.\s]+.+?)[\s.]+(\d+)",
        # Simple: "Introduction .................... 23"
        r"([A-Za-z\u4e00-\u9fff][A-Za-z\s\u4e00-\u9fff]+)[\s.]+(\d+)",
    ]

    for page_idx in range(scan_limit):
        try:
            page = pdf.pages[page_idx]
            text = page.extract_text() or ""
            if not text:
                continue
            for pat in toc_patterns:
                for m in re.finditer(pat, text):
                    groups = m.groups()
                    if len(groups) >= 2:
                        if len(groups) == 3 and re.match(r"[一二三四五六七八九十\d]+$", groups[0]):
                            # Chinese chapter pattern: groups = (num, title, page)
                            chapter = f"第{groups[0]}章 {groups[1].strip()}"
                            page_num = int(groups[2])
                        else:
                            chapter = groups[0].strip()
                            page_num = int(groups[-1])
                        if chapter and page_num > 0:
                            toc.append({"chapter": chapter, "page_start": page_num, "page_end": 0})
        except Exception:
            continue

    # Filter noise: skip very short or very long chapter names
    MIN_CHAPTER_LEN = 3
    MAX_CHAPTER_LEN = 120
    toc = [
        e for e in toc
        if MIN_CHAPTER_LEN <= len(e["chapter"].strip()) <= MAX_CHAPTER_LEN
    ]

    # Deduplicate by chapter name and sort by page_start
    seen: set[str] = set()
    deduped: list[dict] = []
    for entry in toc:
        key = entry["chapter"]
        if key not in seen:
            seen.add(key)
            deduped.append(entry)
    deduped.sort(key=lambda x: x["page_start"])

    # Fill in page_end from next entry
    for i in range(len(deduped)):
        if i + 1 < len(deduped):
            deduped[i]["page_end"] = deduped[i + 1]["page_start"] - 1
        else:
            deduped[i]["page_end"] = total_pages

    return deduped


def match_chapters_by_keywords(toc: list[dict], keywords: str) -> list[dict]:
    """
    Match TOC chapters against comma-separated keywords.
    Returns chapters where any keyword is found in the chapter title.
    Only includes chapters with page_span >= MONOGRAPH_KEYWORD_MATCH_MIN_PAGES.
    """
    if not toc or not keywords:
        return []

    # Normalize keywords: treat hyphen as space for flexible matching
    kw_list = [
        k.strip().lower().replace("-", " ")
        for k in keywords.split(",") if k.strip()
    ]
    matched: list[dict] = []
    for entry in toc:
        chapter_lower = entry["chapter"].lower().replace("-", " ")
        for kw in kw_list:
            if kw in chapter_lower:
                page_span = entry["page_end"] - entry["page_start"] + 1
                if page_span >= MONOGRAPH_KEYWORD_MATCH_MIN_PAGES:
                    matched.append(entry)
                break
    return matched


# ---------------------------------------------------------------------------
# Enhanced metadata fallback with layout awareness
# ---------------------------------------------------------------------------


def extract_meta_fallback_from_text_enhanced(
    text: str, words_data: list | None = None
) -> dict:
    """
    Enhanced fallback that optionally uses pdfplumber word-level data
    (with font sizes) to better identify title and author blocks.

    words_data: list of dicts from pdfplumber page.extract_words()
        each with keys: text, top, fontname, size (if available)
    """
    result = {"title": "", "author": "", "year": ""}
    if not text:
        return result

    # Strip CNKI watermarks first
    text = strip_cnki_watermarks(text)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return result

    # --- Title extraction ---
    # If we have words_data with font sizes, use font-size heuristic
    if words_data:
        try:
            sizes = [
                float(w.get("size", 0)) for w in words_data if w.get("size")
            ]
            if sizes:
                max_size = max(sizes)
                if max_size >= PDFPLUMBER_MIN_FONT_FOR_TITLE:
                    # Collect words with font size close to max
                    title_words = [
                        w["text"] for w in words_data
                        if w.get("size")
                        and max_size - float(w["size"]) <= PDFPLUMBER_FONT_DIFF_THRESHOLD
                    ]
                    candidate = " ".join(title_words).strip()
                    if (
                        META_TITLE_MIN_LEN <= len(candidate.replace(" ", ""))
                        <= META_TITLE_MAX_LEN
                    ):
                        result["title"] = candidate
        except Exception:
            pass

    # Fallback to line-based heuristic if no title from layout
    if not result["title"]:
        candidates = []
        for ln in lines[:META_TITLE_CANDIDATE_LINES]:
            ln_stripped = ln.replace(" ", "").replace("\t", "")
            if (
                META_TITLE_MIN_LEN <= len(ln_stripped) <= META_TITLE_MAX_LEN
                and not ln_stripped.isdigit()
            ):
                candidates.append(ln)
        if candidates:
            result["title"] = max(candidates, key=len)

    # --- Author extraction ---
    author_patterns = [
        r"(?<![a-zA-Z])(?:作者|Author|Authors)\b[:： \t]+([^\n]{2,80})",
        r"(?<![a-zA-Z])(?:著者|Writer|by)\b[:： \t]+([^\n]{2,80})",
        r"(?:通讯作者|Corresponding author)[:： \t]*([^\n]{2,80})",
        r"(?:\*)\s*([^\n]{2,80})\s*\n\s*(?:通信作者|通讯作者|corresponding)",
        # APA citation author extraction from "How to Cite this Article" section
        r"(?:How\s+to\s+Cite\s+this\s+Article|citation)[:：\s]*\n?\s*([A-Za-z\s,.\-\u0026]+?)\s*\(\d{4}\)",
    ]
    for pat in author_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["author"] = re.sub(r"\s+", " ", m.group(1)).strip()
            break

    # Filter known garbage author values from fallback extraction
    if result["author"].lower() in (
        "how to cite this article",
        "cnki",
        "cnki数据库",
        "知网",
        "author",
        "authors",
    ):
        result["author"] = ""

    # --- Year extraction ---
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        result["year"] = year_match.group(0)

    return result
