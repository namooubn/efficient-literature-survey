# efficient-literature-survey

<p align="right">
  <a href="README.md">中文</a> | <b>English</b>
</p>

---

A Claude Code skill for efficiently processing large numbers of PDF references and writing thesis introductions (绪论) and literature reviews (文献综述) with **99%+ token savings**.

## What It Does

Transforms a folder of 10–100 PDFs into a structured literature map, then writes a complete thesis introduction and literature review — without reading every word.

| Stage | Action | Output |
|-------|--------|--------|
| 1. Batch Extract | Script extracts metadata from all PDFs | JSON report with titles, authors, pages, text volume, scan detection |
| 2. Cluster & Prioritize | Group into 5–8 thematic clusters | Literature map with P0/P1/P2 reading tiers |
| 3. Targeted Reading | Read by tier (full / abstract+conclusion / abstract only) | Extracted arguments and quotes |
| 4. Structured Writing | Write according to user's chapter framework | Formatted introduction + review draft |

## Real-World Results

Tested on a corpus of **30 mixed Chinese/English PDFs** (including 3 monographs of 200+ pages):

- **Input:** ~5M+ characters of full-text content
- **Processing cost:** ~30k characters of targeted reading (99.4% reduction)
- **Output:** 1,796-character introduction + 3,767-character literature review with 35 properly positioned citations

## Installation

```bash
mkdir -p ~/.claude/skills/
cp -r efficient-literature-survey ~/.claude/skills/
```

Dependencies:

```bash
pip install PyPDF2 pdfplumber
```

## Usage

**Standalone script:**

```bash
python extract_pdf_metadata.py /path/to/your/pdf/folder
```

**Via Claude Code Skill:**

Auto-triggers when you say:
- "帮我读文献写绪论和综述"
- "快速理解大量PDF"
- "节省token读论文"
- "I have 30 papers to write a literature review"

## Directory Structure

```
efficient-literature-survey/
├── SKILL.md                  # Core skill document (read by Claude)
├── extract_pdf_metadata.py   # Standalone batch extraction script
├── README.md                 # Chinese documentation
└── README_EN.md              # English documentation
```

## Compatibility

| Component | Runtime | Notes |
|-----------|---------|-------|
| `extract_pdf_metadata.py` | **Any Python environment** | Standalone script; works in terminal, Jupyter, VS Code, etc. |
| `SKILL.md` | **Claude Code only** | Requires Claude Code's skill system to be read and auto-triggered by AI |

If you don't use Claude Code, you can still use the **Python script standalone** for Stage 1 (batch extraction). Stages 2–4 must be done manually.

## How It Saves Tokens

| Approach | Characters Read | Depth | Quality |
|----------|----------------|-------|---------|
| Read everything | 5,000,000+ | Shallow (context overflow) | Low |
| **This skill** | **~30,000** | **Deep (targeted excerpts)** | **High** |

The key insight: **academic writing doesn't need full-text comprehension** — it needs strategic extraction of arguments, gaps, and positioning statements.

---

## License

MIT
