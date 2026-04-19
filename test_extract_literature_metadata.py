#!/usr/bin/env python3
"""Unit tests for core helper functions in extract_literature_metadata.py.

Run with:
    python -m unittest test_extract_literature_metadata.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

from extract_literature_metadata import (
    _detect_scanned_pdf,
    _estimate_pages_from_chars,
    _file_sha256,
    _find_duplicates,
    _get_pdf_read_pages,
    _safe_truncate,
    _smart_word_count,
    extract_txt,
    generate_citation,
)

# Optional dependencies for integration tests
HAS_PYPDF2 = False
HAS_PYTHON_DOCX = False
HAS_EBOOKLIB = False

try:
    import PyPDF2  # noqa: F401
    HAS_PYPDF2 = True
except ImportError:
    pass

try:
    import docx  # noqa: F401
    HAS_PYTHON_DOCX = True
except ImportError:
    pass

try:
    import ebooklib  # noqa: F401
    HAS_EBOOKLIB = True
except ImportError:
    pass

if HAS_PYPDF2:
    from extract_literature_metadata import extract_pdf
if HAS_PYTHON_DOCX:
    from extract_literature_metadata import extract_docx
if HAS_EBOOKLIB:
    from extract_literature_metadata import extract_epub


class TestSmartWordCount(unittest.TestCase):
    """Tests for _smart_word_count with mixed CJK/English text."""

    def test_pure_chinese(self):
        text = "这是一个测试句子，包含多个中文字符。"
        # 16 Chinese chars + 0 English tokens
        self.assertEqual(_smart_word_count(text), 16)

    def test_pure_english(self):
        text = "This is a simple test sentence."
        self.assertEqual(_smart_word_count(text), 6)

    def test_mixed_chinese_english(self):
        text = "这是test一个mixed案例case。"
        # 4 Chinese chars + 2 English tokens
        self.assertEqual(_smart_word_count(text), 6)

    def test_empty_string(self):
        self.assertEqual(_smart_word_count(""), 0)

    def test_punctuation_only(self):
        # Pure punctuation falls back to len(text.split()) -> 1 token
        self.assertEqual(_smart_word_count("！？，。;:"), 1)

    def test_numbers_and_english(self):
        text = "In 2024, there are 3 major updates."
        # Pure English falls back to len(text.split()) = 7 tokens
        self.assertEqual(_smart_word_count(text), 7)


class TestDetectScannedPdf(unittest.TestCase):
    """Tests for _detect_scanned_pdf multi-page sampling heuristic."""

    def test_dense_text_not_scanned(self):
        page_texts = ["a" * 600 for _ in range(10)]
        self.assertFalse(_detect_scanned_pdf(page_texts, 10))

    def test_empty_pages_scanned(self):
        page_texts = [""] * 10
        self.assertTrue(_detect_scanned_pdf(page_texts, 10))

    def test_cover_image_then_text(self):
        # First page is cover image, rest are text
        page_texts = [""] + ["a" * 500 for _ in range(9)]
        self.assertFalse(_detect_scanned_pdf(page_texts, 10))

    def test_short_doc_safe(self):
        # 1-page doc with almost no text should not be flagged
        page_texts = ["abc"]
        self.assertFalse(_detect_scanned_pdf(page_texts, 1))

    def test_low_density_scanned(self):
        # Multi-page with very low text density
        page_texts = ["x" * 8 for _ in range(20)]
        self.assertTrue(_detect_scanned_pdf(page_texts, 20))

    def test_no_pages(self):
        self.assertFalse(_detect_scanned_pdf([], 0))


class TestEstimatePagesFromChars(unittest.TestCase):
    """Tests for _estimate_pages_from_chars."""

    def test_normal(self):
        self.assertEqual(_estimate_pages_from_chars(1000), 2)

    def test_exact_multiple(self):
        self.assertEqual(_estimate_pages_from_chars(500), 1)

    def test_zero_fallback(self):
        self.assertEqual(_estimate_pages_from_chars(0), 1)

    def test_custom_chars_per_page(self):
        self.assertEqual(_estimate_pages_from_chars(1000, chars_per_page=300), 4)


class TestSafeTruncate(unittest.TestCase):
    """Tests for _safe_truncate."""

    def test_truncate_long(self):
        text = "a" * 3000
        self.assertEqual(len(_safe_truncate(text)), 2000)

    def test_no_truncate_short(self):
        text = "short text"
        self.assertEqual(_safe_truncate(text), text)

    def test_empty(self):
        self.assertEqual(_safe_truncate(""), "")

    def test_custom_limit(self):
        text = "hello world"
        self.assertEqual(_safe_truncate(text, limit=5), "hello")


class TestFileSha256(unittest.TestCase):
    """Tests for _file_sha256 incremental cache key generation."""

    def test_normal_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("hello world")
            path = f.name
        try:
            h1 = _file_sha256(path)
            h2 = _file_sha256(path)
            self.assertEqual(len(h1), 64)
            self.assertEqual(h1, h2)
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            path = f.name
        try:
            h = _file_sha256(path)
            self.assertEqual(len(h), 64)
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        self.assertEqual(_file_sha256("/nonexistent/path/file.txt"), "")

    def test_different_files_different_hash(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f1:
            f1.write("content A")
            p1 = f1.name
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f2:
            f2.write("content B")
            p2 = f2.name
        try:
            self.assertNotEqual(_file_sha256(p1), _file_sha256(p2))
        finally:
            os.unlink(p1)
            os.unlink(p2)


class TestGetPdfReadPages(unittest.TestCase):
    """Tests for PDF read-strategy heuristic."""

    def test_short_doc_reads_all(self):
        self.assertEqual(_get_pdf_read_pages(30), list(range(30)))

    def test_exactly_50_reads_all(self):
        self.assertEqual(_get_pdf_read_pages(50), list(range(50)))

    def test_long_doc_samples(self):
        pages = _get_pdf_read_pages(100)
        # First 15 + last 5
        self.assertEqual(pages[:15], list(range(15)))
        self.assertEqual(pages[-5:], list(range(95, 100)))
        self.assertEqual(len(pages), 20)

    def test_max_pages_override(self):
        self.assertEqual(_get_pdf_read_pages(100, max_pages=5), list(range(5)))

    def test_zero_max_pages_ignored(self):
        self.assertEqual(_get_pdf_read_pages(10, max_pages=0), list(range(10)))

    def test_negative_max_pages_ignored(self):
        self.assertEqual(_get_pdf_read_pages(10, max_pages=-3), list(range(10)))


class TestFindDuplicates(unittest.TestCase):
    """Tests for duplicate detection by title similarity."""

    def test_exact_match(self):
        results = [
            {"filename": "a.pdf", "title_from_meta": "Deep Learning"},
            {"filename": "b.pdf", "title_from_meta": "Deep Learning"},
        ]
        dups = _find_duplicates(results, threshold=0.90)
        self.assertIn("a.pdf", dups)
        self.assertIn("b.pdf", dups)

    def test_no_match(self):
        results = [
            {"filename": "a.pdf", "title_from_meta": "Deep Learning"},
            {"filename": "b.pdf", "title_from_meta": "Quantum Computing"},
        ]
        dups = _find_duplicates(results, threshold=0.90)
        self.assertEqual(dups, {})

    def test_fallback_to_filename(self):
        results = [
            {"filename": "same_title.pdf", "title_from_meta": ""},
            {"filename": "same_title.pdf", "title_from_meta": ""},
        ]
        dups = _find_duplicates(results, threshold=0.90)
        self.assertIn("same_title.pdf", dups)


class TestGenerateCitation(unittest.TestCase):
    """Tests for citation formatting across styles."""

    def test_gb7714_single_author(self):
        meta = {"author_from_meta": "张三", "title_from_meta": "人工智能导论", "filename": "x.pdf", "format": "pdf"}
        self.assertIn("张三", generate_citation(meta, "gb7714"))
        self.assertIn("人工智能导论", generate_citation(meta, "gb7714"))

    def test_gb7714_multiple_authors(self):
        meta = {"author_from_meta": "张三, 李四, 王五, 赵六", "title_from_meta": "深度学习", "filename": "x.pdf", "format": "pdf"}
        cite = generate_citation(meta, "gb7714")
        self.assertIn("张三", cite)
        self.assertIn("等", cite)

    def test_apa(self):
        meta = {"author_from_meta": "John Smith", "title_from_meta": "AI Survey", "filename": "x.pdf", "format": "pdf"}
        cite = generate_citation(meta, "apa")
        self.assertIn("Smith", cite)
        self.assertIn("AI Survey", cite)

    def test_mla(self):
        meta = {"author_from_meta": "John Smith", "title_from_meta": "AI Survey", "filename": "x.pdf", "format": "pdf"}
        cite = generate_citation(meta, "mla")
        self.assertIn('"AI Survey."', cite)

    def test_numbered(self):
        meta = {"author_from_meta": "", "title_from_meta": "Title", "filename": "x.pdf", "format": "pdf", "_citation_number": 5}
        self.assertEqual(generate_citation(meta, "numbered"), "[5] Title")

    def test_no_author(self):
        meta = {"author_from_meta": "", "title_from_meta": "", "filename": "unknown.pdf", "format": "pdf"}
        cite = generate_citation(meta, "gb7714")
        self.assertIn("unknown.pdf", cite)


class TestExtractTxt(unittest.TestCase):
    """Integration tests for extract_txt (no extra deps)."""

    def test_utf8_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".txt") as f:
            f.write("Hello world\nSecond line")
            path = f.name
        try:
            info = extract_txt(path)
            self.assertEqual(info["word_count"], 4)
            self.assertEqual(info["text_chars"], 23)
            self.assertEqual(info["format"], "txt")
        finally:
            os.unlink(path)

    def test_gbk_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="gbk", suffix=".txt") as f:
            f.write("中文内容测试")
            path = f.name
        try:
            info = extract_txt(path)
            self.assertEqual(info["word_count"], 6)  # 6 Chinese chars
            self.assertEqual(info["format"], "txt")
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".txt") as f:
            path = f.name
        try:
            info = extract_txt(path)
            self.assertEqual(info["word_count"], 0)
            self.assertEqual(info["text_chars"], 0)
        finally:
            os.unlink(path)

    def test_md_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".md") as f:
            f.write("# Title\n\nBody text here.")
            path = f.name
        try:
            info = extract_txt(path)
            self.assertEqual(info["format"], "md")
            self.assertIn("Title", info["first_page_text"])
        finally:
            os.unlink(path)


@unittest.skipUnless(HAS_PYPDF2, "PyPDF2 not installed")
class TestExtractPdf(unittest.TestCase):
    """Integration tests for extract_pdf."""

    def _make_blank_pdf(self, page_count: int) -> str:
        """Create a blank PDF with the given number of pages."""
        from PyPDF2 import PdfWriter
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=612, height=792)
        fd, path = tempfile.mkstemp(suffix=".pdf")
        try:
            with os.fdopen(fd, "wb") as f:
                writer.write(f)
        except Exception:
            os.close(fd)
            raise
        return path

    def test_normal_pdf_pages(self):
        path = self._make_blank_pdf(10)
        try:
            info = extract_pdf(path)
            self.assertEqual(info["pages"], 10)
            self.assertEqual(info["format"], "pdf")
        finally:
            os.unlink(path)

    def test_short_pdf_reads_all_pages(self):
        """Documents with <= 50 pages should have all pages sampled."""
        path = self._make_blank_pdf(20)
        try:
            info = extract_pdf(path)
            self.assertEqual(info["pages"], 20)
            # Blank pages are flagged as scanned
            self.assertTrue(info["is_scanned"])
        finally:
            os.unlink(path)

    def test_long_pdf_samples_pages(self):
        """Documents > 50 pages should sample first 15 + last 5."""
        path = self._make_blank_pdf(100)
        try:
            info = extract_pdf(path)
            self.assertEqual(info["pages"], 100)
            # text_chars should be low because pages are blank
            self.assertEqual(info["text_chars"], 0)
        finally:
            os.unlink(path)

    def test_corrupted_pdf_graceful(self):
        fd, path = tempfile.mkstemp(suffix=".pdf")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("this is not a pdf")
            info = extract_pdf(path)
            self.assertIn("error", info["note"].lower())
        finally:
            os.unlink(path)

    def test_max_pages_override(self):
        path = self._make_blank_pdf(30)
        try:
            info = extract_pdf(path, max_pages=5)
            self.assertEqual(info["pages"], 30)
            # Only 5 pages read, but total_pages is still 30
            self.assertEqual(info["text_chars"], 0)
        finally:
            os.unlink(path)


@unittest.skipUnless(HAS_PYTHON_DOCX, "python-docx not installed")
class TestExtractDocx(unittest.TestCase):
    """Integration tests for extract_docx."""

    def test_normal_docx(self):
        from docx import Document
        doc = Document()
        doc.add_paragraph("Hello world")
        doc.add_paragraph("Second paragraph with more text")

        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            doc.save(path)
            info = extract_docx(path)
            self.assertEqual(info["format"], "docx")
            self.assertGreater(info["word_count"], 0)
            self.assertIn("Hello", info["first_page_text"])
        finally:
            os.unlink(path)

    def test_empty_docx(self):
        from docx import Document
        doc = Document()
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            doc.save(path)
            info = extract_docx(path)
            self.assertEqual(info["format"], "docx")
            self.assertEqual(info["word_count"], 0)
        finally:
            os.unlink(path)

    def test_docx_with_author_title(self):
        from docx import Document
        doc = Document()
        doc.add_paragraph("Content here")
        doc.core_properties.author = "Test Author"
        doc.core_properties.title = "Test Title"

        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            doc.save(path)
            info = extract_docx(path)
            self.assertEqual(info["author_from_meta"], "Test Author")
            self.assertEqual(info["title_from_meta"], "Test Title")
        finally:
            os.unlink(path)


@unittest.skipUnless(HAS_EBOOKLIB, "ebooklib not installed")
class TestExtractEpub(unittest.TestCase):
    """Integration tests for extract_epub."""

    def test_normal_epub(self):
        from ebooklib import epub
        book = epub.EpubBook()
        book.set_identifier("test-id")
        book.set_title("Test Book")
        book.set_language("en")
        book.add_author("Test Author")

        c1 = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
        c1.content = "<html><body><p>Hello world from EPUB.</p></body></html>"
        book.add_item(c1)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = [c1]

        fd, path = tempfile.mkstemp(suffix=".epub")
        os.close(fd)
        try:
            epub.write_epub(path, book)
            info = extract_epub(path)
            self.assertEqual(info["format"], "epub")
            self.assertEqual(info["title_from_meta"], "Test Book")
            self.assertEqual(info["author_from_meta"], "Test Author")
            self.assertIn("Hello", info["first_page_text"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
