"""Citation format engine supporting GB/T 7714, APA, MLA, and numbered styles."""

import re

from core.config import MONOGRAPH_PAGE_THRESHOLD
from core.helpers import split_chinese_name


def _normalize_author(author_raw: str) -> list[str]:
    """Split author string into individual names."""
    if not author_raw:
        return []
    parts = re.split(r"[,;，；/&]", author_raw)
    return [p.strip() for p in parts if p.strip()]


def _guess_doc_type(metadata: dict) -> str:
    """Guess document type code for GB/T 7714."""
    fmt = metadata.get("format", "").lower()
    pages = metadata.get("pages", 0)
    if pages > MONOGRAPH_PAGE_THRESHOLD:
        return "M"
    if fmt == "epub":
        return "M"
    return "J"


def _apa_name(name: str) -> str:
    """Convert name to APA-style 'Zhang, S.' heuristic."""
    name = name.strip()
    if any("\u4e00" <= c <= "\u9fff" for c in name):
        surname, given = split_chinese_name(name)
        if surname:
            given_initials = "".join(f"{g[0]}." for g in given if g)
            return f"{surname}, {given_initials}"
    parts = name.split()
    if len(parts) >= 2 and len(parts[-1]) == 1:
        return f"{parts[-1]}, {''.join(p[0] + '.' for p in parts[:-1])}"
    if len(parts) >= 2:
        return f"{parts[-1]}, {parts[0][0]}."
    return name


def _mla_name(name: str) -> str:
    """Convert name to MLA-style 'Last, First' heuristic."""
    name = name.strip()
    if any("\u4e00" <= c <= "\u9fff" for c in name):
        surname, given = split_chinese_name(name)
        if surname:
            return f"{surname}, {given}"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {parts[0]}"
    return name


def generate_citation(metadata: dict, style: str = "numbered") -> str:
    """
    Generate a formatted citation string from metadata.

    Supported styles:
      - "gb7714"   : GB/T 7714 Chinese standard
      - "apa"      : APA 7th edition (simplified)
      - "mla"      : MLA 9th edition (simplified)
      - "numbered" : [N] numeric citation
    """
    title = (metadata.get("title_from_meta") or metadata.get("filename", "")).strip()
    author_raw = metadata.get("author_from_meta", "").strip()
    authors = _normalize_author(author_raw)
    year = metadata.get("year", "")
    journal = metadata.get("journal", "")
    publisher = metadata.get("publisher", "")
    volume = metadata.get("volume", "")
    issue = metadata.get("issue", "")
    page_range = metadata.get("page_range", "")
    doi = metadata.get("doi", "")
    doc_type = _guess_doc_type(metadata)

    incomplete = False
    if not year or (not journal and not publisher and doc_type == "J"):
        incomplete = True

    def _author_str_gb(authors_list: list[str]) -> str:
        if not authors_list:
            return "佚名"
        if len(authors_list) == 1:
            return authors_list[0]
        if len(authors_list) == 2:
            return f"{authors_list[0]}, {authors_list[1]}"
        if len(authors_list) == 3:
            return f"{authors_list[0]}, {authors_list[1]}, {authors_list[2]}"
        return f"{authors_list[0]} 等"

    def _author_str_apa(authors_list: list[str]) -> str:
        if not authors_list:
            return "Anonymous"
        if len(authors_list) == 1:
            return _apa_name(authors_list[0])
        if len(authors_list) == 2:
            return f"{_apa_name(authors_list[0])} & {_apa_name(authors_list[1])}"
        return f"{_apa_name(authors_list[0])} et al."

    def _author_str_mla(authors_list: list[str]) -> str:
        if not authors_list:
            return "Anonymous"
        first = _mla_name(authors_list[0])
        if len(authors_list) > 1:
            return f"{first}, et al."
        return first

    if style == "gb7714":
        author_str = _author_str_gb(authors)
        parts = [f"[{author_str}]. {title}[{doc_type}]"]
        if publisher:
            parts.append(publisher)
        elif journal:
            parts.append(journal)
        if year:
            parts.append(year)
        if volume:
            vi = f"{volume}"
            if issue:
                vi += f"({issue})"
            parts.append(vi)
        if page_range:
            parts.append(f": {page_range}")
        if doi:
            parts.append(f". DOI:{doi}")
        citation = ". ".join(parts)
        if citation.endswith("."):
            citation = citation[:-1]
        citation += "."

    elif style == "apa":
        author_str = _author_str_apa(authors)
        year_part = f" ({year})" if year else ""
        citation = f"{author_str}{year_part}. {title}."
        if journal:
            citation += f" *{journal}*"
            if volume:
                citation += f", *{volume}*"
                if issue:
                    citation += f"({issue})"
            if page_range:
                citation += f", {page_range}"
            citation += "."
        elif publisher:
            citation += f" {publisher}."
        if doi:
            citation += f" https://doi.org/{doi}"

    elif style == "mla":
        author_str = _author_str_mla(authors)
        citation = f'"{title}." '
        if journal:
            citation += f"*{journal}*, "
            if volume:
                citation += f"vol. {volume}, "
            if issue:
                citation += f"no. {issue}, "
        if year:
            citation += f"{year}, "
        if page_range:
            citation += f"pp. {page_range}."
        else:
            citation = citation.rstrip(", ") + "."
        citation = f"{author_str}. {citation}"

    else:  # numbered
        num = metadata.get("_citation_number", "")
        prefix = f"[{num}] " if num else ""
        parts: list[str] = []
        if authors:
            parts.append(authors[0] + (" 等" if len(authors) > 1 else ""))
        parts.append(title)
        if journal:
            parts.append(f"《{journal}》")
        elif publisher:
            parts.append(publisher)
        if year:
            parts.append(year)
        citation = prefix + ", ".join([p for p in parts if p])
        citation += "."

    if incomplete:
        citation += " 〔文献信息不完整，请手动补全〕"
    return citation
