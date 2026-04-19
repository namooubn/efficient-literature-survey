---
name: efficient-literature-survey
description: Use when the user needs to read a large number of literature references (10+) in PDF, DOCX, TXT, MD, or EPUB format and write a thesis introduction and literature review. Triggers include phrases like "帮我读文献", "写绪论和综述", "快速理解大量文献", "节省token读论文", "literature review", "thesis introduction", "batch read papers", "write my literature review", "帮我写文献综述", "批量读PDF写论文", "efficient literature survey", "save tokens reading papers", typing `/efficient-literature-survey`, or when the user has a folder of literature files and needs structured academic output.
---

# Efficient Literature Survey Workflow

## Overview

A five-stage workflow (Stage 0–4) that compresses millions of words of literature into a structured literature map, then writes a thesis introduction and literature review. **Core principle:** Never read every word — extract metadata, cluster by theme, and read only what the output needs.

**Supported formats:** PDF, DOCX (Word), TXT, MD (Markdown), EPUB. CAJ files are detected but require manual conversion to PDF first.

**Token savings:** Typical reduction from 5M+ characters (full-text reading) to ~30k characters (structured map + targeted excerpts), a **99%+ reduction**.

## When to Use

- User has 10-100 literature references (papers, monographs, mixed Chinese/English) in PDF, DOCX, TXT, MD, or EPUB format
- User needs to write a thesis introduction and/or literature review
- User mentions wanting to "save tokens" or "quickly understand" a large literature corpus
- The task involves extracting themes, finding research gaps, and positioning the user's study

**When NOT to use:**
- User has fewer than 5 papers (just read them directly)
- User only wants a simple summary of one paper
- The papers are non-academic (news clippings, legal filings without abstracts)

## Workflow

### Stage 0: User Configuration (Required)

**BEFORE running Stage 1, collect the following from the user. Do not proceed to Stage 4 without all five.**

| Config Item | Question to Ask | Examples |
|-------------|-----------------|----------|
| **Output language** | "What language should the output be in?" | Chinese, English, Japanese, etc. |
| **Citation format** | "What citation style should I use?" | APA, MLA, Chicago, GB/T 7714, author-year `(Smith, 2004)`, numbered `[1]`, etc. |
| **Chapter structure** | "Do you want to provide your own chapter structure, or use a default template?" | User says "custom" or "default" |
| **User research positioning** | "To judge relevance, please provide your thesis title, abstract, research question, OR 3-5 keywords — whichever is easiest for you." | "短视频平台算法推荐对新闻消费行为的影响" OR "algorithmic recommendation, news consumption, short video, platform logic, user behavior" |
| **Literature folder path** | "Where are your literature files located? Please provide the full folder path." | `/Users/alice/Documents/thesis/references` or `D:\论文\参考文献` |

**Research positioning — two input modes (user chooses whichever is easier):**

**Mode A: Full description (preferred)**
- Thesis title, abstract, or research question — any length, any detail.
- The more context, the more accurate the relevance scoring in Stage 2.

**Mode B: Keywords (lightweight)**
- 3-5 core keywords or key phrases.
- Enough for basic relevance matching if the user doesn't have a draft yet.

**Rules:**
- Accept **any** of the following: title, abstract, research question, keywords, or a mix. Do not force the user into a rigid format.
- If the user provides only keywords, treat it as Mode B and proceed. If they provide a paragraph, treat it as Mode A and proceed. Do not ask for "more" if what they gave is already usable.
- Record this positioning text at the top of the literature map document. Stage 2 uses it to score each cluster's relevance to the user's actual study.

**Chapter structure — two paths:**

**Path A: User provides custom structure**
- Ask: "Please provide your exact chapter/section hierarchy (e.g., 1.1 Background → 1.2 Significance → 1.3 Methods; 2.1 Concepts → 2.2 Theory → 2.3 Review)"
- Record verbatim. Stage 4 must follow this exactly.

**Path B: User chooses default template**
- Ask: "Which default template do you prefer — Chinese thesis structure or English thesis structure?"
- Present both options and let the user pick one.

**Default Chinese Thesis Structure:**
```
第一章 绪论
  1.1 研究背景与问题提出
  1.2 研究目的与意义（理论意义 + 实践意义）
  1.3 研究思路与方法概述

第二章 文献综述与理论框架
  2.1 核心概念界定
  2.2 理论基础与文献回顾（按主题簇组织）
  2.3 文献评述与研究空间（贡献 → 不足 → 本研究切入点）
```

**Default English Thesis Structure:**
```
Chapter 1 Introduction
  1.1 Research Background and Problem Statement
  1.2 Research Objectives and Significance
  1.3 Research Design and Methodology Overview

Chapter 2 Literature Review and Theoretical Framework
  2.1 Key Concepts and Definitions
  2.2 Theoretical Foundations and Literature Review (organized by thematic clusters)
  2.3 Critical Review and Research Gap (contributions → limitations → this study's entry point)
```

**Rules:**
- If the user has not provided all five configs, **ask before proceeding**. Do not guess.
- Record all five configs (language, citation format, chosen structure, research positioning, literature folder path) at the top of the literature map document for reference throughout the workflow.
- If the user chose "custom" but hasn't provided the structure yet, **hold at Stage 0** until they do.

### Stage 1: Batch Extract Literature Metadata

Run a Python script over the user's literature folder to extract:
- Title, author, year, page count, word count
- Estimated text volume (character count from first N pages)
- Scanned-image detection for PDFs (low text count on multi-page files)
- First-page preview text

**Supported formats:**
| Format | Metadata extracted | Scanned detection |
|--------|-------------------|-------------------|
| **PDF** | Title, author, pages, text chars, word count | Yes (heuristic) |
| **DOCX** | Title, author, text chars, word count | No |
| **TXT / MD** | Text chars, word count | No |
| **EPUB** | Title, author, text chars, word count | No |
| **CAJ** | Filename only | N/A (conversion required) |

**Output:** A structured table (JSON) listing all references with their extraction status.

**Decision points:**
- If a PDF is flagged as scanned (image-based), warn the user that OCR may be needed for full-text extraction, but metadata (title/author) may still be readable.
- If CAJ files are detected, instruct the user to convert them to PDF using CAJViewer or `caj2pdf` before re-running the script.

### Stage 2: Build Literature Map (Cluster + Prioritize)

**Inputs:**
1. Extracted metadata (titles, previews, page counts) from Stage 1
2. User research positioning from Stage 0 (title/abstract/research question/keywords)

**Step 1: Cluster by theme**
Group references into **5-8 thematic clusters** based on their titles and preview texts, for example:

| Cluster | Theme | Count |
|---------|-------|-------|
| A | Core theory (e.g., agenda-setting) | 4-6 |
| B | Counter-flow / reverse mechanisms | 3-5 |
| C | Meme / digital culture theory | 3-5 |
| D | Platform logic / governance | 2-4 |
| E | Case methodology | 1-2 |
| F | Weakly related / tangential | 2-5 |

**Step 2: Score relevance against user's study**
Compare each cluster's theme against the user's research positioning (Stage 0). Assign a **relevance score**:

| Score | Meaning | Action |
|-------|---------|--------|
| **Direct** | Cluster directly addresses the user's research question or core concepts | → P0 |
| **Adjacent** | Cluster provides supporting theory, method, or context | → P1 |
| **Peripheral** | Cluster is broadly in the same field but not closely tied to the user's gap | → P2 |
| **Tangential** | Cluster has minimal connection to the user's study | → Exclude or note only |

**Example:**
- User's positioning: "短视频平台中算法推荐对新闻消费行为的影响"
- Cluster A "算法推荐机制" → **Direct** → P0
- Cluster B "平台治理与内容审核" → **Adjacent** → P1
- Cluster C "传统报业数字化转型" → **Peripheral** → P2
- Cluster D "广告竞价策略" → **Tangential** → Exclude

**Prioritization tiers:**
- **P0 (Core):** 5-8 references that anchor the theoretical framework. Read full text.
- **P1 (Support):** 15-20 references. Read abstract + conclusion + sections directly relevant to the user's research question.
- **P2 (Background):** Remaining references. Read abstract only; confirm their positioning sentence (e.g., "This paper reviews early work in X").

**Output:** A literature map document listing each reference with its cluster, relevance score, priority tier, and intended citation location in the thesis structure.

### Stage 3: Targeted Reading by Tier

**For P0 references:**
- Use Read tool on the full text (if extracted) or key chapters.
- Extract: core argument, key quotations, theoretical lineage, methodological approach.

**For P1 references:**
- Read abstract and conclusion.
- Search within the document for keywords matching the user's research question.
- Extract: 2-3 sentences summarizing contribution + how it connects to the user's gap.

**For P2 references:**
- Confirm from abstract: what does this paper do? Where does it fit in the map?
- Write a one-sentence positioning note.

**For scanned monographs (300+ pages):**
- Do NOT attempt OCR of the entire book.
- Extract table of contents if available; identify 2-3 core chapters.
- Read only those chapters or search for keywords to locate relevant passages.

### Stage 4: Structured Writing

Write the introduction and literature review according to the **user's prescribed chapter structure** (collected in Stage 0). **Do not use any default template unless the user explicitly chose "default structure."**

**Writing rules:**
- **Strictly use the user's chapter structure.** If the user hasn't provided it, you must ask in Stage 0 — never guess.
- Cite in the user's required format (e.g., numbered `[1]`, author-year `(McCombs, 2004)`, APA, MLA, etc.).
- Use P0 references for deep theoretical anchoring.
- Use P1 references for empirical support and secondary claims.
- Use P2 references sparingly, mainly for breadth or historical positioning.
- Every claim in the review must be traceable to a specific reference.
- In the final section (typically the "gap analysis" section), explicitly name the research gap and state how the user's study fills it.
- Write in the user's specified output language.

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
| DOCX / EPUB / TXT / MD files | Process normally via the updated script |

## Common Mistakes

1. **Reading everything.** Agents often default to opening every file. This burns context and produces shallow understanding. Always extract metadata first.
2. **No clustering.** Without thematic clusters, the literature review becomes a list of summaries rather than an argument. Clusters create the review's narrative arc.
3. **Clustering without user positioning.** Clustering based only on literature titles produces generic groupings. Without the user's research positioning (title/abstract/keywords), relevance scoring is pure guesswork and P0/P1/P2 tiers may be completely wrong.
4. **Guessing the thesis structure.** If the user hasn't provided the exact heading hierarchy (e.g., 2.2.1 vs 2.2.2), ask in Stage 0 before writing. A mismatched structure requires full rewrite.
5. **Ignoring weak references.** Weak or tangential references should be explicitly flagged and potentially excluded. Citing irrelevant papers damages credibility.
6. **Skipping the gap analysis.** A literature review without a clear "what's missing → here's my study" transition fails its purpose. Stage 4 must end with the user's research positioning.
7. **Skipping Stage 0 configuration.** Writing without confirming language, citation format, chapter structure, research positioning, and literature folder path guarantees a mismatch with user expectations. Stage 0 is a hard prerequisite.

## Reusable Tool

**`extract_literature_metadata.py`** — Batch-extracts titles, authors, page counts, word counts, text volume, and scanned-page detection from a folder of literature files (PDF, DOCX, TXT, MD, EPUB). CAJ files are flagged with a conversion note.

See [`extract_literature_metadata.py`](extract_literature_metadata.py) for the script.

**Dependencies:**
```bash
pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
```

## Real-World Impact

Applied to a corpus of **30 mixed Chinese/English references** (including 3 monographs of 200+ pages each):
- Full-text reading would require ~5M+ characters of context.
- After metadata extraction + clustering, targeted reading consumed ~30k characters of full-text input.
- Produced a **1,796-character introduction** and a **3,767-character literature review** with 35 properly positioned citations, organized into 8 thematic clusters.
