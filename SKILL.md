---
name: efficient-literature-survey
description: Use when the user needs to batch-read academic literature (10+ files) and write a thesis introduction or literature review. Triggers on phrases like "帮我读文献", "literature review", "batch read papers", or when the user has a folder of literature files needing structured academic output.
---

# Efficient Literature Survey Workflow

## Core Assumptions

- **文献类型**：用户提供的文件是学术论文、专著或学位论文。**非学术内容**（新闻报道、法律文件、产品手册）需标记为 `non-academic` 并降级至 P2 仅摘要处理。
- **语言**：支持中英混合文献。输出语言以 Stage 0 用户配置为准。
- **格式**：PDF, DOCX, TXT, MD, EPUB。CAJ 需先转 PDF。
- **Token 策略**：从全文通读（5M+ 字符）压缩至定向阅读（~30k 字符），节省 **99%+**。

## Triggers

- "帮我读文献", "写绪论和综述", "快速理解大量文献", "节省token读论文"
- "literature review", "thesis introduction", "batch read papers"
- User has a folder of literature files and needs structured academic output

**When NOT to use:** < 5 papers, single-paper summary only, or purely non-academic files.

## Starting Mode

- **Mode A (default)**: Run Stage 1 script immediately → show results table → collect remaining Stage 0 configs.
- **Mode B**: If user proactively gives all 5 configs, skip straight to Stage 1.
- **Mode C (Fast Mode)**: Triggered ONLY when (a) all 5 configs are provided, AND (b) user explicitly says "直接走 / 全速推进 / 不用确认". In this mode:
  - Stage 1 results are shown; if user does not object, auto-advance to Stage 2.
  - Stage 2 cluster map is shown; auto-advance to Stage 3 (merged checkpoint).
  - Stage 3 reading summary is shown; MUST pause for user confirmation before Stage 3.5.
  - Stage 3.5 outline is shown; MUST pause for user confirmation before Stage 4.
  - Stage 0 and Stage 2 checkpoints remain; Stage 2→3 checkpoints are merged into one "map + plan" summary.
- **Mode D (Semi-Fast Mode)**: Triggered when (a) all 5 configs are provided, AND (b) user does NOT explicitly say "逐阶段确认". In this mode:
  - Stage 1 results are shown; auto-advance to Stage 2.
  - Stage 2 cluster map + reading plan are merged into ONE output; MUST pause for user confirmation before Stage 3.
  - Stage 3 reading summary is shown; MUST pause for user confirmation before Stage 3.5.
  - Stage 3.5 outline is shown; MUST pause for user confirmation before Stage 4.
  - **Critical rule**: Even in Mode D, the agent MUST NOT proceed from Stage 2→3 or Stage 3.5→4 without explicit user confirmation. These are non-negotiable checkpoints.

## Stage 0: User Configuration (REQUIRED — hold here until all 5 collected)

| # | Config | Ask |
|---|--------|-----|
| 1 | Output language | "What language?" |
| 2 | Citation format | "APA / MLA / GB/T 7714 / numbered `[1]` ?" |
| 3 | Chapter structure | "Custom headings or default template (Chinese/English thesis)?" |
| 4 | Research positioning | "Thesis title, abstract, research question, OR 3-5 keywords — any is fine." |
| 5 | Literature folder path | "Where are your files?" |
| 6 | Output type | "thesis (学位论文) / review article (综述论文) / other?" (default: thesis) |

**Rule**: Do NOT proceed to Stage 4 until all 5 are collected. If custom structure chosen but not yet provided, hold at Stage 0.

## Stage 1: Batch Extract Metadata

### Step 0: Environment Pre-Check (REQUIRED)

Before running extraction, verify the environment to avoid runtime failures:

```bash
python extract_literature_metadata.py <folder_path> --env-check
```

This checks:
- Dependencies installed (`PyPDF2`, `pdfplumber`, `python-docx`, etc.)
- Terminal encoding (Windows GBK → UTF-8 warning)
- Encrypted PDFs, scanned-image PDFs, CAJ files

**If missing deps**: `pip install PyPDF2 PyCryptodome pdfplumber python-docx ebooklib beautifulsoup4`
**If Windows GBK**: run `chcp 65001` or `set PYTHONIOENCODING=utf-8`
**If encrypted PDFs detected**: distinguish light vs full encryption (see Decision points below).

### Step 1: Run Extraction

Run `extract_literature_metadata.py <folder_path> [--keywords "kw1,kw2"]` to extract:
- Title, author, year, page count, word count
- Journal/volume/issue/page-range/DOI (heuristic detection)
- Scanned-image flag, encrypted flag (with tier: light/full), first-page preview text
- **Monograph TOC + keyword-matched chapters** (for PDFs >100 pages)
- Duplicate detection

**Output**: `_literature_extraction.json` + `_literature_report.md` + optional `_literature_references.bib`.

**Incremental re-use**: If `_literature_extraction.json` already exists in the output folder and files are unchanged (SHA-256 cache), skip re-extraction and proceed to Stage 2. Do NOT force re-running Stage 1 unless user explicitly requests it.

**Decision points**:
- Scanned/image PDF → warn user; suggest `marker` / `nougat` / `tesseract` OCR.
- Encrypted PDF → tiered handling:
  - **Light encryption** (`encryption_level: light`): PyPDF2 flags encrypted but pdfplumber can read text normally. Script auto-decrypts with empty password. Proceed normally.
  - **Full encryption** (`encryption_level: full`): Both PyPDF2 and pdfplumber fail. Flag and ask user to decrypt manually.
- CAJ detected → instruct conversion to PDF.
- Monograph (>100 pages) with TOC match → report matched chapters with page ranges in Stage 1 output. These become P0 core reading targets.
- >40 refs → batch by subfolder or cluster.

**[USER_CHECKPOINT]**: Present Stage 1 results table. WAIT for user acknowledgment before Stage 2.

## Stage 2: Build Literature Map (Cluster + Prioritize)

**Inputs**: Stage 1 metadata (titles, previews) + Stage 0 research positioning.

### Step 1: Thematic Clustering (MANDATORY)

Group references into **5-8 thematic clusters**. Each cluster name MUST include 1-2 representative keywords in parentheses.

**Example — Clustering 5 papers on LLM research:**

| Title | Assigned Cluster |
|-------|-----------------|
| Attention Is All You Need | 1. Transformer架构与注意力机制 (Transformer, Attention) |
| BERT: Pre-training of Deep Bidirectional Transformers | 2. 预训练与表征学习 (Pre-training, Representation) |
| Language Models are Few-Shot Learners (GPT-3) | 3. 大模型推理与涌现能力 (LLM, Emergence) |
| Chain-of-Thought Prompting Elicits Reasoning | 3. 大模型推理与涌现能力 (LLM, Emergence) |
| Evaluating Large Language Models via Human Preference | 4. 模型评估与对齐 (Evaluation, Alignment) |

**Rule**: A paper belongs to exactly one primary cluster. If cross-cutting, note secondary cluster in `note`.

### Step 2: Relevance Scoring (MANDATORY)

Score each cluster using the user's Stage 0 research positioning keywords as explicit criteria.

| Score | Meaning | Action | Reading Depth |
|-------|---------|--------|--------------|
| **Direct** | Directly addresses user's research question | → P0 Core | Full text (≤50k chars) or abstract+conclusion+key chapters |
| **Adjacent** | Supports theory, method, or context | → P1 Support | Abstract + conclusion + keyword-matched sections |
| **Peripheral** | Same field, loosely tied | → P2 Background | Abstract only |
| **Tangential** | Minimal connection | → Exclude | Do not cite |

**Rule**: Every score MUST reference at least one keyword from the user's Stage 0 positioning. Example: "Cluster 3 scored Direct because it addresses 'chain-of-thought reasoning', which matches user's keyword 'reasoning enhancement'."

**[CONTEXT_OVERFLOW] guard**: >40 refs → filter by format or cluster in batches.

**[USER_CHECKPOINT]**: Present complete map (clusters, scores, reading strategy). WAIT for confirmation.

## Stage 3: Targeted Reading by Tier

**[USER_CHECKPOINT]**: Present reading plan (which P0/P1/P2, at what depth). WAIT for confirmation.

**Mode C exception**: If user already confirmed the Stage 2 cluster map with "直接走", merge this checkpoint into Stage 2's summary. Present the reading plan as part of the cluster map output, then auto-advance.

**Mode D exception**: The merged "cluster map + reading plan" output in Mode D MUST still wait for user confirmation before proceeding to actual reading execution. Do NOT silently execute Stage 3 reading just because the plan was shown.

### P0 (Core) — 5-8 refs
1. Read first 2,000 chars for structure.
2. If ≤50,000 chars → full text.
3. If >50,000 chars → abstract + conclusion + 2-3 key chapters.
4. Extract: core argument, 2-3 direct quotations, theoretical lineage, methodology.

### P1 (Support) — 15-20 refs
1. First 2,000 chars (abstract + intro).
2. Last 1,500 chars (conclusion).
3. If keywords appear in preview → read matched sections (±500 chars).
4. Extract: 2-3 sentences on contribution + connection to research gap.

### P2 (Background) — remaining refs
1. First 1,000 chars (abstract).
2. One-sentence positioning note.

**[CONTEXT_OVERFLOW] guard**: Combined P0+P1 >100k words → downgrade all P1 to abstract-only; keep top 5 P0 only.

**[USER_CHECKPOINT]**: After Stage 3, present brief reading summary. WAIT before Stage 4.

## Stage 3.5: Outline Confirmation (MANDATORY)

**Purpose**: Prevent high rework cost if user wants structural changes after 6,800+ words are written. The user said "我不着急 一步步来" — this stage honors that intent.

**Input**: Stage 3 reading summaries + Stage 0 chapter structure + monograph chapter mappings (if any).

**Output**: A bullet-point level outline with:
- Section headings (matching user's Stage 0 structure exactly)
- Core argument per section (1-2 sentences)
- Citation numbers planned for each section
- Estimated word count per section
- Monograph chapter-to-section mappings (e.g. "专著《X》第3章 → 本节理论框架")

**Format**:

```markdown
## 写作大纲（待确认）

### 1. 研究背景与问题提出（约 800 字）
- 论点：XXX 领域的发展引出 YYY 核心问题
- 引用：[1], [3], [5]

### 2. 文献综述 — 子主题 A（约 1200 字）
- 论点：早期研究侧重... 近期突破在于...
- 引用：[2], [4], [7]
- 专著映射：专著《X》第3章"理论框架" → 本节理论基础

...

### N. 研究缺口与本研究定位（约 600 字）
- 论点：现有研究存在三方面局限 → 本研究的切入点
- 引用：[6], [8]

**预估总字数**：6800 字
```

**Rules**:
1. Do NOT write full prose in this stage — only bullet points.
2. Every planned citation MUST map to a real reference from Stage 1 results.
3. If user provided custom chapter structure in Stage 0, use it exactly; do not invent new headings.
4. For monographs with `chapter_texts`, note which chapters feed which sections.

**Mode C/D exception**: Even in Fast / Semi-Fast modes, Stage 3.5 is **NON-SKIPPABLE**. Auto-advance is NOT permitted here. The merged checkpoint from Stage 2→3 MUST end at Stage 3.5, not Stage 4.

**[USER_CHECKPOINT]**: Present outline. WAIT for explicit confirmation or revision request.
- If user says "确认 / 可以 / 没问题 / 就这么写" → proceed to Stage 4.
- If user requests changes → revise outline and re-present. Do NOT proceed to Stage 4 until user confirms.

## Stage 4: Structured Writing

Write introduction and literature review per user's Stage 0 chapter structure. **Do NOT use any default template unless explicitly chosen.**

### Writing Rules (MANDATORY)

1. **Strict chapter structure**: Use user's exact heading hierarchy.
2. **Citation format**: Use user's required style (APA/MLA/GB/numbered).
3. **Source anchoring**:
   - P0 refs → deep theoretical anchoring and primary claims
   - P1 refs → empirical support and secondary claims
   - P2 refs → breadth or historical positioning only
4. **Every claim must be traceable** to a specific reference.
5. **Research gap**: Final section MUST explicitly name the gap and state how user's study fills it.
6. **Output language**: Strictly follow Stage 0 config.
7. **Temporal evolution**: Within each cluster, organize references chronologically or by theoretical lineage. Show: early work → turning points → recent advances.
8. **Critical analysis** (branch by output_type):
   - **review article**: In EACH cluster paragraph, inline at least ONE conflict, methodological limitation, or contradictory finding. Place critique within the cluster's narrative flow.
   - **thesis (default)**: Critique MAY be concentrated in a dedicated "文献评述 / Literature Critique" section (typically after all cluster subsections). Each cluster paragraph focuses on chronological evolution and thematic synthesis. The unified critique section identifies cross-cluster gaps, methodological limitations, and contradictory findings across the field. Brief inline critique per cluster is optional.
   - **Mixed**: Brief inline critique per cluster + a unified critique section for cross-cutting gaps.
9. **Survey vs. original distinction**: High-citation survey papers MUST be explicitly flagged with `〔综述〕` immediately after the first in-text citation. Example: "郭小宇等〔综述〕对 X 领域进行了系统梳理……". Original experimental papers carry no flag.

### Few-Shot: Writing a Cluster Paragraph

**User positioning**: "Research on chain-of-thought prompting in large language models"

**Good example** (follows rules 7+8):
> Early efforts to elicit reasoning from LLMs relied on few-shot exemplars without explicit intermediate steps (Brown et al., 2020). The breakthrough came with chain-of-thought (CoT) prompting, which demonstrated that inserting reasoning chains into prompts significantly improves arithmetic and commonsense reasoning (Wei et al., 2022). However, subsequent work revealed a critical tension: while CoT improves performance on complex tasks, it can amplify biases present in the training data (Turpin et al., 2023), and its effectiveness diminishes sharply in low-resource languages (Shi et al., 2022). These conflicting findings highlight the need for bias-aware CoT mechanisms — the gap this study addresses by proposing [your method].

**Good example — thesis style** (chronological synthesis, critique deferred to unified section):
> 早期研究通过少量示例激发 LLM 推理能力，但未显式构建中间步骤 (Brown et al., 2020)。Wei 等 (2022) 提出思维链 (CoT) 提示，在算术与常识推理任务上取得突破。此后，零样本 CoT (Kojima et al., 2022) 与自一致性解码 (Wang et al., 2023) 进一步扩展了该范式。郭小宇等〔综述〕系统梳理了 CoT 在复杂推理中的应用现状。上述研究共同推动了从"直接预测"到"逐步推理"的范式转变，为本研究提出的偏差感知 CoT 机制奠定了理论基础。
>
> （文献评述节统一批判：然而，现有 CoT 方法存在两方面局限：一是可能放大训练数据中的固有偏见 (Turpin et al., 2023)；二是在低资源语言中效果显著下降 (Shi et al., 2022)。这些矛盾发现表明，亟需构建兼顾公平性与跨语言泛化能力的 CoT 框架——这正是本研究的切入点。）

**Bad example** (violates rules 7+8 — flat listing, no conflict):
> Wei et al. (2022) proposed chain-of-thought prompting. Kojima et al. (2022) used zero-shot CoT. Wang et al. (2023) improved it with self-consistency. These methods all improve reasoning.

**[USER_CHECKPOINT]**: After Stage 4, present draft and ask for revision feedback (structure, citations, gap analysis).

## Append Mode: Adding New References

When user says "add more papers" or "I found 5 new refs":

1. **Incremental extraction**: Run Stage 1 script. SHA-256 cache ensures unchanged files are skipped.
2. **Re-cluster assessment**: New refs go through Stage 2. Existing clusters may be renamed or split if new refs reveal a missing theme.
3. **Minimal rewrite**: Update literature map with new refs marked `〔新增〕`. Revise Stage 4 draft ONLY in affected clusters. Do NOT rewrite unaffected sections.
4. **Citation renumbering**: If using numbered citations, renumber globally. Present a diff of citation changes.

## Tool Use

### Bash — Run extraction script
```bash
# Environment pre-check (run first)
python extract_literature_metadata.py <folder_path> --env-check

# Full extraction
python extract_literature_metadata.py <folder_path> [--max-pages N] [--citation-style STYLE] [--output-dir PATH] [--bibtex] [--no-recursive]
```

### Read — Targeted reading by tier
| Tier | Strategy |
|------|----------|
| P0 | Full text if ≤50k chars; else first 2k + key chapters |
| P1 | First 2k + last 1.5k + keyword-matched sections |
| P2 | First 1k (abstract) only |

### Write — Save outputs
- `_literature_map.md` — clusters, scores, reading plan
- `_thesis_introduction.md` / `_literature_review.md` — Stage 4 output

## Quick Reference

| Situation | Action |
|-----------|--------|
| 30+ files in folder | Run Stage 1 immediately (Mode A) |
| Scanned/image PDF | Flag; suggest OCR tools |
| Light encrypted PDF | Auto-decrypt; proceed normally |
| Full encrypted PDF | Flag `encryption_level: full`; user must decrypt |
| Monograph >100 pages | Extract TOC; match chapters by keywords; read matched chapters |
| No chapter structure | Hold at Stage 0; do not guess |
| No research positioning | Hold at Stage 0; do not cluster blindly |
| Weak reference | Exclude; note as "tangential" in map |
| User wants "save tokens" | Emphasize P0/P1/P2 tier system |
| User says "直接走/全速推进" | Enable **Mode C (Fast Mode)** |
| User gives all configs but does NOT say "逐阶段确认" | Enable **Mode D (Semi-Fast Mode)** |
| CAJ files | Instruct conversion to PDF |
| Adding new refs mid-workflow | Use **Append Mode** |
| `_literature_extraction.json` exists | Skip Stage 1; proceed to Stage 2 |

## Common Mistakes

- **Reading everything** — Extract metadata first. Opening every file burns context.
- **No clustering** — Without thematic clusters, review becomes a list of summaries, not an argument.
- **Clustering without positioning** — Relevance scoring is guesswork without user's research keywords.
- **Guessing structure** — Ask for exact headings in Stage 0. Mismatched structure = full rewrite.
- **Ignoring weak refs** — Tangential refs must be flagged and potentially excluded.
- **Skipping gap analysis** — Stage 4 MUST end with gap + positioning.
- **Skipping Stage 0** — Writing without all 5 configs guarantees mismatch.
- **Auto-advancing** — Each `[USER_CHECKPOINT]` exists for a reason. Do NOT silently proceed (except in Mode C with explicit user consent).
- **Flat chronological listing** — Violates Rule 7. Must show evolution, not just sequence.
- **No critical tension** — Violates Rule 8. A review without critique is a bibliography, not scholarship.
- **不分输出类型硬套批判规则** — thesis 和 review article 的批判分布不同，生搬硬套会破坏行文流畅度。
- **忽略环境差异** — Windows GBK 编码、加密 PDF、缺失依赖会导致 Stage 1 批量失败。必须先做环境预检。

## Reusable Tool

**`extract_literature_metadata.py`** — Batch-extracts titles, authors, page/word counts, text volume, scanned-page detection, bibliographic metadata (journal/vol/issue/DOI), duplicate detection, and formatted citations. Outputs JSON + Markdown + optional BibTeX.

**Dependencies**: `PyPDF2 PyCryptodome pdfplumber python-docx ebooklib beautifulsoup4`

## Real-World Impact

30 mixed Chinese/English refs (3 monographs 200+ pages):
- Full-text: ~5M+ chars
- Targeted reading: ~30k chars (**99.4% savings**)
- Output: 1,796-char introduction + 3,767-char review with 35 citations, 8 clusters
