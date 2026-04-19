"""Shared helper functions used across extractors and report generation."""

import difflib
import hashlib
import logging
import math
import re
from pathlib import Path

from .constants import _COMPOUND_SURNAMES


# ---------------------------------------------------------------------------
# String / text utilities
# ---------------------------------------------------------------------------


def safe_truncate(text: str, limit: int = 2000) -> str:
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


def estimate_pages_from_chars(char_count: int, chars_per_page: int = 500) -> int:
    """Estimate page count for text-based files where true pagination is unknown."""
    return max(1, math.ceil(char_count / chars_per_page))


def get_pdf_read_pages(total_pages: int, max_pages: int = 0) -> list[int]:
    """
    Decide which pages to read based on document length.

    - Short docs (<= 50 pages): read all pages.
    - Long docs (> 50 pages): read first 15 + last 5 pages.
    - max_pages > 0 overrides the heuristic.
    """
    if max_pages > 0:
        return list(range(min(total_pages, max_pages)))
    if total_pages <= 50:
        return list(range(total_pages))
    pages = list(range(min(15, total_pages)))
    pages.extend(range(max(0, total_pages - 5), total_pages))
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
    if total_chars > 8000:
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
    empty_samples = sum(1 for t in sampled if len(t.strip()) < 25)
    if len(sampled) >= 2 and empty_samples / len(sampled) >= 0.66:
        return True

    density = total_chars / read_count if read_count > 0 else 0
    if density < 12 and read_count > 3:
        return True

    if total_chars < 50:
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

    for line in text.splitlines()[:15]:
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
