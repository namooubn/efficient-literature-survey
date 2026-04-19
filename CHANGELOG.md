# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-19

### Added

- **Concurrent extraction**: `ThreadPoolExecutor(max_workers=4)` parallelizes Stage 1 metadata extraction for large corpora (30+ files).
- **Incremental / cached mode**: Files are keyed by SHA-256 hash; unchanged files are skipped on re-runs. Cache stored in `_literature_cache.json`.
- **Multi-page scanned-PDF detection**: `_detect_scanned_pdf()` samples pages at beginning, middle, and end to reduce false positives from image-only cover pages.
- **Unit tests**: `test_extract_literature_metadata.py` with 24 test cases covering `_smart_word_count`, `_detect_scanned_pdf`, `_estimate_pages_from_chars`, `_safe_truncate`, and `_file_sha256`.
- **PDF read-strategy differentiation**: `_get_pdf_read_pages()` automatically reads full text for short documents (≤50 pages) and samples first 15 + last 5 pages for long documents (>50 pages), avoiding front-matter bias on monographs.
- **Duplicate detection**: `_find_duplicates()` detects duplicate references by title similarity using `difflib.SequenceMatcher` (threshold 80%). Results are shown in both JSON and Markdown reports.
- **Citation generation**: `generate_citation()` produces formatted citations in GB/T 7714, APA, MLA, and numbered styles. Citations are embedded in JSON (`citation` field) and appended to the Markdown report.
- **Integration tests**: Added `TestExtractPdf`, `TestExtractDocx`, `TestExtractTxt`, `TestExtractEpub`, `TestGetPdfReadPages`, `TestFindDuplicates`, and `TestGenerateCitation` — 28 additional test cases with conditional `skipUnless` for optional dependencies.
- **Context overflow guards in SKILL.md**: Added `[CONTEXT_OVERFLOW]` rules for Stage 2 (batch clustering when >40 refs) and Stage 3 (auto-downgrade P1 to abstract-only when P0+P1 exceeds 100k words).
- **`--output-dir` CLI flag**: Added `-o PATH` / `--output-dir PATH` to specify output directory. Defaults to `.els_output/` subfolder inside the literature folder, preventing intermediate files from polluting the user's reference folder.
- **Year extraction in citations**: PDF metadata `/CreationDate` is now parsed for year; falls back to filename pattern matching (`19xx`/`20xx`). Citations in GB/T 7714, APA, and MLA now include the year field.
- **`## Tool Use` section in SKILL.md**: Added explicit Bash/Read/Write tool usage instructions, including concrete command formats and per-tier reading strategies (P0 full-text with structure scan, P1 abstract+keyword-targeted sections, P2 abstract-only).

### Changed

- **SKILL.md trigger description**: Removed misleading `/efficient-literature-survey` slash command claim (user-installed skills do not support custom slash commands). Replaced with natural-language trigger guidance. README and README_EN updated accordingly.
- **SKILL.md Stage 3 reading strategy**: Replaced abstract instructions with concrete Read-tool steps (structure scan → full text or targeted chapters per tier) to reduce Claude's free-form interpretation.
- **DOCX text sampling strategy**: Changed from first 30 paragraphs to first ~5000 characters, preventing metadata loss on long documents where front matter exceeds 30 paragraphs.
- **Scanned-PDF detection reliability**: `_detect_scanned_pdf()` now receives only actually-read page texts instead of a full-length list padded with empty strings, eliminating false positives on long documents where unread pages defaulted to empty.
- **Import organization**: Moved `import difflib` from mid-function to top-level imports.
- **Cache/output path isolation**: `_literature_cache.json`, `_literature_extraction.json`, and `_literature_report.md` now write to the configured output directory instead of the literature folder root.
- **Error handling**: Replaced silent `except Exception: pass` with structured error logging into `result["note"]` so extraction failures are visible in reports.
- **CLI arguments**: Added `--max-pages` (`-m`) to override PDF page-reading limits and `--citation-style` (`-c`) to choose between `gb7714`, `apa`, `mla`, and `numbered`.
- **JSON output structure**: Wrapped results in a top-level object with `citation_style`, `max_pages`, `duplicates`, and `results` keys for richer downstream consumption.
- **Markdown report**: Added "疑似重复文献" section and "参考文献列表" appendix with auto-generated citations.

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
