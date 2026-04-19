---
name: efficient-literature-survey
description: Use when the user needs to read a large number of PDF references (10+) and write a thesis introduction (绪论) and literature review (文献综述). Triggers include phrases like "帮我读文献", "写绪论和综述", "快速理解大量文献", "节省token读论文", or when the user has a folder of PDFs and needs structured academic output.
---

# Efficient Literature Survey Workflow

## Overview

A four-stage workflow that compresses millions of words of PDFs into a structured literature map, then writes a thesis introduction and literature review. **Core principle:** Never read every word — extract metadata, cluster by theme, and read only what the output needs.

**Token savings:** Typical reduction from 5M+ characters (full-text reading) to ~30k characters (structured map + targeted excerpts), a **99%+ reduction**.

## When to Use

- User has 10–100 PDF references (papers, monographs, mixed Chinese/English)
- User needs to write **绪论** (thesis introduction) and/or **文献综述** (literature review)
- User mentions wanting to "save tokens" or "quickly understand" a large literature corpus
- The task involves extracting themes, finding research gaps, and positioning the user's study

**When NOT to use:**
- User has fewer than 5 papers (just read them directly)
- User only wants a simple summary of one paper
- The papers are non-academic (news clippings, legal filings without abstracts)

## Workflow

### Stage 1: Batch Extract PDF Metadata

Run a Python script over the user's PDF folder to extract:
- Title, author, year, page count
- Estimated text volume (character count from first N pages)
- Scanned-image detection (low text count on multi-page PDFs)
- First-page preview text

**Output:** A structured table (CSV/JSON/TXT) listing all references with their extraction status.

**Decision point:** If a PDF is flagged as scanned (image-based), warn the user that OCR may be needed for full-text extraction, but metadata (title/author) may still be readable.

### Stage 2: Build Literature Map (Cluster + Prioritize)

Based on the extracted metadata (titles, previews, page counts), cluster references into **5–8 thematic clusters**, for example:

| Cluster | Theme | Count | Strategy |
|---------|-------|-------|----------|
| A | Core theory (e.g., agenda-setting) | 4–6 | P0: Full-text精读 |
| B | Counter-flow / reverse mechanisms | 3–5 | P0–P1 |
| C | Meme / digital culture theory | 3–5 | P0–P1 |
| D | Platform logic / governance | 2–4 | P1 |
| E | Case methodology | 1–2 | P1 |
| F | Weakly related / tangential | 2–5 | P2 or exclude |

**Prioritization tiers:**
- **P0 (Core):** 5–8 references that anchor the theoretical framework. Read full text.
- **P1 (Support):** 15–20 references. Read abstract + conclusion + sections directly relevant to the user's research question.
- **P2 (Background):** Remaining references. Read abstract only; confirm their positioning sentence ("该文综述了X领域早期工作").

**Output:** A literature map document listing each reference with its cluster, priority tier, and intended citation location in the thesis structure.

### Stage 3: Targeted Reading by Tier

**For P0 references:**
- Use Read tool on the full PDF text (if extracted) or key chapters.
- Extract: core argument, key quotations, theoretical lineage, methodological approach.

**For P1 references:**
- Read abstract and conclusion.
- Search within PDF for keywords matching the user's research question.
- Extract: 2–3 sentences summarizing contribution + how it connects to the user's gap.

**For P2 references:**
- Confirm from abstract: what does this paper do? Where does it fit in the map?
- Write a one-sentence positioning note.

**For scanned monographs (300+ pages):**
- Do NOT attempt OCR of the entire book.
- Extract table of contents if available; identify 2–3 core chapters.
- Read only those chapters or search for keywords to locate relevant passages.

### Stage 4: Structured Writing

Write the introduction and literature review according to the user's prescribed chapter structure. Typical Chinese thesis structure:

**绪论 (Introduction):**
1.1 研究背景与问题提出
1.2 研究目的与意义（理论意义 + 实践意义）
1.3 研究思路与方法概述

**文献综述 (Literature Review):**
2.1 核心概念界定
2.2 理论基础与文献回顾（按主题簇组织）
2.3 文献评述与研究空间（贡献 → 不足 → 本研究切入点）

**Writing rules:**
- Cite in the user's required format (e.g., 顺序编码制 `[1]`, 著者-出版年制 `(McCombs, 2004)`).
- Use P0 references for deep theoretical anchoring.
- Use P1 references for empirical support and secondary claims.
- Use P2 references sparingly, mainly for breadth or historical positioning.
- Every claim in the review must be traceable to a specific reference.
- In 2.3, explicitly name the research gap and state how the user's study fills it.

## Quick Reference

| Situation | Action |
|-----------|--------|
| User has 30+ PDFs in a folder | Run Stage 1 script immediately |
| PDF is scanned/image-based | Flag it; read TOC or do targeted OCR on key pages only |
| Monograph >200 pages | Extract TOC, identify 2–3 relevant chapters, ignore the rest |
| User hasn't provided chapter structure | Ask for it before writing; do not guess |
| Reference is weakly related | Exclude from citation list; note it in the map as "tangential" |
| User wants to "save tokens" | Emphasize the P0/P1/P2 tier system |

## Common Mistakes

1. **Reading everything.** Agents often default to opening every PDF. This burns context and produces shallow understanding. Always extract metadata first.
2. **No clustering.** Without thematic clusters, the literature review becomes a list of summaries rather than an argument. Clusters create the review's narrative arc.
3. **Guessing the thesis structure.** If the user hasn't provided the exact heading hierarchy (e.g., 2.2.1 vs 2.2.2), ask before writing. A mismatched structure requires full rewrite.
4. **Ignoring weak references.** Weak or tangential references should be explicitly flagged and potentially excluded. Citing irrelevant papers damages credibility.
5. **Skipping the gap analysis.** A literature review without a clear "what's missing → here's my study" transition fails its purpose. Stage 4 must end with the user's research positioning.

## Reusable Tool

**`extract_pdf_metadata.py`** — Batch-extracts titles, authors, page counts, text volume, and scanned-page detection from a folder of PDFs.

See [`extract_pdf_metadata.py`](extract_pdf_metadata.py) for the script.

## Real-World Impact

Applied to a corpus of **30 mixed Chinese/English PDFs** (including 3 monographs of 200+ pages each):
- Full-text reading would require ~5M+ characters of context.
- After metadata extraction + clustering, targeted reading consumed ~30k characters of full-text input.
- Produced a **1,796-character introduction** and a **3,767-character literature review** with 35 properly positioned citations, organized into 8 thematic clusters.
