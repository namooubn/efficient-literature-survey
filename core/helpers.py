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
    DOCX_SAMPLE_CHARS,
    DOCX_TABLE_SAMPLE_COUNT,
    EPUB_BIB_SAMPLE_CHARS,
    EPUB_DOCUMENT_SAMPLE_COUNT,
    LONG_DOC_HEAD_PAGES,
    LONG_DOC_TAIL_PAGES,
    META_TITLE_CANDIDATE_LINES,
    META_TITLE_MAX_LEN,
    META_TITLE_MIN_LEN,
    PDF_FALLBACK_TEXT_CHARS,
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
        r"(?:作者|Author|Authors)[:：\s]+(.{2,80})",
        r"(?:著者|Writer|by)[:：\s]+(.{2,80})",
    ]
    for pat in author_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["author"] = m.group(1).strip()
            break

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
