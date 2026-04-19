#!/usr/bin/env python3
"""Unit tests for core helper functions in extract_literature_metadata.py.

Run with:
    python -m unittest test_extract_literature_metadata.py
"""

import os
import tempfile
import unittest
from pathlib import Path

from extract_literature_metadata import (
    _detect_scanned_pdf,
    _estimate_pages_from_chars,
    _file_sha256,
    _safe_truncate,
    _smart_word_count,
)


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


if __name__ == "__main__":
    unittest.main()
