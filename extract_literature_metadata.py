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
from pathlib import Path
from datetime import datetime


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

def extract_pdf(pdf_path: str) -> dict:
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

        total_text = ""
        for i, page in enumerate(reader.pages[:15]):
            try:
                txt = page.extract_text() or ""
                total_text += txt
                if i == 0:
                    result["first_page_text"] = _safe_truncate(txt)
            except Exception:
                pass
        result["text_chars"] = len(total_text)
    except Exception:
        pass

    # Fallback to pdfplumber if PyPDF2 extracted very little text
    if result["text_chars"] < 500:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                result["pages"] = len(pdf.pages)
                total_text = ""
                for i, page in enumerate(pdf.pages[:15]):
                    txt = page.extract_text() or ""
                    total_text += txt
                    if i == 0:
                        result["first_page_text"] = _safe_truncate(txt)
                result["text_chars"] = len(total_text)
        except Exception:
            pass

    result["word_count"] = _smart_word_count(total_text) if result["text_chars"] > 0 else 0

    # Scanned-image detection heuristic (PDF only)
    if result["text_chars"] < 200 and result["pages"] > 5:
        result["is_scanned"] = True
    elif result["text_chars"] < 50:
        result["is_scanned"] = True

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


def extract_info(file_path: str) -> dict:
    """Dispatch to the correct extractor based on file extension."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return extract_pdf(file_path)
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

def generate_markdown_report(results: list, lit_dir: Path, skipped: list) -> str:
    """Generate a human-readable Markdown report from extraction results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scanned = [r for r in results if r["is_scanned"]]
    by_format = {}
    for r in results:
        fmt = r["format"]
        by_format.setdefault(fmt, []).append(r)

    total_pages = sum(r["pages"] for r in results)
    total_words = sum(r["word_count"] for r in results)

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

    lines.extend([
        "## 文献详情（按文件名排序）\n",
        "| 文件名 | 格式 | 页数 | 字数 | 作者 | 标题 | 备注 |",
        "|--------|------|------|------|------|------|------|",
    ])
    for r in sorted(results, key=lambda x: x["filename"].lower()):
        author = r["author_from_meta"] or "—"
        title = r["title_from_meta"] or "—"
        note = r["note"] or "—"
        if len(title) > 40:
            title = title[:37] + "..."
        if len(author) > 30:
            author = author[:27] + "..."
        lines.append(
            f"| {r['filename']} | {r['format']} | {r['pages']} | {r['word_count']} | "
            f"{author} | {title} | {note} |"
        )
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
    # Help
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    # No args -> interactive prompt
    if len(sys.argv) < 2:
        print("用法：python extract_literature_metadata.py <文献文件夹路径>")
        print("未提供路径，进入交互模式...")
        lit_dir = _prompt_path()
    else:
        lit_dir = Path(sys.argv[1]).expanduser()
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

    results = []
    print(f"\n找到 {len(lit_files)} 篇文献，开始处理...")
    if skipped:
        print(f"跳过 {len(skipped)} 个不支持的文件")

    for i, lf in enumerate(lit_files, 1):
        print(f"  [{i}/{len(lit_files)}] {lf.name}")
        info = extract_info(str(lf))
        results.append(info)

    # Console summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for r in results:
        status = "⚠️ SCANNED" if r["is_scanned"] else "  OK     "
        note = f" | NOTE: {r['note']}" if r["note"] else ""
        print(
            f"[{status}] {r['format']:5} P{r['pages']:3} WC{r['word_count']:6} | "
            f"{r['filename'][:45]}{note}"
        )

    # JSON output
    output_path = lit_dir / "_literature_extraction.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 结果已保存：{output_path}")

    # Markdown report output
    md_path = lit_dir / "_literature_report.md"
    md_content = generate_markdown_report(results, lit_dir, skipped)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown 报告已保存：{md_path}")


if __name__ == "__main__":
    main()
