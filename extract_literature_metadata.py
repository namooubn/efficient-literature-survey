#!/usr/bin/env python3
"""
Batch-extract metadata from a folder of literature files (PDF, DOCX, TXT, MD, EPUB).
Outputs a structured report with title, author, year, page/word count, text volume,
scanned-image detection (PDF only), and formatted citations.

Usage:
    python extract_literature_metadata.py /path/to/literature/folder

Dependencies:
    pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
"""

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Ensure sub-package imports resolve when run as a standalone script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from cache.manager import file_sha256, load_cache, save_cache
from citation.engine import generate_citation
from citation.bibtex import generate_bibtex
from core.constants import SUPPORTED_EXTS, CAJ_EXT
from core.helpers import find_duplicates
from core.logging_config import setup_logging
from extractors import extract_pdf, extract_docx, extract_txt, extract_epub
from report.generator import generate_markdown_report


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


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
        from extractors.base import make_result_template
        result = make_result_template(file_path)
        result["format"] = "caj"
        result["note"] = (
            "CAJ format is not directly supported. "
            "Please convert to PDF using CAJViewer or caj2pdf first."
        )
        return result

    from extractors.base import make_result_template
    result = make_result_template(file_path)
    result["note"] = f"Unsupported file format: {ext}"
    return result


# ---------------------------------------------------------------------------
# Interactive CLI helpers
# ---------------------------------------------------------------------------


def _prompt_path() -> Path:
    """Prompt user for a folder path with validation."""
    while True:
        raw = input(
            "\n请输入文献文件夹路径（例如 /home/alice/references）：\n> "
        ).strip()
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
    output_dir: Path | None = None
    bibtex = False
    verbose = False
    quiet = False
    recursive = True
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
        elif args[i] in ("--output-dir", "-o") and i + 1 < len(args):
            output_dir = Path(args[i + 1]).expanduser()
            i += 2
        elif args[i] in ("--bibtex", "-b"):
            bibtex = True
            i += 1
        elif args[i] in ("--verbose", "-v"):
            verbose = True
            i += 1
        elif args[i] in ("--quiet", "-q"):
            quiet = True
            i += 1
        elif args[i] in ("--no-recursive",):
            recursive = False
            i += 1
        else:
            i += 1

    setup_logging(verbose=verbose, quiet=quiet)

    # Determine folder path (first non-flag positional arg)
    pos_args = [a for a in args if not a.startswith("-")]
    if not pos_args:
        print("用法：python extract_literature_metadata.py <文献文件夹路径>")
        print("  [--max-pages N] [--citation-style gb7714|apa|mla|numbered]")
        print("  [--output-dir PATH] [--bibtex] [--verbose] [--quiet] [--no-recursive]")
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

    # Collect files (recursive by default)
    if recursive:
        all_files = sorted([f for f in lit_dir.rglob("*") if f.is_file()])
    else:
        all_files = sorted([f for f in lit_dir.iterdir() if f.is_file()])

    lit_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTS | CAJ_EXT]
    skipped = [f.name for f in all_files if f.suffix.lower() not in SUPPORTED_EXTS | CAJ_EXT]

    if not lit_files:
        logging.error("在 %s 中未找到支持的文献文件。", lit_dir)
        _interactive_prompt_unsupported(skipped, SUPPORTED_EXTS | CAJ_EXT)
        sys.exit(1)

    logging.info("找到 %d 篇文献，开始处理...", len(lit_files))
    if skipped:
        logging.info("跳过 %d 个不支持的文件", len(skipped))

    # Determine output directory
    if output_dir is None:
        output_dir = lit_dir / ".els_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load cache for incremental extraction
    cache_path = output_dir / "_literature_cache.json"
    cache = load_cache(cache_path)
    results: list[dict] = []
    to_extract: list[Path] = []
    cache_hits = 0

    # FIX: use relative path as cache key instead of bare filename
    for lf in lit_files:
        rel_path = str(lf.relative_to(lit_dir))
        file_hash = file_sha256(str(lf))
        cached = cache.get(rel_path)
        if cached and cached.get("sha256") == file_hash and cached.get("result"):
            results.append(cached["result"])
            cache_hits += 1
        else:
            to_extract.append(lf)

    if cache_hits:
        logging.info("缓存命中 %d 篇（文件未变更），跳过重新提取", cache_hits)
    if to_extract:
        logging.info("需要重新提取 %d 篇", len(to_extract))

    # Concurrent extraction with ThreadPoolExecutor (I/O-bound: reading files)
    if to_extract:
        max_workers = min(4, len(to_extract)) if to_extract else 1
        logging.info("使用 %d 线程并发处理...", max_workers)

        def _extract_with_log(path: str) -> dict:
            info = extract_info(path, max_pages=max_pages)
            rel = Path(path).relative_to(lit_dir)
            info["relative_path"] = str(rel)
            info["filename"] = rel.name
            logging.info(
                "  [DONE] %s P%d WC%d | %s",
                info["format"],
                info["pages"],
                info["word_count"],
                str(rel)[:50],
            )
            return info

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            extracted = list(
                executor.map(_extract_with_log, (str(lf) for lf in to_extract))
            )
        results.extend(extracted)

    # Also set relative_path for cached results if missing
    for r in results:
        if not r.get("relative_path"):
            for lf in lit_files:
                if lf.name == r.get("filename"):
                    r["relative_path"] = str(lf.relative_to(lit_dir))
                    break

    # Update cache with fresh results (keyed by relative path)
    new_cache: dict[str, dict] = {}
    for r in results:
        rel_path = r.get("relative_path", "")
        if not rel_path:
            for lf in lit_files:
                if lf.name == r.get("filename"):
                    rel_path = str(lf.relative_to(lit_dir))
                    break
        if rel_path:
            for lf in lit_files:
                if str(lf.relative_to(lit_dir)) == rel_path:
                    new_cache[rel_path] = {
                        "sha256": file_sha256(str(lf)),
                        "result": r,
                    }
                    break
    save_cache(cache_path, new_cache)

    # Duplicate detection
    duplicates = find_duplicates(results)
    if duplicates:
        logging.info("检测到 %d 篇疑似重复文献", len(duplicates))
        for fname, dlist in duplicates.items():
            logging.info("  - %s ↔ %s", fname, ", ".join(dlist))

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
        rel = r.get("relative_path", r["filename"])
        print(
            f"[{status}] {r['format']:5} P{r['pages']:3} WC{r['word_count']:6} | "
            f"{rel[:45]}{dup_mark}{note}"
        )

    # JSON output
    output_payload = {
        "citation_style": citation_style,
        "max_pages": max_pages,
        "duplicates": duplicates,
        "results": results,
    }
    output_path = output_dir / "_literature_extraction.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)
    logging.info("JSON 结果已保存：%s", output_path)

    # Markdown report output
    md_path = output_dir / "_literature_report.md"
    md_content = generate_markdown_report(
        results, lit_dir, skipped, duplicates, citation_style
    )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logging.info("Markdown 报告已保存：%s", md_path)

    # BibTeX output
    if bibtex:
        bib_path = output_dir / "_literature_references.bib"
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(generate_bibtex(results))
        logging.info("BibTeX 文件已保存：%s", bib_path)


if __name__ == "__main__":
    main()
