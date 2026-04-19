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
- **`argparse`-based CLI argument parsing**: Replaced the hand-rolled `while` loop argument parser with `argparse.ArgumentParser`. All existing short/long flags (`-m`, `-c`, `-o`, `-b`, `-v`, `-q`, `--no-recursive`) remain unchanged; adds automatic `--help` generation and strict type/choice validation.
- **Package `__init__.py` files**: Added `__init__.py` to `core/`, `extractors/`, `citation/`, `cache/`, `checkpoint/`, and `report/` so the module tree is recognized as a proper Python package.
- **Dependency declaration files**: Added `requirements.txt` (runtime deps with minimum versions) and `pyproject.toml` (PEP 621 project metadata + build-system + CLI entry-point).
- **Centralized configuration (`core/config.py`)**: All previously hard-coded heuristic constants (page thresholds, scan-detection limits, text-sampling sizes, citation thresholds) are now defined in one place. Users and developers can tune behavior without hunting through `helpers.py` and extractors.
- **Metadata fallback heuristics (`extract_meta_fallback_from_text`)**: When PDF `/Title` or `/Author` metadata is empty, the system now falls back to extracting title, author, and year from the first-page text using heuristic rules (title-length windowing, author-marker regexes, year extraction). Reduces "incomplete metadata" false positives significantly.
- **Workflow checkpoint persistence (`checkpoint/manager.py`)**: After Stage 1 finishes, `_els_stage.json` is written to the output directory containing stage number, literature folder path, result count, and optional Stage 0 config. Enables Claude to resume multi-turn sessions without re-running extraction.
- **Test coverage expanded**: Added `TestExtractMetaFallbackFromText` (6 cases) and `TestCheckpointManager` (4 cases). Total test count: 92+ → 103.
- **Environment pre-check (`--env-check`)**: New CLI flag runs dependency validation, terminal encoding detection (Windows GBK trap), encrypted PDF preview, and scanned-PDF preview before extraction begins.
- **Encrypted PDF detection**: `extractors/pdf.py` now detects `is_encrypted` via PyPDF2; attempts empty-password decrypt; surfaces encryption status in JSON/Markdown output.
- **Windows encoding robustness**: `extract_literature_metadata.py` now forces UTF-8 on `sys.stdout`/`sys.stderr` via `TextIOWrapper` to prevent mojibake on GBK terminals.
- **Fast Mode (Mode C)**: SKILL.md now supports a fast-path workflow where Stage 2 and Stage 3 checkpoints are merged when the user explicitly authorizes auto-advance (all 5 configs provided + "直接走").
- **Output type configuration (Stage 0)**: New config item #6 (`thesis` / `review article`) controls how Rule 8 (critical analysis) is distributed — inline per cluster for reviews, or concentrated in a unified critique section for theses.
- **Survey paper explicit flagging**: Rule 9 now mandates `〔综述〕` immediately after the first in-text citation of high-citation survey papers.
- **Incremental result reuse**: SKILL.md Stage 1 now explicitly instructs: if `_literature_extraction.json` exists and files are unchanged (SHA-256 cache), skip re-extraction and proceed to Stage 2.

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
- Cross-subfolder cache key collision: previously used `lf.name` (bare filename) as cache key, causing false hits for identically-named files in different subfolders. Now uses `str(lf.relative_to(lit_dir))` (relative path) as cache key.
- Cache update logic reduced from O(n³) to O(n) by pre-building a `path_map` dict, eliminating redundant nested loops over `lit_files` during cache writes.
- BibTeX export now escapes LaTeX special characters (`\ { } $ & # _ ^ ~ %`) to prevent `.bib` compilation failures.

### Refactored

- **Modular architecture**: Split the 1,282-line monolithic `extract_literature_metadata.py` into a clean module structure:
  - `core/` — constants, config, helpers, logging config
  - `extractors/` — format-specific extractors (PDF/DOCX/TXT/EPUB) with module-level lazy imports for optional dependencies
  - `citation/` — citation engine + BibTeX generator
  - `cache/` — cache manager (upgraded to version 2)
  - `checkpoint/` — workflow checkpoint persistence for multi-turn sessions
  - `report/` — Markdown report generator
  - `extract_literature_metadata.py` remains the CLI entry point for full backward compatibility.

### Added (Tests)

- Mock-based unit tests that run without optional dependencies installed:
  - `TestExtractPdfMock` (4 cases: metadata extraction, scan detection, corrupted file, year-from-filename fallback)
  - `TestExtractDocxMock` (2 cases)
  - `TestExtractEpubMock` (2 cases)
  - `TestExtractInfoDispatcher` (2 cases: unsupported format, CAJ format)
  - `TestCacheManager` (3 cases: roundtrip, missing file, version number)
- Total test count: 79 → 92+.

### Changed

- Optional dependencies (`PyPDF2`, `python-docx`, `ebooklib`) now use module-level `try/except` imports; functions return friendly messages instead of crashing when dependencies are missing.
- Cache format upgraded from `version: 1` to `version: 2`. Old caches are ignored and automatically rebuilt — no breaking changes.
- `SKILL.md` compressed from 456 lines to ~220 lines; full example dialogue moved to README.md.

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
