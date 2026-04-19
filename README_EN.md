# efficient-literature-survey

[Chinese](README.md) | **English**

---

## What It Does

Transforms a folder of 10-100 literature files (PDF, DOCX, TXT, MD, EPUB) into a structured literature map, then writes a complete thesis introduction and literature review — without reading every word.

Supports **custom chapter structures** or **default templates** (Chinese / English thesis frameworks), automatically adapting to the user's specified citation format and output language.

| Stage | Action | Output |
|-------|--------|--------|
| 1. Batch Extract | Script extracts metadata from all literature files | JSON report with titles, authors, pages, word count, text volume, scan detection |
| 2. Cluster & Prioritize | Group into 5-8 thematic clusters | Literature map with P0/P1/P2 reading tiers |
| 3. Targeted Reading | Read by tier (full / abstract+conclusion / abstract only) | Extracted arguments and quotes |
| 4. Structured Writing | Write according to user's chapter framework | Formatted introduction + review draft |

### Supported Formats Matrix

| Format | Metadata Extracted | pages | word_count | Scan Detection | Dependencies |
|--------|-------------------|-------|-----------|----------------|--------------|
| **PDF** | Title, author, pages, word count, text volume | ✅ Real page count | ✅ | ✅ Yes | PyPDF2 + pdfplumber |
| **DOCX** | Title, author, word count, text volume | ✅ Estimated (chars÷500) | ✅ | ❌ No | python-docx |
| **TXT / MD** | Word count, text volume | ✅ Estimated | ✅ | ❌ No | Built-in |
| **EPUB** | Title, author, word count, text volume | ✅ Estimated | ✅ | ❌ No | ebooklib + beautifulsoup4 |
| **CAJ** | Filename only | ❌ | ❌ | N/A | Prompts user to convert to PDF (CAJViewer / caj2pdf) |

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
pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
```

### Usage

**Standalone script:**

```bash
python extract_literature_metadata.py /path/to/your/literature/folder
```

... More CLI options via `--help`

**Via Claude Code Skill:**

**Direct trigger (recommended):** Type `/efficient-literature-survey` in the input box and press Enter.

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
├── SKILL.md                         # Core skill document for Claude (Claude Code only)
├── extract_literature_metadata.py   # Standalone batch extraction script (any Python env)
├── extract_pdf_metadata.py          # Legacy PDF-only script (backward compatible)
├── README.md                        # Chinese version
└── README_EN.md                     # English version (this file)
```

### How It Saves Tokens

| Approach | Characters Read | Depth | Quality |
|----------|----------------|-------|---------|
| Read everything | 5,000,000+ | Shallow (context overflow) | Low |
| **This skill** | **~30,000** | **Deep (targeted excerpts)** | **High** |

The key insight: **academic writing doesn't need full-text comprehension** — it needs strategic extraction of arguments, gaps, and positioning statements.

---

### License

MIT
