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
    <td>Confirm language, citation format, chapter structure, <b>research positioning</b> (title/abstract/keywords — any is fine), <b>literature folder path</b></td>
    <td>Config checklist + user study positioning</td>
  </tr>
  <tr>
    <td>1. Extract</td>
    <td>Script extracts metadata from all literature files</td>
    <td>JSON report + Markdown summary (titles/authors/pages/word count/text volume/scan detection)</td>
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
    <td>Write according to user's chapter framework</td>
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
pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
```

**Step 2: Open Claude Code and say**

> "Help me write a literature review. My references are in `/Users/alice/Documents/references`."

**Step 3: Claude will guide you through this flow**

| Turn | What Claude Does | What You Do |
|------|-----------------|-------------|
| 1 | Scans the folder, tells you how many files, what formats, any scanned PDFs | Check the count, confirm |
| 2 | Asks: language, citation style, research topic, chapter structure template | Answer the 4 questions |
| 3 | Clusters references by theme, shows the map with priorities (P0/P1/P2) | Confirm or say "move [file] to P0" |
| 4 | Shows reading plan: which to read fully, which to skim | Confirm or adjust reading depth |
| 5 | Reads references by tier, extracts arguments | Wait for Claude to finish |
| 6 | Outputs introduction + literature review draft | Review and request revisions |

**You can pause, adjust, or redirect Claude at any turn.**

---

### Supported Formats Matrix

| Format | Metadata Extracted | pages | word_count | Scan Detection | Dependencies |
|--------|-------------------|-------|-----------|----------------|--------------|
| **PDF** | Title, author, pages, word count, text volume | ✅ Real page count | ✅ Smart CJK/English mixed counting | ✅ Yes | PyPDF2 + pdfplumber |
| **DOCX** | Title, author, word count, text volume | ✅ Estimated (chars÷500) | ✅ Smart CJK/English mixed counting | ❌ No | python-docx |
| **TXT / MD** | Word count, text volume | ✅ Estimated | ✅ Smart CJK/English mixed counting | ❌ No | Built-in |
| **EPUB** | Title, author, word count, text volume | ✅ Estimated | ✅ Smart CJK/English mixed counting | ❌ No | ebooklib + beautifulsoup4 |
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

Interactive CLI features:
- No arguments → prompts for path interactively
- Path does not exist → prompts to re-enter
- No supported files found → lists what was detected and why they were skipped

Outputs:
- `_literature_extraction.json` — structured data
- `_literature_report.md` — human-readable summary report

... Supports mixed folders of PDF / DOCX / TXT / MD / EPUB

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
