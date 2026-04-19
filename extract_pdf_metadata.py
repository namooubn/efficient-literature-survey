#!/usr/bin/env python3
"""
Batch-extract metadata from a folder of PDFs.
Outputs a structured report with title, author, page count, text volume,
and scanned-image detection.

Usage:
    python extract_pdf_metadata.py /path/to/pdf/folder

Dependencies:
    pip install PyPDF2 pdfplumber
"""

import os
import sys
import json
from pathlib import Path


def extract_info(pdf_path: str) -> dict:
    """Extract metadata and text sample from a single PDF."""
    result = {
        "filename": os.path.basename(pdf_path),
        "pages": 0,
        "text_chars": 0,
        "first_page_text": "",
        "is_scanned": False,
        "author_from_meta": "",
        "title_from_meta": "",
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
                    result["first_page_text"] = txt[:2000]
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
                        result["first_page_text"] = txt[:2000]
                result["text_chars"] = len(total_text)
        except Exception:
            pass

    # Scanned-image detection heuristic
    if result["text_chars"] < 200 and result["pages"] > 5:
        result["is_scanned"] = True
    elif result["text_chars"] < 50:
        result["is_scanned"] = True

    return result


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} /path/to/pdf/folder")
        sys.exit(1)

    pdf_dir = Path(sys.argv[1])
    pdf_files = sorted([f for f in pdf_dir.iterdir() if f.suffix.lower() == ".pdf"])

    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        sys.exit(1)

    results = []
    print(f"Total PDFs found: {len(pdf_files)}")
    for i, pf in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pf.name}")
        info = extract_info(str(pf))
        results.append(info)

    # Console summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for r in results:
        status = "SCANNED" if r["is_scanned"] else "OK"
        print(
            f"[{status:7}] P{r['pages']:3} | {r['text_chars']:6} chars | {r['filename'][:55]}"
        )

    # JSON output
    output_path = pdf_dir / "_literature_extraction.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
