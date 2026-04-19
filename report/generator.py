"""Markdown report generator for literature extraction results."""

from datetime import datetime
from pathlib import Path

OCR_GUIDANCE = """
> **处理建议**：以下工具可将其转换为可提取文本的 PDF
> - **marker**（推荐，GPU 快、排版保留好）：`pip install marker-pdf && marker_single <文件>`
> - **nougat**（学术 PDF 专用）：`pip install nougat-ocr && nougat <文件>`
> - **pdf2image + pytesseract**（CPU 可用）：`pip install pdf2image pytesseract`，然后逐页 OCR
> - 转换完成后，重新运行本脚本以获取完整元数据。
"""


def generate_markdown_report(
    results: list,
    lit_dir: Path,
    skipped: list,
    duplicates: dict | None = None,
    citation_style: str = "gb7714",
) -> str:
    """Generate a human-readable Markdown report from extraction results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scanned = [r for r in results if r["is_scanned"]]
    light_encrypted = [r for r in results if r.get("encryption_level") == "light"]
    full_encrypted = [r for r in results if r.get("encryption_level") == "full"]
    monographs = [r for r in results if r.get("matched_chapters")]
    by_format = {}
    by_subdir: dict[str, list] = {}
    for r in results:
        fmt = r["format"]
        by_format.setdefault(fmt, []).append(r)
        subdir = str(Path(r.get("relative_path", "")).parent)
        if subdir and subdir != ".":
            by_subdir.setdefault(subdir, []).append(r)

    total_pages = sum(r["pages"] for r in results)
    total_words = sum(r["word_count"] for r in results)
    dup_count = len(duplicates) if duplicates else 0

    lines = [
        "# 文献提取报告\n",
        f"**生成时间**：{now}",
        f"**文献目录**：`{lit_dir}`\n",
        "## 汇总统计\n",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总文献数 | {len(results)} 篇 |",
        f"| 总页数（含估算） | {total_pages} 页 |",
        f"| 总字数（含估算） | {total_words} 字 |",
        f"| 扫描件（需 OCR） | {len(scanned)} 篇 |",
        f"| 轻度加密（可提取） | {len(light_encrypted)} 篇 |",
        f"| 完全加密（需解密） | {len(full_encrypted)} 篇 |",
        f"| 专著章节匹配 | {len(monographs)} 篇 |",
        f"| 疑似重复 | {dup_count} 篇 |",
        f"| 格式分布 | {', '.join(f'{k}: {len(v)} 篇' for k, v in by_format.items())} |",
        "",
    ]

    if scanned:
        lines.extend([
            "## ⚠️ 扫描件清单（需 OCR 处理）\n",
            "| 文件名 | 页数 | 状态 |",
            "|--------|------|------|",
        ])
        for r in scanned:
            lines.append(f"| {r['filename']} | {r['pages']} | 扫描 PDF，无法直接提取全文 |")
        lines.append("")
        lines.append(OCR_GUIDANCE)
        lines.append("")

    if light_encrypted:
        lines.extend([
            "## 🔓 轻度加密 PDF（可自动提取）\n",
            "| 文件名 | 页数 | 状态 |",
            "|--------|------|------|",
        ])
        for r in light_encrypted:
            lines.append(f"| {r['filename']} | {r['pages']} | 轻度加密，pdfplumber 可正常读取 |")
        lines.append("")

    if full_encrypted:
        lines.extend([
            "## 🔒 完全加密 PDF（需手动解密）\n",
            "| 文件名 | 页数 | 状态 |",
            "|--------|------|------|",
        ])
        for r in full_encrypted:
            lines.append(f"| {r['filename']} | {r['pages']} | 完全加密，PyPDF2 + pdfplumber 均无法读取 |")
        lines.append("")

    if monographs:
        lines.extend([
            "## 📖 专著章节匹配结果\n",
            "| 文件名 | 匹配章节 | 页码范围 |",
            "|--------|---------|---------|",
        ])
        for r in monographs:
            for ch in r["matched_chapters"]:
                lines.append(
                    f"| {r['filename']} | {ch['chapter']} | p.{ch['page_start']}-{ch['page_end']} |"
                )
        lines.append("")

    if duplicates:
        lines.extend([
            "## 🔁 疑似重复文献\n",
            "| 文件名 | 疑似重复对象 |",
            "|--------|-------------|",
        ])
        for fname, dlist in sorted(duplicates.items()):
            lines.append(f"| {fname} | {'; '.join(dlist)} |")
        lines.append("")

    if by_subdir:
        lines.extend(["## 按子文件夹分组\n"])
        for subdir, items in sorted(by_subdir.items()):
            lines.append(f"### {subdir} ({len(items)} 篇)\n")
            lines.append("| 文件名 | 格式 | 页数 | 字数 | 作者 | 标题 | 备注 |")
            lines.append("|--------|------|------|------|------|------|------|")
            for r in sorted(items, key=lambda x: x["filename"].lower()):
                author = r["author_from_meta"] or "—"
                title = r["title_from_meta"] or "—"
                note = r["note"] or "—"
                if len(title) > 40:
                    title = title[:37] + "..."
                if len(author) > 30:
                    author = author[:27] + "..."
                lines.append(
                    f"| {r['filename']} | {r['format']} | {r['pages']} | {r['word_count']} | "
                    f"{author} | {title} | {note} |"
                )
            lines.append("")

    lines.extend([
        "## 文献详情（按文件名排序）\n",
        "| 序号 | 文件名 | 格式 | 页数 | 字数 | 作者 | 标题 | 备注 |",
        "|------|--------|------|------|------|------|------|------|",
    ])
    for r in sorted(results, key=lambda x: x["filename"].lower()):
        author = r["author_from_meta"] or "—"
        title = r["title_from_meta"] or "—"
        note = r["note"] or "—"
        if len(title) > 40:
            title = title[:37] + "..."
        if len(author) > 30:
            author = author[:27] + "..."
        num = r.get("_citation_number", "")
        lines.append(
            f"| {num} | {r['filename']} | {r['format']} | {r['pages']} | {r['word_count']} | "
            f"{author} | {title} | {note} |"
        )
    lines.append("")

    lines.extend([
        f"## 参考文献列表（{citation_style.upper()} 格式）\n",
    ])
    for r in sorted(results, key=lambda x: x.get("_citation_number", 0)):
        citation = r.get("citation", "")
        if citation:
            lines.append(f"{r.get('_citation_number', '')}. {citation}")
    lines.append("")

    if skipped:
        lines.extend([
            "## 跳过的文件\n",
            "| 文件名 | 原因 |",
            "|--------|------|",
        ])
        for name in skipped:
            ext = Path(name).suffix.lower()
            reason = f"不支持的格式 {ext}" if ext else "无文件后缀"
            lines.append(f"| {name} | {reason} |")
        lines.append("")

    lines.append("---\n*由 efficient-literature-survey 自动生成*\n")
    return "\n".join(lines)
