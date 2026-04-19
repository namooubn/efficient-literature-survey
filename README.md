# efficient-literature-survey

**中文** | [English](README_EN.md)

---

## 高效文献综述工作流

一个 Claude Code skill，用于高效处理大量**多格式文献**（PDF、DOCX、TXT、MD、EPUB）并撰写**绪论**和**文献综述**，实现 **99%+ 的 Token 节省**。

### 它能做什么

将 10-100 篇文献转换为一个结构化的文献地图，然后输出完整的论文绪论和文献综述——**不需要逐字阅读每篇文献**。

支持**自定义章节结构**或选择**默认模板**（中文/英文论文框架），自动适配用户指定的引用格式与输出语言。

| 阶段 | 动作 | 输出 |
|------|------|------|
| **一、用户配置** | 确认语言、引用格式、章节结构、**研究定位**（题目/摘要/关键词均可） | 配置清单 + 用户研究方向记录 |
| 二、 批量提取 | 脚本遍历文献文件夹提取元数据 | JSON 报告（标题、作者、页数、字数、文本量、扫描版检测） |
| 三、聚类分级 | 按主题聚成 5-8 个簇，**对照用户研究定位评分相关度**（Direct/Adjacent/Peripheral/Tangential），标定精读优先级 | 文献地图（P0/P1/P2 三级阅读策略） |
| 四、分层精读 | 按优先级差异化阅读（全文/摘要+结论/仅摘要） | 提取的论点与可引用原文 |
| 五、结构化撰写 | 按用户给定的章节框架输出 | 格式化的绪论 + 文献综述草稿 |

### 支持格式矩阵

| 格式 | 元数据提取 | pages | word_count | 扫描检测 | 依赖 |
|------|-----------|-------|-----------|---------|------|
| **PDF** | 标题、作者、页数、字数、文本量 | ✅ 真实页数 | ✅ | ✅ 是 | PyPDF2 + pdfplumber |
| **DOCX** | 标题、作者、字数、文本量 | ✅ 估算（字数÷500） | ✅ | ❌ 否 | python-docx |
| **TXT / MD** | 字数、文本量 | ✅ 估算 | ✅ | ❌ 否 | 内置 |
| **EPUB** | 标题、作者、字数、文本量 | ✅ 估算 | ✅ | ❌ 否 | ebooklib + beautifulsoup4 |
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

... 更多命令用法见脚本内 `--help`

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
