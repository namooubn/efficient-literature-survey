# efficient-literature-survey

<p align="right">
  <b>中文</b> | <a href="README_EN.md">English</a>
</p>

---

## 高效文献综述工作流

一个 Claude Code skill，用于高效处理大量 PDF 参考文献并撰写**绪论**和**文献综述**，实现 **99%+ 的 Token 节省**。

### 它能做什么

将 10–100 篇 PDF 转换为一个结构化的文献地图，然后输出完整的论文绪论和文献综述——**不需要逐字阅读每篇文献**。

| 阶段 | 动作 | 输出 |
|------|------|------|
| 一、批量提取 | 脚本遍历 PDF 文件夹提取元数据 | JSON 报告（标题、作者、页数、文本量、扫描版检测） |
| 二、聚类分级 | 按主题聚成 5–8 个簇，标定精读优先级 | 文献地图（P0/P1/P2 三级阅读策略） |
| 三、分层精读 | 按优先级差异化阅读（全文/摘要+结论/仅摘要） | 提取的论点与可引用原文 |
| 四、结构化撰写 | 按用户给定的章节框架输出 | 格式化的绪论 + 文献综述草稿 |

### 真实数据闭环

在 **30 篇中英混合 PDF**（含 3 本 200+ 页专著）上实测：

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
pip install PyPDF2 pdfplumber
```

### 使用方式

**方式一：独立脚本**

```bash
python extract_pdf_metadata.py /path/to/your/pdf/folder
```

**方式二：Claude Code Skill 自动触发**

说出以下关键词即可激活：
- "帮我读文献写绪论和综述"
- "快速理解大量 PDF"
- "节省 token 读论文"
- "我有 30 篇文献需要写文献综述"

### 兼容性说明

| 组件 | 运行环境 | 说明 |
|------|----------|------|
| `extract_pdf_metadata.py` | **任何 Python 环境** | 独立脚本，可在终端、Jupyter、VS Code 等任意环境运行 |
| `SKILL.md` | **仅限 Claude Code** | 需要 Claude Code 的 skill 系统才能被 AI 自动读取和触发 |

如果你不使用 Claude Code，可以**单独使用 Python 脚本**完成阶段一（批量提取），阶段二到阶段四需手动完成。

### 目录结构

```
efficient-literature-survey/
├── SKILL.md                  # Claude 读取的核心 skill 文档（仅 Claude Code 有效）
├── extract_pdf_metadata.py   # 独立批量提取脚本（任何 Python 环境可用）
├── README.md                 # 中文文档
└── README_EN.md              # 英文文档
```

### 为什么能省 Token

| 方式 | 阅读量 | 阅读深度 | 产出质量 |
|------|--------|----------|----------|
| 全文通读 | 500 万+ 字符 | 浅（上下文溢出） | 低 |
| **本工作流** | **~3 万字符** | **深（定向摘录）** | **高** |

---

### License

MIT
