---
name: efficient-literature-survey
description: Use when the user needs to batch-read academic literature (10+ files in PDF/DOCX/TXT/MD/EPUB) and write a thesis introduction or literature review. Triggers on phrases like "帮我读文献", "literature review", "batch read papers", or when the user has a folder of literature files needing structured academic output.
---

# Efficient Literature Survey Workflow

## Overview

A five-stage workflow (Stage 0–4) that compresses millions of words of literature into a structured literature map, then writes a thesis introduction and literature review. **Core principle:** Never read every word — extract metadata, cluster by theme, and read only what the output needs.

**Supported formats:** PDF, DOCX (Word), TXT, MD (Markdown), EPUB. CAJ files are detected but require manual conversion to PDF first.

**Token savings:** Typical reduction from 5M+ characters (full-text reading) to ~30k characters (structured map + targeted excerpts), a **99%+ reduction**.

## Triggers

Natural-language triggers that activate this skill:
- "帮我读文献", "写绪论和综述", "快速理解大量文献", "节省token读论文"
- "帮我写文献综述", "批量读PDF写论文"
- "literature review", "thesis introduction", "batch read papers", "write my literature review"
- "efficient literature survey", "save tokens reading papers"
- Typing `/efficient-literature-survey`
- User has a folder of literature files and needs structured academic output

## When to Use

- User has 10-100 literature references (papers, monographs, mixed Chinese/English) in PDF, DOCX, TXT, MD, or EPUB format
- User needs to write a thesis introduction and/or literature review
- User mentions wanting to "save tokens" or "quickly understand" a large literature corpus
- The task involves extracting themes, finding research gaps, and positioning the user's study

**When NOT to use:**
- User has fewer than 5 papers (just read them directly)
- User only wants a simple summary of one paper
- The papers are non-academic (news clippings, legal filings without abstracts)

## Two Starting Modes

### Mode A: Guided Start (default — when user has not provided all config)

If the user has given you a literature folder but has not yet confirmed the five Stage 0 configs, **do NOT bombard them with five questions upfront**. Instead, take the fastest action path:

1. **Run Stage 1 immediately** using the `extract_literature_metadata.py` script on the user's folder. Present the results (how many files found, formats detected, scan warnings).
2. **Show the results in a table** — this gives the user immediate tangible feedback and builds trust.
3. **Then ask for the remaining Stage 0 configs** one at a time, or in a single compact message. The user now sees that "something is already working" and is more willing to fill in the rest.

**Example opening when user says "帮我读文献写综述，文献在 D:\论文\references":**

> 好的，我先扫描一下你的文献文件夹，看看有多少篇、都是什么格式。
>
> ...（运行脚本）...
>
> ✅ 找到 34 篇文献：PDF 28 篇，DOCX 4 篇，TXT 2 篇
> ⚠️ 其中 3 篇 PDF 是扫描件（需 OCR）
>
> 在开始之前，我还需要确认几个信息：
> 1. 输出语言：中文还是英文？
> 2. 引用格式：比如 APA、GB/T 7714、还是 `[1]` 编号格式？
> 3. 你的研究题目或关键词是什么？（用于判断文献相关性）
> 4. 你学校的章节结构模板是怎样的？（没有的话我提供默认模板）

### Mode B: Full Config Start (when user has already provided all 5 configs)

If the user proactively gives you language, citation format, chapter structure, research positioning, and folder path all at once, skip straight to Stage 1.

## Workflow

### Stage 0: User Configuration (Required)

**BEFORE proceeding to Stage 2, collect the following from the user. Do not proceed to Stage 4 without all five.**

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

Run the Python script `extract_literature_metadata.py` over the user's literature folder to extract:
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

**Output:** A structured table (JSON) and a Markdown report (`_literature_report.md`) listing all references.

**Decision points:**
- If a PDF is flagged as scanned (image-based), warn the user that OCR may be needed for full-text extraction, but metadata (title/author) may still be readable.
- If CAJ files are detected, instruct the user to convert them to PDF using CAJViewer or `caj2pdf` before re-running the script.

**[USER_CHECKPOINT]: After presenting Stage 1 results, WAIT for user acknowledgment before proceeding to Stage 2.** Do not auto-advance. Ask: "以上是文献扫描结果。如果没有问题，我将继续进行主题聚类和优先级划分。你可以随时叫停或调整。"

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

**Context overflow guard — [CONTEXT_OVERFLOW] in Stage 2:**
If the total number of references exceeds 40, or if the combined title + preview text exceeds your context window capacity:
1. Ask the user to filter by format (e.g., "只看 PDF" or "排除 EPUB") before clustering.
2. If still too large, cluster in **batches** — process the first 30-35 references first, then the remainder in a second pass. Merge clusters thematically between batches.
3. If a single monograph's preview text alone is very long (>5,000 chars), truncate it before clustering.

**[USER_CHECKPOINT]: Present the complete literature map to the user and WAIT for confirmation.**

Show the user:
1. The full cluster list with each reference assigned to a cluster
2. The relevance score and priority tier for each reference
3. The proposed reading strategy (how many P0/P1/P2, estimated reading depth)

**Ask the user:** "以上是文献地图。请确认：
- 这些主题分类是否合理？
- 有没有核心文献被分到了 P1/P2？
- 有没有不相关的文献被分到了 P0/P1？
你可以直接告诉我调整意见，比如'把 [文件名] 移到 P0'。"

**Do NOT proceed to Stage 3 until the user confirms or explicitly says "继续".**

### Stage 3: Targeted Reading by Tier

**[USER_CHECKPOINT]: Before starting Stage 3, present the reading plan to the user for confirmation.**

Show the user:
- Which P0 references you will read in full (list titles)
- Which P1 references you will read abstract + conclusion + keyword-matched sections (list titles)
- Which P2 references you will read abstract only (list titles)
- Any scanned monographs and your strategy for handling them

**Ask:** "我计划按以下策略阅读，确认后开始：
- P0 精读 X 篇（列标题）
- P1 摘要+结论+关键词匹配 Y 篇
- P2 仅摘要 Z 篇
如果某篇你想调整阅读深度，直接告诉我。"

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

**Context overflow guard — [CONTEXT_OVERFLOW] in Stage 3:**
If the combined full-text word count of all P0 + P1 references exceeds 100,000 words (~300k chars):
1. Keep P0 references at full-text reading.
2. Downgrade **all P1 references** to "abstract + conclusion only" (no keyword-matched sections).
3. If still overflowing, keep only the **top 5 P0 references** by relevance and downgrade the rest to P1.
4. Alert the user: "文献总量过大，已自动降级部分文献的阅读深度以节省上下文空间。"

**For scanned monographs (300+ pages):**
- Do NOT attempt OCR of the entire book.
- Extract table of contents if available; identify 2-3 core chapters.
- Read only those chapters or search for keywords to locate relevant passages.

**[USER_CHECKPOINT]: After completing Stage 3, present a brief reading summary.**

Summarize for the user:
- Key arguments extracted from P0 references
- How P1 references support the user's research gap
- Any surprises or inconsistencies found during reading

**Ask:** "以上是阅读摘要。是否满意？可以直接进入写作阶段，或让我重新阅读某篇文献。"

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

**[USER_CHECKPOINT]: After Stage 4 output, ask for revision feedback.**

Present the draft and ask:
"以上是初稿。请确认：
1. 章节结构是否符合你的要求？
2. 引用格式是否正确？
3. 是否有文献引用遗漏或错配？
4. 研究空白的论述是否准确？
告诉我具体修改意见，我会逐条调整。"

## Complete Example Dialogue

This shows a realistic multi-turn interaction that demonstrates the workflow and all `[USER_CHECKPOINT]` pauses.

**Turn 1 — User:** "帮我写文献综述，文献在 D:\论文\references"

**Claude:**
> 好的，我先扫描一下你的文献文件夹。
>
> ...（运行 extract_literature_metadata.py）...
>
> ✅ 找到 34 篇文献
> | 格式 | 数量 |
> |------|------|
> | PDF | 28 篇 |
> | DOCX | 4 篇 |
> | TXT | 2 篇 |
>
> ⚠️ 3 篇 PDF 为扫描件（可能需要 OCR）
>
> 在开始之前，我还需要确认几个信息：
> 1. 输出语言：中文还是英文？
> 2. 引用格式：APA、GB/T 7714、还是 `[1]` 编号？
> 3. 你的研究题目或关键词是什么？（用于判断文献相关性）
> 4. 你学校的章节结构模板？（没有的话我提供默认模板）

**Turn 2 — User:** "中文，GB/T 7714，研究题目是'短视频平台算法推荐对新闻消费行为的影响'，用默认模板"

**Claude:**
> 收到，配置已记录：
> - 语言：中文
> - 引用格式：GB/T 7714
> - 研究定位：短视频平台算法推荐对新闻消费行为的影响
> - 章节结构：默认中文论文模板
>
> 现在开始 **Stage 2：主题聚类** ...（聚类结果）...
>
> **[USER_CHECKPOINT]** 以上是文献地图，请确认：
> - 主题分类是否合理？
> - 有没有核心文献被分到 P1/P2？
> - 有没有不相关的文献被分到 P0/P1？
> 你可以直接说调整意见，比如"把 [文件名] 移到 P0"。

**Turn 3 — User:** "没问题，继续"

**Claude:**
> **[USER_CHECKPOINT]** 阅读计划如下，确认后开始：
> - P0 精读 6 篇：...
> - P1 摘要+结论 18 篇：...
> - P2 仅摘要 10 篇：...
> 如果某篇你想调整阅读深度，直接告诉我。

**Turn 4 — User:** "开始读吧"

**Claude:** ...（执行 Stage 3 阅读）...

> **[USER_CHECKPOINT]** 阅读完成。关键发现：...
> 是否满意？可直接进入写作，或让我重新阅读某篇。

**Turn 5 — User:** "写吧"

**Claude:** ...（输出 Stage 4 初稿）...

> **[USER_CHECKPOINT]** 以上是初稿。请确认：
> 1. 章节结构是否符合你的要求？
> 2. 引用格式是否正确？
> 3. 是否有文献引用遗漏或错配？
> 4. 研究空白的论述是否准确？
> 告诉我具体修改意见，我会逐条调整。

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
| User only gave a folder path | Use **Mode A Guided Start** — run Stage 1 first, then collect configs |

## Common Mistakes

1. **Reading everything.** Agents often default to opening every file. This burns context and produces shallow understanding. Always extract metadata first.
2. **No clustering.** Without thematic clusters, the literature review becomes a list of summaries rather than an argument. Clusters create the review's narrative arc.
3. **Clustering without user positioning.** Clustering based only on literature titles produces generic groupings. Without the user's research positioning (title/abstract/keywords), relevance scoring is pure guesswork and P0/P1/P2 tiers may be completely wrong.
4. **Guessing the thesis structure.** If the user hasn't provided the exact heading hierarchy (e.g., 2.2.1 vs 2.2.2), ask in Stage 0 before writing. A mismatched structure requires full rewrite.
5. **Ignoring weak references.** Weak or tangential references should be explicitly flagged and potentially excluded. Citing irrelevant papers damages credibility.
6. **Skipping the gap analysis.** A literature review without a clear "what's missing → here's my study" transition fails its purpose. Stage 4 must end with the user's research positioning.
7. **Skipping Stage 0 configuration.** Writing without confirming language, citation format, chapter structure, research positioning, and literature folder path guarantees a mismatch with user expectations. Stage 0 is a hard prerequisite.
8. **Auto-advancing without user confirmation.** Each `[USER_CHECKPOINT]` exists for a reason. The user must see and approve the cluster map and reading plan before you spend context on reading. Do not silently proceed.

## Reusable Tool

**`extract_literature_metadata.py`** — Batch-extracts titles, authors, page counts, word counts, text volume, and scanned-page detection from a folder of literature files (PDF, DOCX, TXT, MD, EPUB). Outputs both JSON and a human-readable Markdown report.

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
