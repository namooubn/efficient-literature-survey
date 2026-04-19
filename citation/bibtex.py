"""BibTeX export generator."""

import re

from .engine import _normalize_author


def _guess_bibtex_type(metadata: dict) -> str:
    """Map metadata to a BibTeX entry type."""
    fmt = metadata.get("format", "").lower()
    pages = metadata.get("pages", 0)
    journal = metadata.get("journal", "")
    if journal:
        return "article"
    if pages > 200 or fmt == "epub":
        return "book"
    return "misc"


def _bibtex_escape(s: str) -> str:
    return s.replace("{", "\\{").replace("}", "\\}").replace("&", "\\&")


def generate_bibtex(results: list[dict]) -> str:
    """Generate a .bib file from extracted metadata."""
    lines: list[str] = []
    for idx, r in enumerate(results, start=1):
        entry_type = _guess_bibtex_type(r)
        citekey = re.sub(
            r"[^a-zA-Z0-9]",
            "",
            (r.get("author_from_meta") or "Unknown").split(",")[0].split(" ")[0],
        )
        citekey = citekey or "Unknown"
        year = r.get("year", "")
        citekey = f"{citekey}{year}{idx}"
        lines.append(f"@{entry_type}{{{citekey},")
        lines.append(
            f"  title = {{{_bibtex_escape(r.get('title_from_meta', r['filename']))}}},"
        )
        authors = _normalize_author(r.get("author_from_meta", ""))
        if authors:
            lines.append(f"  author = {{{_bibtex_escape(' and '.join(authors))}}},")
        if year:
            lines.append(f"  year = {{{year}}},")
        if r.get("journal"):
            lines.append(f"  journal = {{{_bibtex_escape(r['journal'])}}},")
        if r.get("publisher"):
            lines.append(f"  publisher = {{{_bibtex_escape(r['publisher'])}}},")
        if r.get("volume"):
            lines.append(f"  volume = {{{r['volume']}}},")
        if r.get("issue"):
            lines.append(f"  number = {{{r['issue']}}},")
        if r.get("page_range"):
            lines.append(f"  pages = {{{r['page_range']}}},")
        if r.get("doi"):
            lines.append(f"  doi = {{{r['doi']}}},")
        if not r.get("journal") and not r.get("publisher"):
            lines.append("  note = {文献信息不完整，请手动补全},")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)
