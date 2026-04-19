# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-19

### Added

- **Full citation format support**: Rewrote `generate_citation()` to output standard-compliant references:
  - **GB/T 7714**: includes document-type marker `[J/M]`, publisher/journal, year, volume(issue), page range, DOI.
  - **APA 7th**: author(s), (year), title, *journal*, *volume*(issue), pages, DOI.
  - **MLA 9th**: author(s), "title," *journal*, vol. X, no. Y, year, pp. Z-W.
  - **Numbered**: `[N] author, title, 《journal》, year.`
  - Missing critical fields trigger a `〔文献信息不完整，请手动补全〕` warning instead of fabricating data.
- **Bibliographic metadata heuristics**: `_extract_bib_info_from_text()` scans first-page text for DOI, `Vol./No.`, `pp.`, Chinese `第X卷第Y期`, `第Z-W页`, `《journal》` patterns. Extracted fields feed into citations automatically.
- **BibTeX export**: `--bibtex` / `-b` CLI flag outputs `_literature_references.bib` with `@article` / `@book` / `@misc` auto-inference. Incomplete entries include a `note = {文献信息不完整，请手动补全}`.
- **Recursive folder traversal**: Default behavior now uses `rglob("*")` to discover files in subdirectories. `--no-recursive` disables it. Subfolder structure is preserved in `relative_path` and grouped in the Markdown report.
- **Structured logging**: Replaced all `print()` calls with the `logging` module. Added `--verbose` / `-v` (DEBUG) and `--quiet` / `-q` (WARNING) CLI flags.
- **Chinese compound surname support**: `_split_chinese_name()` recognizes 30+ compound surnames (欧阳, 司马, 诸葛, etc.). APA and MLA name converters now correctly handle Chinese names without whitespace delimiters.
- **Enhanced scanned-PDF guidance**: Markdown report now appends a blockquote with specific OCR tool recommendations (`marker`, `nougat`, `pdf2image + pytesseract`) and installation/usage commands.
- **Test coverage expanded**: 79 unit and integration tests (was 52), covering citation formats, BibTeX generation, bibliographic regex extraction, compound surnames, logging setup, and document-type heuristics.

### Changed

- **Citation generation overhaul**: Previous citations only contained `author. title[format]. year.` — now follows actual academic standards with all available metadata fields.
- **DOCX text sampling strategy**: Changed from first 30 paragraphs to first ~5000 characters, preventing metadata loss on long documents where front matter exceeds 30 paragraphs.
- **Scanned-PDF detection reliability**: `_detect_scanned_pdf()` now receives only actually-read page texts instead of a full-length list padded with empty strings, eliminating false positives on long documents where unread pages defaulted to empty.
- **Import organization**: Moved `import difflib` from mid-function to top-level imports.
- **Cache/output path isolation**: `_literature_cache.json`, `_literature_extraction.json`, and `_literature_report.md` now write to the configured output directory instead of the literature folder root.
- **Error handling**: Replaced silent `except Exception: pass` with structured error logging into `result["note"]` so extraction failures are visible in reports.
- **CLI arguments**: Added `--max-pages` (`-m`) to override PDF page-reading limits and `--citation-style` (`-c`) to choose between `gb7714`, `apa`, `mla`, and `numbered`.
- **JSON output structure**: Wrapped results in a top-level object with `citation_style`, `max_pages`, `duplicates`, and `results` keys for richer downstream consumption.
- **Markdown report**: Added "疑似重复文献" section, "按子文件夹分组" section, and "参考文献列表" appendix with auto-generated citations.

### Fixed

- Scanned-image false positives caused by image-only first pages (e.g., journal cover pages with text content later in the document).
- Chinese-name APA/MLA formatting failed for names without spaces (e.g., `欧阳明` was not recognized as `欧阳, M.`).
- `logging.basicConfig()` did not override existing handlers when called multiple times (e.g., in test suites).

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
