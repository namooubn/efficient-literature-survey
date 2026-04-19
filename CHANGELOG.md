# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-19

### Added

- **Concurrent extraction**: `ThreadPoolExecutor(max_workers=4)` parallelizes Stage 1 metadata extraction for large corpora (30+ files).
- **Incremental / cached mode**: Files are keyed by SHA-256 hash; unchanged files are skipped on re-runs. Cache stored in `_literature_cache.json`.
- **Multi-page scanned-PDF detection**: `_detect_scanned_pdf()` samples pages at beginning, middle, and end to reduce false positives from image-only cover pages.
- **Unit tests**: `test_extract_literature_metadata.py` with 24 test cases covering `_smart_word_count`, `_detect_scanned_pdf`, `_estimate_pages_from_chars`, `_safe_truncate`, and `_file_sha256`.

### Changed

- **SKILL.md trigger description**: Split long trigger list into a concise `description` field + a dedicated `## Triggers` section for better Claude Code skill matching.
- **Error handling**: Replaced silent `except Exception: pass` with structured error logging into `result["note"]` so extraction failures are visible in reports.

### Fixed

- Scanned-image false positives caused by image-only first pages (e.g., journal cover pages with text content later in the document).

### Skipped

- PDF reference-list extraction (deemed low ROI; user-approved skip).

## [1.1.0] - 2026-04-18

### Added

- Interactive CLI with path validation.
- CJK/English mixed word counting (`_smart_word_count`).
- Markdown report generation (`_literature_report.md`).
- User checkpoint annotations in SKILL.md workflow.
- Multi-format support: PDF, DOCX, TXT, MD, EPUB.

## [1.0.0] - 2026-04-17

### Added

- Initial release with PDF-only extraction (`extract_pdf_metadata.py`).
- Five-stage workflow (Stage 0–4) for literature survey automation.
