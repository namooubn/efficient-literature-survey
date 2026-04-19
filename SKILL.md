---
name: efficient-literature-survey
description: Use when the user needs to batch-read academic literature (10+ files in PDF/DOCX/TXT/MD/EPUB) and write a thesis introduction or literature review. Triggers on phrases like "帮我读文献", "literature review", "batch read papers", or when the user has a folder of literature files needing structured academic output.
---

# Efficient Literature Survey Workflow

## Overview

A five-stage workflow (Stage 0–4) that compresses millions of words of literature into a structured literature map, then writes a thesis introduction and literature review. **Core principle:** Never read every word — extract metadata, cluster by theme, and read only what the output needs.

**Supported formats:** PDF, DOCX, TXT, MD, EPUB. CAJ files are detected but require manual conversion to PDF first.

**Token savings:** Typical reduction from 5M+ characters (full-text reading) to ~30k characters (structured map + targeted excerpts), a **99%+ reduction**.

## Triggers

- "帮我读文献", "写绪论和综述", "快速理解大量文献", "节省token读论文"
- "帮我写文献综述", "批量读PDF写论文"
- "literature review", "thesis introduction", "batch read papers"
- "efficient literature survey", "save tokens reading papers"
- User has a folder of literature files and needs structured academic output

## When to Use

- User has 10-100 literature references (papers, monographs, mixed Chinese/English)
- User needs to write a thesis introduction and/or literature review
- User mentions wanting to "save tokens" or "quickly understand" a large corpus

**When NOT to use:**
- User has fewer than 5 papers (just read them directly)
- User only wants a simple summary of one paper
- The papers are non-academic (news clippings, legal filings without abstracts)

## Two Starting Modes

### Mode A: Guided Start (default)

If the user has given a literature folder but has not yet confirmed the five Stage 0 configs, do NOT bombard them with five questions upfront. Instead:

1. **Run Stage 1 immediately** using the `extract_literature_metadata.py` script on the user's folder.
2. **Show the results in a table** — this gives the user immediate tangible feedback and builds trust.
3. **Then ask for the remaining Stage 0 configs** one at a time, or in a single compact message.

### Mode B: Full Config Start

If the user proactively gives language, citation format, chapter structure, research positioning, and folder path all at once, skip straight to Stage 1.

## Workflow

### Stage 0: User Configuration (Required)

**BEFORE proceeding to Stage 2, collect the following. Do not proceed to Stage 4 without all five.**

| Config Item | Question to Ask |
|-------------|-----------------|
| **Output language** | "What language should the output be in?" |
| **Citation format** | "What citation style should I use?" (APA, MLA, GB/T 7714, numbered `[1]`, etc.) |
| **Chapter structure** | "Custom structure or default template (Chinese/English thesis)?" |
| **User research positioning** | "Thesis title, abstract, research question, OR 3-5 keywords — whichever is easiest." |
| **Literature folder path** | "Where are your literature files located?" |

Accept **any** of: title, abstract, research question, keywords, or a mix. Do not force the user into a rigid format.

If the user chose "custom" but hasn't provided the structure yet, **hold at Stage 0** until they do.

### Stage 1: Batch Extract Literature Metadata

Run `extract_literature_metadata.py` over the user's literature folder to extract:
- Title, author, year, page count, word count
- Estimated text volume (character count from first N pages)
- Scanned-image detection for PDFs
- First-page preview text

**Output:** A structured JSON table and a Markdown report (`_literature_report.md`).

**Decision points:**
- If a PDF is flagged as scanned, warn the user that OCR may be needed.
- If CAJ files are detected, instruct the user to convert them to PDF before re-running.

**[USER_CHECKPOINT]: After presenting Stage 1 results, WAIT for user acknowledgment before proceeding to Stage 2.**

### Stage 2: Build Literature Map (Cluster + Prioritize)

**Inputs:** Extracted metadata (titles, previews) from Stage 1 + user research positioning from Stage 0.

**Step 1: Cluster by theme** — Group references into **5-8 thematic clusters** based on titles and preview texts.

**Step 2: Score relevance** — Assign a relevance score to each cluster:

| Score | Meaning | Action |
|-------|---------|--------|
| **Direct** | Directly addresses the user's research question | → P0 |
| **Adjacent** | Provides supporting theory, method, or context | → P1 |
| **Peripheral** | Broadly in the same field but not closely tied | → P2 |
| **Tangential** | Minimal connection | → Exclude |

**Prioritization tiers:**
- **P0 (Core):** 5-8 references. Read full text.
- **P1 (Support):** 15-20 references. Read abstract + conclusion + keyword-matched sections.
- **P2 (Background):** Remaining references. Read abstract only.

**[CONTEXT_OVERFLOW] guard:** If >40 references, filter by format or cluster in batches.

**[USER_CHECKPOINT]: Present the complete literature map and WAIT for confirmation.** Show clusters, relevance scores, and proposed reading strategy. Ask the user to confirm or adjust before proceeding.

### Stage 3: Targeted Reading by Tier

**[USER_CHECKPOINT]: Before starting Stage 3, present the reading plan for confirmation.** Show which P0/P1/P2 references you will read at what depth, and any scanned monographs strategy.

**For P0 references (full-text or structured read):**
1. Read the first 2,000 characters to identify structure.
2. If ≤ 50,000 characters, read the entire file.
3. If > 50,000 characters, read abstract + conclusion first, then 2-3 key chapters.
4. Extract: core argument, 2-3 direct quotations, theoretical lineage, methodological approach.

**For P1 references (abstract + keyword-targeted sections):**
1. Read the first 2,000 characters (abstract + introduction).
2. Read the last 1,500 characters (conclusion / discussion).
3. If keywords appear in preview text, read matched sections (± 500 chars around each match).
4. Extract: 2-3 sentences summarizing contribution + how it connects to the user's research gap.

**For P2 references (abstract only):**
1. Read the first 1,000 characters (abstract).
2. Confirm what the paper does and where it fits in the thematic map.
3. Write a one-sentence positioning note.

**[CONTEXT_OVERFLOW] guard:** If combined P0 + P1 text exceeds 100,000 words, downgrade all P1 to "abstract only" and keep only top 5 P0 for full reading.

**[USER_CHECKPOINT]: After Stage 3, present a brief reading summary.** Summarize key arguments from P0, how P1 supports the gap, and any surprises. Ask if satisfied before proceeding.

### Stage 4: Structured Writing

Write the introduction and literature review according to the **user's prescribed chapter structure** (collected in Stage 0). Do not use any default template unless the user explicitly chose "default structure."

**Writing rules:**
- Strictly use the user's chapter structure.
- Cite in the user's required format.
- Use P0 references for deep theoretical anchoring.
- Use P1 references for empirical support and secondary claims.
- Use P2 references sparingly, mainly for breadth or historical positioning.
- Every claim must be traceable to a specific reference.
- In the final section, explicitly name the research gap and state how the user's study fills it.
- Write in the user's specified output language.

**[USER_CHECKPOINT]: After Stage 4 output, ask for revision feedback.** Present the draft and ask the user to confirm structure, citation format, reference accuracy, and gap analysis.

## Tool Use

### Bash — Run the extraction script

**When to use:** At the start of Stage 1, after the user has provided the literature folder path.

```bash
python extract_literature_metadata.py <folder_path> [--max-pages N] [--citation-style STYLE] [--output-dir PATH]
```

**Rules:**
- Always use the full path (expand `~` if needed).
- If missing dependencies, ask the user to run `pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4`.
- Read the generated `_literature_report.md` to present results.

### Read — Read individual papers by tier

**When to use:** During Stage 3 (Targeted Reading).

| Tier | Strategy |
|------|----------|
| **P0 (Core)** | Full text if ≤ 50k chars; otherwise first 2k chars + key chapters |
| **P1 (Support)** | First 2k chars + last 1.5k chars + keyword-matched sections |
| **P2 (Background)** | First 1k chars (abstract) only |

**Context overflow guard:** If combined P0 + P1 text exceeds 100k chars, downgrade all P1 to "abstract only" and keep only top 5 P0.

### Write — Save the literature map and draft

**When to use:** After Stage 2 (clustering) and Stage 4 (writing).

**Files to write:**
- `_literature_map.md` — cluster assignments, relevance scores, and reading plan
- `_thesis_introduction.md` and/or `_literature_review.md` — Stage 4 output

## Quick Reference

| Situation | Action |
|-----------|--------|
| User has 30+ files in a folder | Run Stage 1 script immediately |
| PDF is scanned/image-based | Flag it; read TOC or do targeted OCR on key pages only |
| Monograph >200 pages | Extract TOC, identify 2-3 relevant chapters, ignore the rest |
| User hasn't provided chapter structure | Ask for it in Stage 0 before writing; do not guess |
| User hasn't provided research positioning | Ask for title/abstract/keywords in Stage 0; do not cluster blindly |
| Reference is weakly related | Exclude from citation list; note it in the map as "tangential" |
| User wants to "save tokens" | Emphasize the P0/P1/P2 tier system |
| CAJ files detected | Instruct user to convert to PDF using CAJViewer or caj2pdf |
| User only gave a folder path | Use **Mode A Guided Start** — run Stage 1 first, then collect configs |

## Common Mistakes

- **Reading everything** — Extract metadata first. Opening every file burns context.
- **No clustering** — Without thematic clusters, the review becomes a list of summaries rather than an argument.
- **Clustering without user positioning** — Relevance scoring is guesswork without the user's research positioning.
- **Guessing the thesis structure** — Ask for the exact heading hierarchy in Stage 0. A mismatched structure requires a full rewrite.
- **Ignoring weak references** — Tangential references should be flagged and potentially excluded.
- **Skipping the gap analysis** — Stage 4 must end with the user's research positioning.
- **Skipping Stage 0 configuration** — Writing without confirming all five configs guarantees a mismatch.
- **Auto-advancing without user confirmation** — Each `[USER_CHECKPOINT]` exists for a reason. Do not silently proceed.

## Reusable Tool

**`extract_literature_metadata.py`** — Batch-extracts titles, authors, page counts, word counts, text volume, and scanned-page detection from a folder of literature files. Outputs both JSON and Markdown.

**Dependencies:**
```bash
pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
```

## Real-World Impact

Applied to a corpus of **30 mixed Chinese/English references** (including 3 monographs of 200+ pages each):
- Full-text reading would require ~5M+ characters of context.
- After metadata extraction + clustering, targeted reading consumed ~30k characters.
- Produced a **1,796-character introduction** and a **3,767-character literature review** with 35 properly positioned citations, organized into 8 thematic clusters.
