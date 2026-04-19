# efficient-literature-survey

**中文** | [English](README_EN.md)

---

## 高效文献综述工作流

一个 Claude Code skill，用于高效处理大量**多格式文献**（PDF、DOCX、TXT、MD、EPUB）并撰写**绪论**和**文献综述**，实现 **99%+ 的 Token 节省**。

### 它能做什么

将 10-100 篇文献转换为一个结构化的文献地图，然后输出完整的论文绪论和文献综述——**不需要逐字阅读每篇文献**。

支持**自定义章节结构**或选择**默认模板**（中文/英文论文框架），自动适配用户指定的引用格式与输出语言。

<table>
  <tr>
    <th width="12%">阶段</th>
    <th>动作</th>
    <th width="28%">输出</th>
  </tr>
  <tr>
    <td><b>0. 配置</b></td>
    <td>确认语言、引用格式、章节结构、<b>研究定位</b>（题目/摘要/关键词均可）、<b>文献文件夹路径</b>、输出类型（学位论文/综述论文）</td>
    <td>配置清单 + 研究方向记录</td>
  </tr>
  <tr>
    <td>1. 提取</td>
    <td>脚本遍历文献文件夹提取元数据（支持子文件夹递归）</td>
    <td>JSON 报告 + Markdown 汇总（标题/作者/页数/字数/期刊/卷期页/DOI/扫描检测）</td>
  </tr>
  <tr>
    <td>2. 聚类</td>
    <td>按主题聚成 5-8 个簇，<b>对照用户研究定位评分相关度</b>（Direct/Adjacent/Peripheral/Tangential），标定精读优先级</td>
    <td>文献地图（P0/P1/P2 三级阅读策略）—— <b>用户确认后继续</b></td>
  </tr>
  <tr>
    <td>3. 精读</td>
    <td>按优先级差异化阅读（全文/摘要+结论/仅摘要）—— <b>阅读计划用户确认后执行</b></td>
    <td>提取的论点与可引用原文</td>
  </tr>
  <tr>
    <td>4. 撰写</td>
    <td>按用户给定的章节框架输出，引用格式符合学术规范</td>
    <td>格式化的绪论 + 文献综述草稿</td>
  </tr>
</table>

---

## 5 分钟快速上手

### 场景：你有一个文件夹的文献，想快速写综述

**Step 1：安装**

```bash
mkdir -p ~/.claude/skills/
cp -r efficient-literature-survey ~/.claude/skills/
pip install -r requirements.txt
```

**Step 2：打开 Claude Code，说一句**

> "帮我写文献综述，文献在 `/Users/alice/Documents/references`"

**Step 3：Claude 会经历以下流程**

| 轮次 | Claude 做什么 | 你需要做什么 |
|------|-------------|-------------|
| 1 | 扫描文献文件夹（含子文件夹），告诉你找到多少篇、什么格式、有没有扫描件 | 看结果，确认文献数量 |
| 2 | 问你：语言、引用格式、研究题目、章节结构模板 | 回答这 4 个问题 |
| 3 | 做主题聚类，给你看分类和优先级（P0/P1/P2） | 确认分类，或说"把某篇移到 P0" |
| 4 | 给你阅读计划：精读哪几篇、略读哪几篇 | 确认或调整阅读深度 |
| 5 | 按优先级阅读文献，提取论点 | 等 Claude 读完 |
| 6 | 输出绪论 + 文献综述初稿 | 审阅，提出修改意见 |

**整个过程中你可以在任意轮次叫停、调整、修改。**

---

### 支持格式矩阵

| 格式 | 元数据提取 | pages | word_count | 期刊/卷期页/DOI | 扫描检测 | 依赖 |
|------|-----------|-------|-----------|----------------|---------|------|
| **PDF** | 标题、作者、页数、字数、期刊、卷期页、DOI、加密检测 | ✅ 真实页数 | ✅ 中英文混合智能统计 | ✅ 首页正则探测 | ✅ 多页采样 | PyPDF2 + PyCryptodome + pdfplumber |
| **DOCX** | 标题、作者、字数、期刊、卷期页 | ✅ 估算（字数÷500） | ✅ 中英文混合智能统计 | ✅ 前5000字符探测 | ❌ 否 | python-docx |
| **TXT / MD** | 字数、期刊、卷期页 | ✅ 估算 | ✅ 中英文混合智能统计 | ✅ 前3000字符探测 | ❌ 否 | 内置 |
| **EPUB** | 标题、作者、字数、期刊、卷期页 | ✅ 估算 | ✅ 中英文混合智能统计 | ✅ 前3000字符探测 | ❌ 否 | ebooklib + beautifulsoup4 |
| **CAJ** | 仅文件名 | ❌ | ❌ | ❌ | N/A | 提示用户转为 PDF（CAJViewer / caj2pdf） |

### 性能与增量特性

| 特性 | 说明 | 效果 |
|------|------|------|
| **环境预检** | `--env-check` 检测依赖完整性、终端编码、加密 PDF、扫描件 | 避免运行时批量失败 |
| **并发提取** | `ThreadPoolExecutor(max_workers=4)` 多线程并行读取 | 30 篇文献提速约 2-3 倍 |
| **增量缓存** | 基于文件 SHA-256 哈希，未变更文件跳过重新提取 | 二次运行秒级完成 |
| **智能分页策略** | 短篇（≤50页）读全文，专著（>50页）采样前15+后5页 | 避免专著封面/目录误导扫描检测和字数统计 |
| **多页采样扫描检测** | 采样 PDF 开头、中间、结尾页判断是否为扫描件 | 大幅降低封面图导致的误报 |
| **重复文献检测** | 基于标题相似度（SequenceMatcher ≥80%）自动标记重复 | 避免同一文献多格式重复引用 |
| **规范引用生成** | 支持 GB/T 7714、APA、MLA、编号四种格式，含期刊/卷期页/DOI | 引用可直接用于论文参考文献列表 |
| **不完整引用标记** | 当期刊/出版社/年份缺失时，自动标注 `〔文献信息不完整，请手动补全〕` | 避免引用格式"形似神不似" |
| **BibTeX 导出** | `--bibtex` 一键生成 `.bib` 文件，支持 `@article`/`@book`/`@misc` | LaTeX 用户刚需 |
| **BibTeX LaTeX 转义** | 自动转义 `& % $ # _ { } ~ ^ \` 等特殊字符，避免 `.bib` 编译报错 | LaTeX 用户刚需 |
| **子文件夹递归** | 默认递归遍历所有子文件夹，保留相对路径结构 | 适合按主题/年份组织文献的用户 |
| **结构化异常记录** | 提取失败时记录错误类型到报告备注栏 | 不再静默失败 |
| **扫描件 OCR 指引** | 检测到扫描 PDF 时，报告内附 marker/nougat/tesseract 安装命令 | 用户知道下一步该做什么 |
| **元数据 fallback** | PDF `/Title`、`/Author` 为空时，自动从首行文本启发式提取标题/作者/年份 | 大幅降低"文献信息不完整"误报 |
| **专著目录提取** | 对 >100 页 PDF 自动扫描目录结构，按 `--keywords` 匹配相关章节 | McCombs 204页 → 仅精读第 3 章（p.23-45） |
| **加密 PDF 分级** | 区分轻度加密（pdfplumber 可读）和完全加密（需手动解密） | 知网轻度加密 PDF 不再阻断流程 |
| **中文布局感知元数据** | pdfplumber 字体分析 + CNKI 水印过滤，提升中文论文标题/作者提取准确率 | 大幅降低"文献信息不完整"误报 |
| **Windows GBK 编码降级** | 检测到 UTF-8 已强制时，GBK 警告降为 INFO 级别 | 减少不必要的用户焦虑 |
| **工作流 checkpoint** | Stage 1 完成后写入 `_els_stage.json`，Claude 可在多轮对话中断后恢复状态 | 支持长时间任务断点续作 |

### 真实数据闭环

在 **30 篇中英混合文献**（含 3 本 200+ 页专著）上实测：

- **输入总量**：约 500 万+ 字符全文内容
- **处理成本**：约 3 万字符定向阅读（节省 **99.4%**）
- **产出结果**：1796 字绪论 + 3767 字文献综述，含 35 处精准引用

**核心底层逻辑**：学术写作不需要全文理解，只需要战略性提取论点、空白与研究定位。

### 安装

```bash
mkdir -p ~/.claude/skills/
cp -r efficient-literature-survey ~/.claude/skills/
```

依赖：

```bash
pip install -r requirements.txt
```

> **Windows 用户注意**：如果终端默认编码为 GBK，运行前请先执行 `chcp 65001` 或 `set PYTHONIOENCODING=utf-8`，避免中文输出乱码。

### 使用方式

**方式一：独立脚本**

```bash
python extract_literature_metadata.py /path/to/your/literature/folder
```

支持命令行参数：
- `--env-check` / `-e`：运行环境预检（依赖/编码/加密PDF/扫描件），不执行提取
- `--max-pages N` / `-m N`：强制只读前 N 页（覆盖智能分页策略）
- `--citation-style gb7714|apa|mla|numbered` / `-c STYLE`：选择引用格式（默认 gb7714）
- `--output-dir PATH` / `-o PATH`：指定输出目录（默认在文献文件夹内创建 `.els_output/` 子目录）
- `--keywords "kw1,kw2"` / `-k "kw1,kw2"`：专著章节匹配关键词（用于 >100 页 PDF 的目录匹配）
- `--bibtex` / `-b`：额外输出 BibTeX 文件 `_literature_references.bib`
- `--verbose` / `-v`：DEBUG 级别日志输出
- `--quiet` / `-q`：只输出 WARNING 及以上级别日志
- `--no-recursive`：禁用子文件夹递归遍历

支持交互式使用：
- 不带参数 → 提示输入路径
- 路径不存在 → 提示重新输入
- 无支持文件 → 列出检测到哪些、为什么不支持

输出：
- `_literature_extraction.json` — 结构化数据（含 `duplicates`、`citation_style`、`results[].citation`、`results[].toc`、`results[].matched_chapters`、`results[].encryption_level`）
- `_literature_report.md` — 人可读汇总报告（含重复检测、加密分级、专著章节匹配、OCR 指引、按子文件夹分组、参考文献列表附录）
- `_literature_references.bib` — BibTeX 文件（当使用 `--bibtex` 时）

... 支持 PDF / DOCX / TXT / MD / EPUB 多格式混合文件夹，含子文件夹递归

**方式二：Claude Code Skill 自动触发**

说出以下关键词即可激活：
- "帮我读文献写绪论和综述"
- "快速理解大量文献"
- "节省 token 读论文"
- "我有 30 篇文献需要写文献综述"
- ... 更多触发词见 [SKILL.md](SKILL.md) 的 Triggers 部分

### 兼容性说明

| 组件 | 运行环境 | 说明 |
|------|----------|------|
| `extract_literature_metadata.py` | **任何 Python 环境** | 独立脚本，可在终端、Jupyter、VS Code 等任意环境运行 |
| `SKILL.md` | **仅限 Claude Code** | 需要 Claude Code 的 skill 系统才能被 AI 自动读取和触发 |

如果你不使用 Claude Code，可以**单独使用 Python 脚本**完成阶段一（批量提取），阶段二到阶段四需手动完成。

### 目录结构

```
efficient-literature-survey/
├── SKILL.md                              # Claude 读取的核心 skill 文档（仅 Claude Code 有效）
├── extract_literature_metadata.py        # CLI 入口（向后兼容，任何 Python 环境可用）
├── test_extract_literature_metadata.py   # 单元测试（120 个用例）
├── CHANGELOG.md                          # 版本变更日志
├── README.md                             # 中文版本（本文件）
├── README_EN.md                          # English version
├── requirements.txt                      # 运行时依赖
├── pyproject.toml                        # Python 包元数据与构建配置
├── core/
│   ├── config.py                         # 所有可调常量集中配置（采样阈值、扫描检测参数等）
│   ├── constants.py                      # SUPPORTED_EXTS, CAJ_EXT, 复姓表
│   ├── helpers.py                        # 核心工具函数（字数统计、扫描检测、重复检测、元数据 fallback 等）
│   └── logging_config.py                 # 日志配置
├── extractors/
│   ├── base.py                           # 结果模板工厂
│   ├── pdf.py                            # PDF 提取器
│   ├── docx.py                           # DOCX 提取器
│   ├── txt.py                            # TXT/MD 提取器
│   └── epub.py                           # EPUB 提取器
├── citation/
│   ├── engine.py                         # 引用格式引擎（APA/MLA/GB）
│   └── bibtex.py                         # BibTeX 生成器
├── cache/
│   └── manager.py                        # 缓存管理（version 2）
├── checkpoint/
│   └── manager.py                        # 工作流 checkpoint 持久化（多轮对话断点续作）
└── report/
    └── generator.py                      # Markdown 报告生成
```

### 开发者

#### 模块架构

本项目采用**模块化拆分**设计，将原先 1282 行的单体脚本拆分为职责清晰的子模块：

- **`core/`** — 常量、工具函数、日志配置
- **`extractors/`** — 各格式提取器（PDF/DOCX/TXT/EPUB），可选依赖采用模块级懒加载
- **`citation/`** — 引用格式引擎 + BibTeX 生成器
- **`cache/`** — 基于 SHA-256 + 相对路径的增量缓存（version 2）
- **`report/`** — Markdown 报告生成器

#### 向后兼容

`extract_literature_metadata.py` 保留为 CLI 入口，所有命令行参数、输出文件格式、JSON/Markdown 结构均与 v1.2.0 之前保持一致。缓存从 `version: 1` 自动升级到 `version: 2`，旧缓存会被忽略并自动重新提取，无破坏性变更。

#### 运行测试

```bash
python -m unittest test_extract_literature_metadata.py -v
```

当前测试覆盖：
- PDF/DOCX/EPUB 提取器的 mock 测试（不依赖可选库）
- 缓存管理器 roundtrip 测试
- 提取器 dispatcher 路由测试
- 引用格式、BibTeX 生成、重复检测等集成测试
- CNKI 水印过滤、目录提取、章节关键词匹配
- 加密分级处理（轻度/完全）
- 基于字体大小的增强元数据 fallback

---

### 为什么能省 Token

| 方式 | 阅读量 | 阅读深度 | 产出质量 |
|------|--------|----------|---------|
| 全文通读 | 500 万+ 字符 | 浅（上下文溢出） | 低 |
| **本工作流** | **~3 万字符** | **深（定向摘录）** | **高** |

---

### License

MIT
