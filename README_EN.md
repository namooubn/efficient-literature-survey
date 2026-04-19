# efficient-literature-survey

[Chinese](README.md) | **English**

---

## What It Does

Transforms a folder of 10-100 PDFs into a structured literature map, then writes a complete thesis introduction and literature review — without reading every word.

| Stage | Action | Output |
|-------|--------|--------|
| 1. Batch Extract | Script extracts metadata from all PDFs | JSON report with titles, authors, pages, text volume, scan detection |
| 2. Cluster & Prioritize | Group into 5-8 thematic clusters | Literature map with P0/P1/P2 reading tiers |
| 3. Targeted Reading | Read by tier (full / abstract+conclusion / abstract only) | Extracted arguments and quotes |
| 4. Structured Writing | Write according to user's chapter framework | Formatted introduction + review draft |

### Real-World Results

Tested on a corpus of **30 mixed Chinese/English PDFs** (including 3 monographs of 200+ pages):

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
pip install PyPDF2 pdfplumber
```

### Usage

**Standalone script:**

```bash
python extract_pdf_metadata.py /path/to/your/pdf/folder
```

**Via Claude Code Skill:**

Auto-triggers when you say:
- "Help me read papers and write an introduction and literature review"
- "Quickly understand a large number of PDFs"
- "Save tokens reading papers"
- "I have 30 papers to write a literature review"

### Compatibility

| Component | Runtime | Notes |
|-----------|---------|-------|
| `extract_pdf_metadata.py` | **Any Python environment** | Standalone script; works in terminal, Jupyter, VS Code, etc. |
| `SKILL.md` | **Claude Code only** | Requires Claude Code's skill system to be read and auto-triggered by AI |

If you don't use Claude Code, you can still use the **Python script standalone** for Stage 1 (batch extraction). Stages 2-4 must be done manually.

### Directory Structure

```
efficient-literature-survey/
├── SKILL.md                  # Core skill document for Claude (Claude Code only)
├── extract_pdf_metadata.py   # Standalone batch extraction script (any Python env)
├── README.md                 # Chinese version
└── README_EN.md              # English version (this file)
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
