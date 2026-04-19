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

## Stage 0: User Configuration (REQUIRED — hold here until all 5 collected)

| # | Config | Ask |
|---|--------|-----|
| 1 | Output language | "What language?" |
| 2 | Citation format | "APA / MLA / GB/T 7714 / numbered `[1]` ?" |
| 3 | Chapter structure | "Custom headings or default template (Chinese/English thesis)?" |
| 4 | Research positioning | "Thesis title, abstract, research question, OR 3-5 keywords — any is fine." |
| 5 | Literature folder path | "Where are your files?" |

**Rule**: Do NOT proceed to Stage 4 until all 5 are collected. If custom structure chosen but not yet provided, hold at Stage 0.

## Stage 1: Batch Extract Metadata

Run `extract_literature_metadata.py <folder_path>` to extract:
- Title, author, year, page count, word count
- Journal/volume/issue/page-range/DOI (heuristic detection)
- Scanned-image flag, first-page preview text
- Duplicate detection

**Output**: `_literature_extraction.json` + `_literature_report.md` + optional `_literature_references.bib`.

**Decision points**:
- Scanned PDF → warn user; suggest `marker` / `nougat` / `tesseract` OCR.
- CAJ detected → instruct conversion to PDF.
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
7. **Temporal evolution (NEW)**: Within each cluster, organize references chronologically or by theoretical lineage. Show: early work → turning points → recent advances.
8. **Critical analysis (NEW)**: In each cluster, identify at least ONE conflict, methodological limitation, or contradictory finding among cited refs. Explain how user's study addresses or avoids it.
9. **Survey vs. original distinction**: High-citation survey papers in a cluster must be flagged as `〔综述〕` and used as theoretical anchors; original experimental papers support specific claims.

### Few-Shot: Writing a Cluster Paragraph

**User positioning**: "Research on chain-of-thought prompting in large language models"

**Good example** (follows rules 7+8):
> Early efforts to elicit reasoning from LLMs relied on few-shot exemplars without explicit intermediate steps (Brown et al., 2020). The breakthrough came with chain-of-thought (CoT) prompting, which demonstrated that inserting reasoning chains into prompts significantly improves arithmetic and commonsense reasoning (Wei et al., 2022). However, subsequent work revealed a critical tension: while CoT improves performance on complex tasks, it can amplify biases present in the training data (Turpin et al., 2023), and its effectiveness diminishes sharply in low-resource languages (Shi et al., 2022). These conflicting findings highlight the need for bias-aware CoT mechanisms — the gap this study addresses by proposing [your method].

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
| Monograph >200 pages | Extract TOC; read 2-3 relevant chapters only |
| No chapter structure | Hold at Stage 0; do not guess |
| No research positioning | Hold at Stage 0; do not cluster blindly |
| Weak reference | Exclude; note as "tangential" in map |
| User wants "save tokens" | Emphasize P0/P1/P2 tier system |
| CAJ files | Instruct conversion to PDF |
| Adding new refs mid-workflow | Use **Append Mode** |

## Common Mistakes

- **Reading everything** — Extract metadata first. Opening every file burns context.
- **No clustering** — Without thematic clusters, review becomes a list of summaries, not an argument.
- **Clustering without positioning** — Relevance scoring is guesswork without user's research keywords.
- **Guessing structure** — Ask for exact headings in Stage 0. Mismatched structure = full rewrite.
- **Ignoring weak refs** — Tangential refs must be flagged and potentially excluded.
- **Skipping gap analysis** — Stage 4 MUST end with gap + positioning.
- **Skipping Stage 0** — Writing without all 5 configs guarantees mismatch.
- **Auto-advancing** — Each `[USER_CHECKPOINT]` exists for a reason. Do NOT silently proceed.
- **Flat chronological listing** — Violates Rule 7. Must show evolution, not just sequence.
- **No critical tension** — Violates Rule 8. A review without critique is a bibliography, not scholarship.

## Reusable Tool

**`extract_literature_metadata.py`** — Batch-extracts titles, authors, page/word counts, text volume, scanned-page detection, bibliographic metadata (journal/vol/issue/DOI), duplicate detection, and formatted citations. Outputs JSON + Markdown + optional BibTeX.

**Dependencies**: `PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4`

## Real-World Impact

30 mixed Chinese/English refs (3 monographs 200+ pages):
- Full-text: ~5M+ chars
- Targeted reading: ~30k chars (**99.4% savings**)
- Output: 1,796-char introduction + 3,767-char review with 35 citations, 8 clusters
