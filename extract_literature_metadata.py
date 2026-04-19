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

import argparse
import importlib
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Fix Windows terminal encoding (GBK → UTF-8) to prevent mojibake in Chinese output
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Ensure sub-package imports resolve when run as a standalone script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from cache.manager import file_sha256, load_cache, save_cache
from checkpoint.manager import save_checkpoint
from citation.engine import generate_citation
from citation.bibtex import generate_bibtex
from core.constants import SUPPORTED_EXTS, CAJ_EXT
from core.helpers import find_duplicates
from core.logging_config import setup_logging
from extractors.pdf import extract_pdf
from extractors.docx import extract_docx
from extractors.txt import extract_txt
from extractors.epub import extract_epub
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
# Environment pre-check
# ---------------------------------------------------------------------------


def run_env_check(lit_dir: Path | None = None) -> bool:
    """Check dependencies, encoding, and preview problematic files.
    Returns True if all critical checks pass, False otherwise.
    """
    print("=" * 60)
    print("[环境预检] Efficient Literature Survey")
    print("=" * 60)
    all_ok = True

    # 1. Dependency check
    deps = {
        "PyPDF2": "PyPDF2",
        "pdfplumber": "pdfplumber",
        "docx": "python-docx",
        "ebooklib": "ebooklib",
        "bs4": "beautifulsoup4",
    }
    missing = []
    for mod, pkg in deps.items():
        try:
            importlib.import_module(mod)
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [FAIL] {pkg} 未安装")
            missing.append(pkg)
    if missing:
        print(f"\n  请运行: pip install {' '.join(missing)}")
        all_ok = False

    # 2. Encoding check (Windows GBK trap)
    import locale
    encoding = locale.getpreferredencoding(False)
    print(f"\n  系统默认编码: {encoding}")
    if encoding.lower() in ("gbk", "gb2312", "cp936"):
        print("  [WARN] Windows 默认编码为 GBK，中文输出可能出现乱码")
        print("  建议执行: chcp 65001  或  set PYTHONIOENCODING=utf-8")
        # Not fatal; just warn

    # 3. File preview (if folder provided)
    if lit_dir and lit_dir.exists():
        pdf_files = list(lit_dir.rglob("*.pdf")) if lit_dir.is_dir() else []
        if pdf_files:
            print(f"\n  扫描到 {len(pdf_files)} 个 PDF，预览前 5 个：")
            from PyPDF2 import PdfReader
            for p in pdf_files[:5]:
                flag = ""
                try:
                    r = PdfReader(str(p))
                    if getattr(r, "is_encrypted", False):
                        flag = " [加密]"
                    elif len(pdf_files) < 10 or not r.pages[0].extract_text():
                        flag = " [可能为扫描件/图片PDF]"
                except Exception as e:
                    flag = f" [读取失败: {type(e).__name__}]"
                print(f"    - {p.name}{flag}")
            encrypted = 0
            for p in pdf_files:
                try:
                    r = PdfReader(str(p))
                    if getattr(r, "is_encrypted", False):
                        encrypted += 1
                except Exception:
                    pass
            if encrypted:
                print(f"\n  [WARN] 检测到 {encrypted} 个加密 PDF，需手动解密")
    else:
        print("\n  未提供文献文件夹路径，跳过文件预览")

    print("=" * 60)
    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Batch-extract metadata from a folder of literature files."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Path to the literature folder (optional; enters interactive mode if omitted)",
    )
    parser.add_argument(
        "--max-pages", "-m", type=int, default=0,
        help="Maximum pages to read per PDF (0 = use smart heuristic)",
    )
    parser.add_argument(
        "--citation-style", "-c", default="gb7714",
        choices=["gb7714", "apa", "mla", "numbered"],
        help="Citation output style (default: gb7714)",
    )
    parser.add_argument(
        "--output-dir", "-o", default=None,
        help="Directory for output files (default: <folder>/.els_output)",
    )
    parser.add_argument(
        "--bibtex", "-b", action="store_true",
        help="Also export a BibTeX (.bib) file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable DEBUG-level logging",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Only show WARNING-level (and above) logging",
    )
    parser.add_argument(
        "--no-recursive", action="store_true",
        help="Disable recursive folder traversal",
    )
    parser.add_argument(
        "--env-check", "-e", action="store_true",
        help="Run environment pre-check only (no extraction)",
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Resolve folder path early for env-check
    lit_dir: Path | None = None
    if args.folder:
        lit_dir = Path(args.folder).expanduser()
        if not lit_dir.exists():
            lit_dir = None

    if args.env_check:
        ok = run_env_check(lit_dir)
        sys.exit(0 if ok else 1)

    # Always run a quick env check on first run
    run_env_check(lit_dir)

    # Determine folder path
    if args.folder is None:
        print("未提供路径，进入交互模式...")
        lit_dir = _prompt_path()
    else:
        lit_dir = Path(args.folder).expanduser()
        if not lit_dir.exists():
            print(f"路径不存在：{lit_dir}")
            print("进入交互模式...")
            lit_dir = _prompt_path()
        elif not lit_dir.is_dir():
            print(f"这不是一个文件夹：{lit_dir}")
            print("进入交互模式...")
            lit_dir = _prompt_path()

    # Collect files (recursive by default)
    if args.no_recursive:
        all_files = sorted([f for f in lit_dir.iterdir() if f.is_file()])
    else:
        all_files = sorted([f for f in lit_dir.rglob("*") if f.is_file()])

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
    output_dir: Path
    if args.output_dir is None:
        output_dir = lit_dir / ".els_output"
    else:
        output_dir = Path(args.output_dir).expanduser()
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
            info = extract_info(path, max_pages=args.max_pages)
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

    # Build a lookup once, reuse for both path-fixup and cache update
    path_map = {str(lf.relative_to(lit_dir)): lf for lf in lit_files}

    # Also set relative_path for cached results if missing
    for r in results:
        if not r.get("relative_path"):
            for rel, lf in path_map.items():
                if lf.name == r.get("filename"):
                    r["relative_path"] = rel
                    break

    # Update cache with fresh results (keyed by relative path)
    new_cache: dict[str, dict] = {}
    for r in results:
        rel_path = r.get("relative_path", "")
        if not rel_path:
            for rel, lf in path_map.items():
                if lf.name == r.get("filename"):
                    rel_path = rel
                    break
        lf = path_map.get(rel_path)
        if lf:
            new_cache[rel_path] = {
                "sha256": file_sha256(str(lf)),
                "result": r,
            }
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
        r["citation"] = generate_citation(r, args.citation_style)

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
        "citation_style": args.citation_style,
        "max_pages": args.max_pages,
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
        results, lit_dir, skipped, duplicates, args.citation_style
    )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logging.info("Markdown 报告已保存：%s", md_path)

    # BibTeX output
    if args.bibtex:
        bib_path = output_dir / "_literature_references.bib"
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(generate_bibtex(results))
        logging.info("BibTeX 文件已保存：%s", bib_path)

    # Persist workflow checkpoint for multi-turn Claude sessions
    save_checkpoint(
        output_dir=output_dir,
        stage=1,
        lit_dir=lit_dir,
        results_count=len(results),
    )


if __name__ == "__main__":
    main()
