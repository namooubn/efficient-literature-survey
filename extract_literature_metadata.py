#!/usr/bin/env python3
"""
Batch-extract metadata from a folder of literature files (PDF, DOCX, TXT, MD, EPUB).
Outputs a structured report with title, author, page/word count, text volume,
and scanned-image detection (PDF only).

Usage:
    python extract_literature_metadata.py /path/to/literature/folder

Dependencies:
    pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
"""

import os
import sys
import json
import math
import re
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_pages_from_chars(char_count: int, chars_per_page: int = 500) -> int:
    """Estimate page count for text-based files where true pagination is unknown."""
    return max(1, math.ceil(char_count / chars_per_page))


def _safe_truncate(text: str, limit: int = 2000) -> str:
    return text[:limit] if text else ""


def _smart_word_count(text: str) -> int:
    """
    Estimate word count for mixed Chinese/English text.
    Chinese: count characters (excluding whitespace and punctuation).
    English: count space-separated tokens.
    """
    if not text:
        return 0
    # Chinese characters (CJK Unified Ideographs + extensions)
    cn_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002b73f]', text)
    # English words: tokens with at least one letter
    en_tokens = re.findall(r'\b[a-zA-Z]+\b', text)
    # For non-CJK languages, also count numeric tokens and other space-separated words
    # Pure CJK text should not count space splits, so only count en_tokens + cn_chars
    # If text has very few CJK chars, supplement with simple split to catch non-English e.g. German, French
    if len(cn_chars) == 0:
        return len(text.split())
    return len(cn_chars) + len(en_tokens)


def _detect_scanned_pdf(page_texts: list, total_pages: int) -> bool:
    """
    Multi-page sampling heuristic for scanned/image-based PDF detection.
    Samples pages at beginning, middle, and end to avoid false positives
    from cover pages or front matter that are image-only.
    """
    if total_pages <= 1 or not page_texts:
        return False

    total_chars = sum(len(t) for t in page_texts)

    # Fast path: very high text volume = definitely not scanned
    if total_chars > 8000:
        return False

    # Sample pages at beginning, middle, and end
    indices = [0]
    if total_pages > 3:
        mid = min(total_pages // 2, len(page_texts) - 1)
        if mid > 0:
            indices.append(mid)
    if total_pages > 5:
        end = min(total_pages - 1, len(page_texts) - 1)
        if end not in indices:
            indices.append(end)

    sampled = [page_texts[i] for i in indices if i < len(page_texts)]
    empty_samples = sum(1 for t in sampled if len(t.strip()) < 25)

    # If majority of sampled pages are nearly empty, likely scanned
    if len(sampled) >= 2 and empty_samples / len(sampled) >= 0.66:
        return True

    # Fallback: very low text density across all sampled pages
    density = total_chars / total_pages if total_pages > 0 else 0
    if density < 12 and total_pages > 3:
        return True

    # Extra fallback: original single-threshold for short docs
    if total_chars < 50:
        return True

    return False


def _get_pdf_read_pages(total_pages: int, max_pages: int = 0) -> list[int]:
    """
    Decide which pages to read based on document length.

    - Short docs (<= 50 pages): read all pages.
    - Long docs (> 50 pages): read first 15 + last 5 pages to avoid
      getting stuck in front-matter (cover, TOC, preface) while still
      sampling the body and conclusion.
    - max_pages > 0 overrides the heuristic and caps total pages read.
    """
    if max_pages > 0:
        return list(range(min(total_pages, max_pages)))
    if total_pages <= 50:
        return list(range(total_pages))
    # Monograph strategy
    pages = list(range(min(15, total_pages)))
    pages.extend(range(max(0, total_pages - 5), total_pages))
    return sorted(set(pages))


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

import difflib  # noqa: E402


def _find_duplicates(results: list[dict], threshold: float = 0.80) -> dict[str, list[str]]:
    """
    Detect duplicate references by title similarity (SequenceMatcher).
    Returns {filename: [list of duplicate filenames]}.
    """
    dups: dict[str, list[str]] = {}
    n = len(results)
    for i in range(n):
        title_i = (results[i].get("title_from_meta") or results[i]["filename"]).lower().strip()
        if not title_i:
            continue
        for j in range(i + 1, n):
            title_j = (results[j].get("title_from_meta") or results[j]["filename"]).lower().strip()
            if not title_j:
                continue
            ratio = difflib.SequenceMatcher(None, title_i, title_j).ratio()
            if ratio >= threshold:
                fi = results[i]["filename"]
                fj = results[j]["filename"]
                dups.setdefault(fi, []).append(f"{fj} (相似度 {ratio:.0%})")
                dups.setdefault(fj, []).append(f"{fi} (相似度 {ratio:.0%})")
    # deduplicate values
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
# Citation generation
# ---------------------------------------------------------------------------

def _normalize_author(author_raw: str) -> list[str]:
    """Split author string into individual names."""
    if not author_raw:
        return []
    # Split on common separators
    parts = re.split(r"[,;，；/&]", author_raw)
    return [p.strip() for p in parts if p.strip()]


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
    fmt = metadata.get("format", "").upper()

    if style == "gb7714":
        if not authors:
            author_str = "佚名"
        elif len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]}, {authors[1]}"
        elif len(authors) == 3:
            author_str = f"{authors[0]}, {authors[1]}, {authors[2]}"
        else:
            author_str = f"{authors[0]} 等"
        return f"[{author_str}]. {title}[{fmt}]."

    if style == "apa":
        if not authors:
            author_str = "Anonymous"
        elif len(authors) == 1:
            author_str = _apa_name(authors[0])
        elif len(authors) == 2:
            author_str = f"{_apa_name(authors[0])} & {_apa_name(authors[1])}"
        else:
            author_str = f"{_apa_name(authors[0])} et al."
        return f"{author_str} {title}."

    if style == "mla":
        if not authors:
            author_str = "Anonymous"
        else:
            author_str = _mla_name(authors[0])
            if len(authors) > 1:
                author_str += f", et al."
        return f'"{title}." {author_str}.'

    # default numbered
    return f"[{metadata.get('_citation_number', '')}] {title}"


def _apa_name(name: str) -> str:
    """Convert 'Zhang San' or 'San Zhang' to APA-style 'Zhang, S.' heuristic."""
    parts = name.split()
    if len(parts) >= 2 and len(parts[-1]) == 1:
        # Likely 'San Z.' format
        return f"{parts[-1]}, {''.join(p[0] + '.' for p in parts[:-1])}"
    if len(parts) >= 2:
        return f"{parts[-1]}, {parts[0][0]}."
    return name


def _mla_name(name: str) -> str:
    """Convert name to MLA-style 'Last, First' heuristic."""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {parts[0]}"
    return name


# ---------------------------------------------------------------------------
# Incremental / caching helpers
# ---------------------------------------------------------------------------

def _file_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file for cache invalidation."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def _load_cache(cache_path: Path) -> dict:
    """Load cached extraction results keyed by filename -> {sha256, result}."""
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "files" in data:
            return data["files"]
    except Exception:
        pass
    return {}


def _save_cache(cache_path: Path, cache_data: dict) -> None:
    """Save cache with version and timestamp metadata."""
    payload = {
        "version": 1,
        "generated_at": datetime.now().isoformat(),
        "files": cache_data,
    }
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [WARN] 缓存保存失败：{e}")


# ---------------------------------------------------------------------------
# Interactive CLI helpers
# ---------------------------------------------------------------------------

def _prompt_path() -> Path:
    """Prompt user for a folder path with validation."""
    while True:
        raw = input("\n请输入文献文件夹路径（例如 /home/alice/references）：\n> ").strip()
        p = Path(raw).expanduser()
        if not p.exists():
            print(f"  路径不存在：{p}")
            continue
        if not p.is_dir():
            print(f"  这不是一个文件夹：{p}")
            continue
        return p


def _interactive_prompt_unsupported(skipped: list, supported_exts: set) -> None:
    """Explain why files were skipped in a user-friendly way."""
    if not skipped:
        return
    print(f"\n  检测到 {len(skipped)} 个不支持的文件：")
    for name in skipped:
        ext = Path(name).suffix.lower()
        print(f"    - {name} ({ext or '无后缀'})")
    print(f"  当前支持的格式：{', '.join(sorted(supported_exts))}")


# ---------------------------------------------------------------------------
# Extractors by format
# ---------------------------------------------------------------------------

def extract_pdf(pdf_path: str, max_pages: int = 0) -> dict:
    """Extract metadata and text sample from a single PDF."""
    result = {
        "filename": os.path.basename(pdf_path),
        "format": "pdf",
        "pages": 0,
        "word_count": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
        "note": "",
    }

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        result["pages"] = len(reader.pages)
        meta = reader.metadata
        if meta:
            result["author_from_meta"] = str(meta.get("/Author", ""))
            result["title_from_meta"] = str(meta.get("/Title", ""))

        read_pages = _get_pdf_read_pages(result["pages"], max_pages)
        page_texts: list[str] = [""] * result["pages"]
        total_text = ""
        for i in read_pages:
            try:
                page = reader.pages[i]
                txt = page.extract_text() or ""
                page_texts[i] = txt
                total_text += txt
                if i == 0:
                    result["first_page_text"] = _safe_truncate(txt)
            except Exception as e:
                if not result["note"]:
                    result["note"] = ""
                result["note"] += f"Page {i} extract error: {type(e).__name__}; "
        result["text_chars"] = len(total_text)
    except Exception as e:
        page_texts = []
        if not result["note"]:
            result["note"] = ""
        result["note"] += f"PyPDF2 error: {type(e).__name__}: {e}; "

    # Fallback to pdfplumber if PyPDF2 extracted very little text
    if result["text_chars"] < 500 and result["pages"] > 0:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                result["pages"] = len(pdf.pages)
                read_pages = _get_pdf_read_pages(result["pages"], max_pages)
                page_texts = [""] * result["pages"]
                total_text = ""
                for i in read_pages:
                    txt = pdf.pages[i].extract_text() or ""
                    page_texts[i] = txt
                    total_text += txt
                    if i == 0:
                        result["first_page_text"] = _safe_truncate(txt)
                result["text_chars"] = len(total_text)
        except Exception as e:
            if not result["note"]:
                result["note"] = ""
            result["note"] += f"pdfplumber fallback error: {type(e).__name__}: {e}; "

    result["word_count"] = _smart_word_count(total_text) if result["text_chars"] > 0 else 0

    # Scanned-image detection heuristic (PDF only) — multi-page sampling
    result["is_scanned"] = _detect_scanned_pdf(page_texts, result["pages"])

    return result


def extract_docx(docx_path: str) -> dict:
    """Extract metadata and text sample from a DOCX file."""
    result = {
        "filename": os.path.basename(docx_path),
        "format": "docx",
        "pages": 0,
        "word_count": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
        "note": "",
    }

    try:
        from docx import Document
        doc = Document(docx_path)

        core_props = doc.core_properties
        result["author_from_meta"] = core_props.author or ""
        result["title_from_meta"] = core_props.title or ""

        paragraphs = doc.paragraphs[:30]
        full_text = "\n".join(p.text for p in paragraphs)
        result["text_chars"] = len(full_text)
        result["word_count"] = _smart_word_count(full_text)
        result["first_page_text"] = _safe_truncate(full_text)
        result["pages"] = _estimate_pages_from_chars(result["text_chars"])

        table_texts = []
        for table in doc.tables[:5]:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        table_texts.append(cell.text.strip())
        if table_texts:
            table_full = "\n".join(table_texts)
            result["word_count"] += _smart_word_count(table_full)

    except Exception as e:
        result["note"] = f"DOCX extraction error: {e}"

    return result


def extract_txt(txt_path: str) -> dict:
    """Extract text sample from a plain-text file (TXT or MD)."""
    result = {
        "filename": os.path.basename(txt_path),
        "format": Path(txt_path).suffix.lower().lstrip("."),
        "pages": 0,
        "word_count": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
        "note": "",
    }

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
    result["word_count"] = _smart_word_count(content)
    result["first_page_text"] = _safe_truncate(content)
    result["pages"] = _estimate_pages_from_chars(result["text_chars"])

    return result


def extract_epub(epub_path: str) -> dict:
    """Extract metadata and text sample from an EPUB file."""
    result = {
        "filename": os.path.basename(epub_path),
        "format": "epub",
        "pages": 0,
        "word_count": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
        "note": "",
    }

    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

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
                if count >= 10:
                    break

        full_text = "\n".join(all_texts)
        result["text_chars"] = len(full_text)
        result["word_count"] = _smart_word_count(full_text)
        result["first_page_text"] = _safe_truncate(full_text)
        result["pages"] = _estimate_pages_from_chars(result["text_chars"])

    except ImportError:
        result["note"] = "Missing dependency: pip install ebooklib beautifulsoup4"
    except Exception as e:
        result["note"] = f"EPUB extraction error: {e}"

    return result


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

SUPPORTED_EXTS = {".pdf", ".docx", ".txt", ".md", ".epub"}
CAJ_EXT = {".caj"}


def extract_info(file_path: str, max_pages: int = 0) -> dict:
    """Dispatch to the correct extractor based on file extension."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return extract_pdf(file_path, max_pages=max_pages)
    if ext == ".docx":
        return extract_docx(file_path)
    if ext in (".txt", ".md"):
        return extract_txt(file_path)
    if ext == ".epub":
        return extract_epub(file_path)

    if ext in CAJ_EXT:
        return {
            "filename": os.path.basename(file_path),
            "format": "caj",
            "pages": 0,
            "word_count": 0,
            "text_chars": 0,
            "first_page_text": "",
            "is_scanned": False,
            "author_from_meta": "",
            "title_from_meta": "",
            "note": "CAJ format is not directly supported. Please convert to PDF using CAJViewer or caj2pdf first.",
        }

    return {
        "filename": os.path.basename(file_path),
        "format": ext.lstrip("."),
        "pages": 0,
        "word_count": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
        "note": f"Unsupported file format: {ext}",
    }


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------

def generate_markdown_report(
    results: list,
    lit_dir: Path,
    skipped: list,
    duplicates: dict | None = None,
    citation_style: str = "gb7714",
) -> str:
    """Generate a human-readable Markdown report from extraction results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scanned = [r for r in results if r["is_scanned"]]
    by_format = {}
    for r in results:
        fmt = r["format"]
        by_format.setdefault(fmt, []).append(r)

    total_pages = sum(r["pages"] for r in results)
    total_words = sum(r["word_count"] for r in results)
    dup_count = len(duplicates) if duplicates else 0

    lines = [
        "# 文献提取报告\n",
        f"**生成时间**：{now}",
        f"**文献目录**：`{lit_dir}`\n",
        "## 汇总统计\n",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总文献数 | {len(results)} 篇 |",
        f"| 总页数（含估算） | {total_pages} 页 |",
        f"| 总字数（含估算） | {total_words} 字 |",
        f"| 扫描件（需 OCR） | {len(scanned)} 篇 |",
        f"| 疑似重复 | {dup_count} 篇 |",
        f"| 格式分布 | {', '.join(f'{k}: {len(v)} 篇' for k, v in by_format.items())} |",
        "",
    ]

    if scanned:
        lines.extend([
            "## ⚠️ 扫描件清单（需 OCR 处理）\n",
            "| 文件名 | 页数 | 状态 |",
            "|--------|------|------|",
        ])
        for r in scanned:
            lines.append(f"| {r['filename']} | {r['pages']} | 扫描 PDF，无法直接提取全文 |")
        lines.append("")

    if duplicates:
        lines.extend([
            "## 🔁 疑似重复文献\n",
            "| 文件名 | 疑似重复对象 |",
            "|--------|-------------|",
        ])
        for fname, dlist in sorted(duplicates.items()):
            lines.append(f"| {fname} | {'; '.join(dlist)} |")
        lines.append("")

    lines.extend([
        "## 文献详情（按文件名排序）\n",
        "| 序号 | 文件名 | 格式 | 页数 | 字数 | 作者 | 标题 | 备注 |",
        "|------|--------|------|------|------|------|------|------|",
    ])
    for r in sorted(results, key=lambda x: x["filename"].lower()):
        author = r["author_from_meta"] or "—"
        title = r["title_from_meta"] or "—"
        note = r["note"] or "—"
        if len(title) > 40:
            title = title[:37] + "..."
        if len(author) > 30:
            author = author[:27] + "..."
        num = r.get("_citation_number", "")
        lines.append(
            f"| {num} | {r['filename']} | {r['format']} | {r['pages']} | {r['word_count']} | "
            f"{author} | {title} | {note} |"
        )
    lines.append("")

    # Citation list
    lines.extend([
        f"## 参考文献列表（{citation_style.upper()} 格式）\n",
    ])
    for r in sorted(results, key=lambda x: x.get("_citation_number", 0)):
        citation = r.get("citation", "")
        if citation:
            lines.append(f"{r.get('_citation_number', '')}. {citation}")
    lines.append("")

    if skipped:
        lines.extend([
            "## 跳过的文件\n",
            "| 文件名 | 原因 |",
            "|--------|------|",
        ])
        for name in skipped:
            ext = Path(name).suffix.lower()
            reason = f"不支持的格式 {ext}" if ext else "无文件后缀"
            lines.append(f"| {name} | {reason} |")
        lines.append("")

    lines.append("---\n*由 efficient-literature-survey 自动生成*\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    # Help
    if any(a in args for a in ("-h", "--help")):
        print(__doc__)
        sys.exit(0)

    # Parse optional flags
    max_pages = 0
    citation_style = "gb7714"
    i = 0
    while i < len(args):
        if args[i] in ("--max-pages", "-m") and i + 1 < len(args):
            try:
                max_pages = int(args[i + 1])
                if max_pages < 0:
                    max_pages = 0
            except ValueError:
                pass
            i += 2
        elif args[i] in ("--citation-style", "-c") and i + 1 < len(args):
            citation_style = args[i + 1].lower()
            i += 2
        else:
            i += 1

    # Determine folder path (first non-flag positional arg)
    pos_args = [a for a in args if not a.startswith("-")]
    if not pos_args:
        print("用法：python extract_literature_metadata.py <文献文件夹路径>")
        print("  [--max-pages N] [--citation-style gb7714|apa|mla|numbered]")
        print("未提供路径，进入交互模式...")
        lit_dir = _prompt_path()
    else:
        lit_dir = Path(pos_args[0]).expanduser()
        if not lit_dir.exists():
            print(f"路径不存在：{lit_dir}")
            print("进入交互模式...")
            lit_dir = _prompt_path()
        elif not lit_dir.is_dir():
            print(f"这不是一个文件夹：{lit_dir}")
            print("进入交互模式...")
            lit_dir = _prompt_path()

    all_files = sorted([f for f in lit_dir.iterdir() if f.is_file()])
    lit_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTS | CAJ_EXT]
    skipped = [f.name for f in all_files if f.suffix.lower() not in SUPPORTED_EXTS | CAJ_EXT]

    if not lit_files:
        print(f"\n在 {lit_dir} 中未找到支持的文献文件。")
        _interactive_prompt_unsupported(skipped, SUPPORTED_EXTS | CAJ_EXT)
        sys.exit(1)

    print(f"\n找到 {len(lit_files)} 篇文献，开始处理...")
    if skipped:
        print(f"跳过 {len(skipped)} 个不支持的文件")

    # Load cache for incremental extraction
    cache_path = lit_dir / "_literature_cache.json"
    cache = _load_cache(cache_path)
    results: list[dict] = []
    to_extract: list[Path] = []
    cache_hits = 0

    for lf in lit_files:
        file_hash = _file_sha256(str(lf))
        cached = cache.get(lf.name)
        if cached and cached.get("sha256") == file_hash and cached.get("result"):
            results.append(cached["result"])
            cache_hits += 1
        else:
            to_extract.append(lf)

    if cache_hits:
        print(f"  缓存命中 {cache_hits} 篇（文件未变更），跳过重新提取")
    if to_extract:
        print(f"  需要重新提取 {len(to_extract)} 篇")

    # Concurrent extraction with ThreadPoolExecutor (I/O-bound: reading files)
    if to_extract:
        max_workers = min(4, len(to_extract)) if to_extract else 1
        print(f"使用 {max_workers} 线程并发处理...")

        def _extract_with_log(path: str) -> dict:
            info = extract_info(path, max_pages=max_pages)
            print(f"  [DONE] {info['format']:5} P{info['pages']:3} WC{info['word_count']:6} | {info['filename'][:45]}")
            return info

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            extracted = list(executor.map(_extract_with_log, (str(lf) for lf in to_extract)))
        results.extend(extracted)

    # Update cache with fresh results
    new_cache: dict[str, dict] = {}
    for r in results:
        fname = r.get("filename", "")
        for lf in lit_files:
            if lf.name == fname:
                new_cache[fname] = {
                    "sha256": _file_sha256(str(lf)),
                    "result": r,
                }
                break
    _save_cache(cache_path, new_cache)

    # Duplicate detection
    duplicates = _find_duplicates(results)
    if duplicates:
        print(f"\n  检测到 {len(duplicates)} 篇疑似重复文献")
        for fname, dlist in duplicates.items():
            print(f"    - {fname} ↔ {', '.join(dlist)}")

    # Generate citations for each result
    for idx, r in enumerate(results, start=1):
        r["_citation_number"] = idx
        r["citation"] = generate_citation(r, citation_style)

    # Console summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for r in results:
        status = "⚠️ SCANNED" if r["is_scanned"] else "  OK     "
        dup_mark = " [DUP]" if r["filename"] in duplicates else ""
        note = f" | NOTE: {r['note']}" if r["note"] else ""
        print(
            f"[{status}] {r['format']:5} P{r['pages']:3} WC{r['word_count']:6} | "
            f"{r['filename'][:45]}{dup_mark}{note}"
        )

    # JSON output
    output_payload = {
        "citation_style": citation_style,
        "max_pages": max_pages,
        "duplicates": duplicates,
        "results": results,
    }
    output_path = lit_dir / "_literature_extraction.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 结果已保存：{output_path}")

    # Markdown report output
    md_path = lit_dir / "_literature_report.md"
    md_content = generate_markdown_report(results, lit_dir, skipped, duplicates, citation_style)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown 报告已保存：{md_path}")


if __name__ == "__main__":
    main()
