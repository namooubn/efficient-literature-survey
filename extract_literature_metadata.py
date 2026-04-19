#!/usr/bin/env python3
"""
Batch-extract metadata from a folder of literature files (PDF, DOCX, TXT, MD, EPUB).
Outputs a structured report with title, author, page/word count, text volume,
and scanned-image detection (PDF only).

Usage:
    python extract_literature_metadata.py /path/to/literature/folder

Dependencies:
    pip install PyPDF2 pdfplumber python-docx ebooklib
"""

import os
import sys
import json
import math
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_pages_from_chars(char_count: int, chars_per_page: int = 500) -> int:
    """Estimate page count for text-based files (TXT/MD) where true pagination is unknown."""
    return max(1, math.ceil(char_count / chars_per_page))


def _safe_truncate(text: str, limit: int = 2000) -> str:
    return text[:limit] if text else ""


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

    # Word count approximation (PDF text extraction often loses spacing; treat as rough)
    result["word_count"] = len(total_text.split()) if result["text_chars"] > 0 else 0

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

        # Core properties
        core_props = doc.core_properties
        result["author_from_meta"] = core_props.author or ""
        result["title_from_meta"] = core_props.title or ""

        # Collect text from all paragraphs (limit to first 30 for speed)
        paragraphs = doc.paragraphs[:30]
        full_text = "\n".join(p.text for p in paragraphs)
        result["text_chars"] = len(full_text)
        result["word_count"] = len(full_text.split())
        result["first_page_text"] = _safe_truncate(full_text)

        # Estimate page count
        result["pages"] = _estimate_pages_from_chars(result["text_chars"])

        # If there are tables, include their text too for word_count
        table_texts = []
        for table in doc.tables[:5]:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        table_texts.append(cell.text.strip())
        if table_texts:
            table_full = "\n".join(table_texts)
            result["word_count"] += len(table_full.split())

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
    result["word_count"] = len(content.split())
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

        # Metadata
        title_list = book.get_metadata("DC", "title")
        if title_list:
            result["title_from_meta"] = str(title_list[0][0])
        creator_list = book.get_metadata("DC", "creator")
        if creator_list:
            result["author_from_meta"] = str(creator_list[0][0])

        # Extract text from document items (limit to first 10 for speed)
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
        result["word_count"] = len(full_text.split())
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
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if sys.argv[1:] and sys.argv[1] in ("-h", "--help") else 1)

    lit_dir = Path(sys.argv[1])

    all_files = sorted([f for f in lit_dir.iterdir() if f.is_file()])
    lit_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTS | CAJ_EXT]
    skipped = [f.name for f in all_files if f.suffix.lower() not in SUPPORTED_EXTS | CAJ_EXT]

    if not lit_files:
        print(f"No supported literature files found in {lit_dir}")
        print(f"Supported: {', '.join(sorted(SUPPORTED_EXTS | CAJ_EXT))}")
        sys.exit(1)

    results = []
    print(f"Total literature files found: {len(lit_files)}")
    if skipped:
        print(f"Skipped unsupported files: {len(skipped)}")

    for i, lf in enumerate(lit_files, 1):
        print(f"[{i}/{len(lit_files)}] Processing: {lf.name}")
        info = extract_info(str(lf))
        results.append(info)

    # Console summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for r in results:
        status = "SCANNED" if r["is_scanned"] else "OK"
        note = f" | NOTE: {r['note']}" if r["note"] else ""
        print(
            f"[{status:7}] {r['format']:5} P{r['pages']:3} WC{r['word_count']:6} | "
            f"{r['filename'][:45]}{note}"
        )

    # JSON output
    output_path = lit_dir / "_literature_extraction.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
