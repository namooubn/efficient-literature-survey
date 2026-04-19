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
    <td>确认语言、引用格式、章节结构、<b>研究定位</b>（题目/摘要/关键词均可）、<b>文献文件夹路径</b></td>
    <td>配置清单 + 研究方向记录</td>
  </tr>
  <tr>
    <td>1. 提取</td>
    <td>脚本遍历文献文件夹提取元数据</td>
    <td>JSON 报告 + Markdown 汇总（标题/作者/页数/字数/文本量/扫描检测）</td>
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
    <td>按用户给定的章节框架输出</td>
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
pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
```

**Step 2：打开 Claude Code，说一句**

> "帮我写文献综述，文献在 `/Users/alice/Documents/references`"

**Step 3：Claude 会经历以下流程**

| 轮次 | Claude 做什么 | 你需要做什么 |
|------|-------------|-------------|
| 1 | 扫描文献文件夹，告诉你找到多少篇、什么格式、有没有扫描件 | 看结果，确认文献数量 |
| 2 | 问你：语言、引用格式、研究题目、章节结构模板 | 回答这 4 个问题 |
| 3 | 做主题聚类，给你看分类和优先级（P0/P1/P2） | 确认分类，或说"把某篇移到 P0" |
| 4 | 给你阅读计划：精读哪几篇、略读哪几篇 | 确认或调整阅读深度 |
| 5 | 按优先级阅读文献，提取论点 | 等 Claude 读完 |
| 6 | 输出绪论 + 文献综述初稿 | 审阅，提出修改意见 |

**整个过程中你可以在任意轮次叫停、调整、修改。**

---

### 支持格式矩阵

| 格式 | 元数据提取 | pages | word_count | 扫描检测 | 依赖 |
|------|-----------|-------|-----------|---------|------|
| **PDF** | 标题、作者、页数、字数、文本量 | ✅ 真实页数 | ✅ 中英文混合智能统计 | ✅ 是 | PyPDF2 + pdfplumber |
| **DOCX** | 标题、作者、字数、文本量 | ✅ 估算（字数÷500） | ✅ 中英文混合智能统计 | ❌ 否 | python-docx |
| **TXT / MD** | 字数、文本量 | ✅ 估算 | ✅ 中英文混合智能统计 | ❌ 否 | 内置 |
| **EPUB** | 标题、作者、字数、文本量 | ✅ 估算 | ✅ 中英文混合智能统计 | ❌ 否 | ebooklib + beautifulsoup4 |
| **CAJ** | 仅文件名 | ❌ | ❌ | N/A | 提示用户转为 PDF（CAJViewer / caj2pdf） |

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
pip install PyPDF2 pdfplumber python-docx ebooklib beautifulsoup4
```

### 使用方式

**方式一：独立脚本**

```bash
python extract_literature_metadata.py /path/to/your/literature/folder
```

支持交互式使用：
- 不带参数 → 提示输入路径
- 路径不存在 → 提示重新输入
- 无支持文件 → 列出检测到哪些、为什么不支持

输出：
- `_literature_extraction.json` — 结构化数据
- `_literature_report.md` — 人可读汇总报告

... 支持 PDF / DOCX / TXT / MD / EPUB 多格式混合文件夹

**方式二：Claude Code Skill 自动触发**

**直接触发（推荐）：** 在输入框输入 `/efficient-literature-survey` 回车即可。

**自然语言触发：** 说出以下关键词亦可激活：
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
├── SKILL.md                         # Claude 读取的核心 skill 文档（仅 Claude Code 有效）
├── extract_literature_metadata.py   # 独立批量提取脚本（任何 Python 环境可用）
├── extract_pdf_metadata.py          # 旧版 PDF-only 脚本（保留向后兼容）
├── README.md                        # 中文版本（本文件）
└── README_EN.md                     # English version
```

### 为什么能省 Token

| 方式 | 阅读量 | 阅读深度 | 产出质量 |
|------|--------|----------|----------|
| 全文通读 | 500 万+ 字符 | 浅（上下文溢出） | 低 |
| **本工作流** | **~3 万字符** | **深（定向摘录）** | **高** |

---

### License

MIT
