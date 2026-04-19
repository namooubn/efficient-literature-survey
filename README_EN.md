# efficient-literature-survey

[Chinese](README.md) | **English**

---

## What It Does

Transforms a folder of 10-100 literature files (PDF, DOCX, TXT, MD, EPUB) into a structured literature map, then writes a complete thesis introduction and literature review — without reading every word.

Supports **custom chapter structures** or **default templates** (Chinese / English thesis frameworks), automatically adapting to the user's specified citation format and output language.

<table>
  <tr>
    <th width="12%">Stage</th>
    <th>Action</th>
    <th width="28%">Output</th>
  </tr>
  <tr>
    <td><b>0. Config</b></td>
    <td>Confirm language, citation format, chapter structure, <b>research positioning</b> (title/abstract/keywords — any is fine), <b>literature folder path</b>, output type (thesis / review article)</td>
    <td>Config checklist + user study positioning</td>
  </tr>
  <tr>
    <td>1. Extract</td>
    <td>Script extracts metadata from all literature files (recursive subfolder support)</td>
    <td>JSON report + Markdown summary (titles/authors/pages/word count/journal/vol/issue/pages/DOI/scan detection)</td>
  </tr>
  <tr>
    <td>2. Cluster</td>
    <td>Group into 5-8 thematic clusters, <b>score relevance against user's positioning</b> (Direct/Adjacent/Peripheral/Tangential), then assign reading tiers</td>
    <td>Literature map (P0/P1/P2 reading tiers) — <b>user confirmation required before proceeding</b></td>
  </tr>
  <tr>
    <td>3. Read</td>
    <td>Read by tier (full / abstract+conclusion / abstract only) — <b>reading plan confirmed by user before execution</b></td>
    <td>Extracted arguments and quotes</td>
  </tr>
  <tr>
    <td>4. Write</td>
    <td>Write according to user's chapter framework, with academically-compliant citations</td>
    <td>Formatted introduction + review draft</td>
  </tr>
</table>

---

## 5-Minute Quick Start

### Scenario: You have a folder of references and want to write a literature review quickly

**Step 1: Install**

```bash
mkdir -p ~/.claude/skills/
cp -r efficient-literature-survey ~/.claude/skills/
pip install -r requirements.txt
```

**Step 2: Open Claude Code and say**

> "Help me write a literature review. My references are in `/Users/alice/Documents/references`."

**Step 3: Claude will guide you through this flow**

| Turn | What Claude Does | What You Do |
|------|-----------------|-------------|
| 1 | Scans the folder (including subfolders), tells you how many files, what formats, any scanned PDFs | Check the count, confirm |
| 2 | Asks: language, citation style, research topic, chapter structure template | Answer the 4 questions |
| 3 | Clusters references by theme, shows the map with priorities (P0/P1/P2) | Confirm or say "move [file] to P0" |
| 4 | Shows reading plan: which to read fully, which to skim | Confirm or adjust reading depth |
| 5 | Reads references by tier, extracts arguments | Wait for Claude to finish |
| 6 | Outputs introduction + literature review draft | Review and request revisions |

**You can pause, adjust, or redirect Claude at any turn.**

---

### Supported Formats Matrix

| Format | Metadata Extracted | pages | word_count | Journal/Vol/Issue/Pages/DOI | Scan Detection | Dependencies |
|--------|-------------------|-------|-----------|---------------------------|----------------|--------------|
| **PDF** | Title, author, pages, word count, journal, vol/issue/pages, DOI, encryption detection | ✅ Real page count | ✅ Smart CJK/English mixed counting | ✅ First-page regex heuristics | ✅ Multi-page sampling | PyPDF2 + PyCryptodome + pdfplumber |
| **DOCX** | Title, author, word count, journal, vol/issue | ✅ Estimated (chars÷500) | ✅ Smart CJK/English mixed counting | ✅ First 5000 chars heuristics | ❌ No | python-docx |
| **TXT / MD** | Word count, journal, vol/issue | ✅ Estimated | ✅ Smart CJK/English mixed counting | ✅ First 3000 chars heuristics | ❌ No | Built-in |
| **EPUB** | Title, author, word count, journal, vol/issue | ✅ Estimated | ✅ Smart CJK/English mixed counting | ✅ First 3000 chars heuristics | ❌ No | ebooklib + beautifulsoup4 |
| **CAJ** | Filename only | ❌ | ❌ | ❌ | N/A | Prompts user to convert to PDF (CAJViewer / caj2pdf) |

### Performance & Incremental Features

| Feature | Description | Impact |
|---------|-------------|--------|
| **Environment pre-check** | `--env-check` detects missing deps, terminal encoding, encrypted PDFs, scanned PDFs | Prevents batch runtime failures |
| **Concurrent extraction** | `ThreadPoolExecutor(max_workers=4)` parallelizes file I/O | ~2-3x faster for 30+ files |
| **Incremental caching** | SHA-256 file hashing skips unchanged files on re-runs | Subsequent runs complete in seconds |
| **Smart page-reading strategy** | Short docs (≤50 pages) read fully; monographs (>50 pages) sample first 15 + last 5 | Avoids front-matter bias on monographs for scan detection and word counts |
| **Multi-page scan detection** | Samples beginning, middle, and end pages of PDFs | Greatly reduces false positives from image-only cover pages |
| **Duplicate detection** | Auto-flags duplicate references by title similarity (SequenceMatcher ≥80%) | Prevents multi-format duplicates from being cited twice |
| **Citation generation** | Auto-generates citations in GB/T 7714, APA, MLA, and numbered styles with journal/vol/issue/pages/DOI | Citations are ready for a real reference list |
| **Incomplete citation marker** | Automatically appends `〔文献信息不完整，请手动补全〕` when journal/publisher/year is missing | Prevents "looks right but is wrong" citations |
| **BibTeX export** | `--bibtex` outputs a `.bib` file with `@article`/`@book`/`@misc` auto-inference | Essential for LaTeX users |
| **BibTeX LaTeX escaping** | Auto-escapes `& % $ # _ { } ~ ^ \` to prevent `.bib` compilation errors | LaTeX users |
| **Recursive traversal** | Default `rglob("*")` discovers files in subfolders with `relative_path` preserved | Fits users who organize by topic/year |
| **Structured error logging** | Extraction failures are recorded in report notes | No more silent failures |
| **Scanned PDF guidance** | Report includes specific OCR tool recommendations (marker, nougat, tesseract) with install commands | Users know exactly what to do next |
| **Metadata fallback** | When PDF `/Title` or `/Author` is empty, heuristically extracts title/author/year from first-page text | Reduces "incomplete metadata" false positives |
| **Workflow checkpoint** | Writes `_els_stage.json` after Stage 1 so Claude can resume across multi-turn sessions | Supports long-running tasks with interruption recovery |

### Real-World Results

Tested on a corpus of **30 mixed Chinese/English references** (including 3 monographs of 200+ pages):

- **Input:** ~5M+ characters of full-text content
- **Processing cost:** ~30k characters of targeted reading (99.4% reduction)
- **Output:** 1,796-character introduction + 3,767-character literature review with 35 properly positioned citations

### Installation

```bash
mkdir -p ~/.claude/skills/
cp -r efficient-literature-survey ~/.claude/skills/
```

Dependencies:

```bash
pip install -r requirements.txt
```

### Usage

**Standalone script:**

```bash
python extract_literature_metadata.py /path/to/your/literature/folder
```

CLI flags:
- `--env-check` / `-e`: Run environment pre-check (deps / encoding / encrypted PDFs / scanned PDFs) without extraction
- `--max-pages N` / `-m N`: Force read only the first N pages (overrides smart paging)
- `--citation-style gb7714|apa|mla|numbered` / `-c STYLE`: Choose citation format (default: gb7714)
- `--output-dir PATH` / `-o PATH`: Specify output directory (default: `.els_output/` subfolder inside the literature folder)
- `--bibtex` / `-b`: Also output a BibTeX file `_literature_references.bib`
- `--verbose` / `-v`: DEBUG-level logging
- `--quiet` / `-q`: Only WARNING and above
- `--no-recursive`: Disable subfolder traversal

Interactive CLI features:
- No arguments → prompts for path interactively
- Path does not exist → prompts to re-enter
- No supported files found → lists what was detected and why they were skipped

Outputs:
- `_literature_extraction.json` — structured data (includes `duplicates`, `citation_style`, `results[].citation`)
- `_literature_report.md` — human-readable summary report (includes duplicate detection, OCR guidance, subfolder grouping, citation appendix)
- `_literature_references.bib` — BibTeX file (when `--bibtex` is used)

... Supports mixed folders of PDF / DOCX / TXT / MD / EPUB, including recursive subfolders

**Via Claude Code Skill:**

**Natural language triggers:**
- "Help me read papers and write an introduction and literature review"
- "Quickly understand a large number of references"
- "Save tokens reading papers"
- "I have 30 papers to write a literature review"
- ... More triggers in [SKILL.md](SKILL.md)

### Compatibility

| Component | Runtime | Notes |
|-----------|---------|-------|
| `extract_literature_metadata.py` | **Any Python environment** | Standalone script; works in terminal, Jupyter, VS Code, etc. |
| `SKILL.md` | **Claude Code only** | Requires Claude Code's skill system to be read and auto-triggered by AI |

If you don't use Claude Code, you can still use the **Python script standalone** for Stage 1 (batch extraction). Stages 2-4 must be done manually.

### Directory Structure

```
efficient-literature-survey/
├── SKILL.md                              # Core skill document for Claude (Claude Code only)
├── extract_literature_metadata.py        # CLI entry point (backward-compatible, any Python env)
├── test_extract_literature_metadata.py   # Unit tests (92+ test cases)
├── CHANGELOG.md                          # Version changelog
├── README.md                             # Chinese version
├── README_EN.md                          # English version (this file)
├── requirements.txt                      # Runtime dependencies
├── pyproject.toml                        # Python package metadata and build config
├── core/
│   ├── config.py                         # Centralized tunable constants (sampling thresholds, scan params)
│   ├── constants.py                      # SUPPORTED_EXTS, CAJ_EXT, compound surname table
│   ├── helpers.py                        # Core utilities (word count, scan detection, duplicates, metadata fallback)
│   └── logging_config.py                 # Logging setup
├── extractors/
│   ├── base.py                           # Result template factory
│   ├── pdf.py                            # PDF extractor
│   ├── docx.py                           # DOCX extractor
│   ├── txt.py                            # TXT/MD extractor
│   └── epub.py                           # EPUB extractor
├── citation/
│   ├── engine.py                         # Citation format engine (APA/MLA/GB)
│   └── bibtex.py                         # BibTeX generator
├── cache/
│   └── manager.py                        # Cache manager (version 2)
├── checkpoint/
│   └── manager.py                        # Workflow checkpoint persistence (multi-turn resume)
└── report/
    └── generator.py                      # Markdown report generator
```

### Developers

#### Module Architecture

This project uses a **modular architecture**, splitting the original 1,282-line monolithic script into cleanly separated submodules:

- **`core/`** — Constants, helper utilities, logging configuration
- **`extractors/`** — Format-specific extractors (PDF/DOCX/TXT/EPUB) with module-level lazy imports for optional dependencies
- **`citation/`** — Citation format engine + BibTeX generator
- **`cache/`** — Incremental cache based on SHA-256 + relative path (version 2)
- **`report/`** — Markdown report generator

#### Backward Compatibility

`extract_literature_metadata.py` remains the CLI entry point. All CLI arguments, output file formats, and JSON/Markdown structures are fully backward-compatible with pre-v1.2.0 releases. The cache auto-upgrades from `version: 1` to `version: 2`; old caches are ignored and rebuilt automatically — no breaking changes.

#### Running Tests

```bash
python -m unittest test_extract_literature_metadata.py -v
```

Current test coverage includes:
- Mock-based tests for PDF/DOCX/EPUB extractors (no optional dependencies required)
- Cache manager roundtrip tests
- Extractor dispatcher routing tests
- Integration tests for citation formats, BibTeX generation, and duplicate detection

---

### How It Saves Tokens

| Approach | Characters Read | Depth | Quality |
|----------|----------------|-------|---------|
| Read everything | 5,000,000+ | Shallow (context overflow) | Low |
| **This skill** | **~30,000** | **Deep (targeted excerpts)** | **High** |

The key insight: **academic writing doesn't need full-text comprehension** — it needs strategic extraction of arguments, gaps, and positioning statements.

---

### License

MIT
