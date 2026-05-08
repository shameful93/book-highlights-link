# Book Highlights Link 更新日志

## 2026-05-08 - v2.1 PDF 转换支持

### 新增功能

**1. PDF 转 Markdown 模块** (`scripts/pdf_converter.py`)
- 基于 pymupdf4llm 的高质量 PDF→Markdown 转换
- 自动提取嵌入图片，转换为 Obsidian wikilink 格式
- 支持跳过封面/扉页 (`--skip-pages`)
- 与现有流水线完全兼容（Block ID、高亮匹配、格式化）

**2. CLI 新增 `--pdf` 参数**
- `--pdf`/`-p` 与原有 `--epub` 二选一
- `--skip-pages` 用于跳过 PDF 前 N 页
- 参数验证确保二选一且不能同时使用

### 文件改动

| 文件 | 操作 |
|------|------|
| `scripts/pdf_converter.py` | 新建 |
| `scripts/__init__.py` | 添加导出 `convert_pdf_to_markdown` |
| `scripts/main.py` | 添加 `--pdf`/`--skip-pages` 路由逻辑 |
| `requirements.txt` | 添加 `pymupdf4llm` |
| `SKILL.md` | 更新文档示例 |

### 使用方式

```bash
# PDF 转换并链接高亮
python scripts/main.py --pdf "book.pdf" --asset-id "XXX" --output-dir "./output"

# 跳过前 4 页（封面/扉页）
python scripts/main.py --pdf "book.pdf" --asset-id "XXX" --skip-pages 4
```

## 2026-04-24 - v2.0 格式升级

### 新增功能

**1. 书籍别名搜索模块** (`scripts/alias_searcher.py`)
- `build_search_query(book_title, author)` - 构建搜索查询
- `extract_english_title_from_results(search_results)` - 从搜索结果提取英文书名
- `search_book_alias(book_title, author)` - 占位函数，返回 None

**2. 高亮文档新格式**

| 项目 | 旧格式 | 新格式 |
|------|--------|--------|
| Frontmatter | `title`, `source` | `aliasest`, `author`, `created`, `total_highlights`, `total_notes` |
| 章节标题 | `## 第 N 章` | `# 原始章节标题` |
| 链接文本 | `↗原文` | `原文位置↗` |
| 高亮/批注 | 分开两个 `###` 小节 | 连续排列，批注紧跟高亮 |
| 章节分隔 | 无 | `---` 分隔线 |

### 文件改动

| 文件 | 操作 |
|------|------|
| `scripts/alias_searcher.py` | 新建 |
| `scripts/highlight_linker.py` | 重构 `format_highlights_document()`，添加 `aliasest` 参数 |
| `scripts/main.py` | 添加别名搜索调用，传递 `aliasest` 参数 |
| `tests/test_link_highlights.py` | 新增 7 个测试用例，更新现有测试 |

### API 变更

**`format_highlights_document()` 签名变更**

```python
# 旧签名
def format_highlights_document(
    book_title: str,
    book_author: str,
    linked_highlights: list,
    book_filename: str
) -> str

# 新签名
def format_highlights_document(
    book_title: str,
    book_author: str,
    linked_highlights: list,
    book_filename: str,
    aliasest: str = ""  # 新增参数
) -> str
```

**`link_and_format_highlights()` 签名变更**

```python
# 旧签名
def link_and_format_highlights(
    highlights, paragraphs, book_title, book_author, book_filename,
    threshold: float = 0.75
) -> tuple

# 新签名
def link_and_format_highlights(
    highlights, paragraphs, book_title, book_author, book_filename,
    threshold: float = 0.75,
    aliasest: str = ""  # 新增参数
) -> tuple
```

### 输出示例

**旧格式：**
```markdown
---
title: "书名 — 高亮笔记"
author: "作者"
source: "Apple Books"
created: "2026-04-24T12:00:00"
total_highlights: 32
total_notes: 5
---

# 书名 — 高亮笔记

**作者**: 作者
**高亮**: 32 条
**批注**: 5 条

---

## 第 1 章

### 高亮

> 高亮文本内容

> — 位置: `epubcfi(...)` · [[书名#^para-xxx|↗原文]]

### 批注

> 带批注的高亮

> — 位置: `epubcfi(...)` · [[书名#^para-xxx|↗原文]]

**我的笔记**: 批注内容
```

**新格式：**
```markdown
---
aliasest: Behave: The Biology of Humans at Our Best and Worst
author: 羅伯．薩波斯基（Robert M. Sapolsky）
created: 2026-04-24T16:04:44
total_highlights: 32
total_notes: 5
---

# 第 0 章

> 本书的目标是避免这种类别化的思考...
> [[书名#^para-xxx|原文位置↗]]

**批注：**
这是我的批注内容

---
# 第 1 章

> 第一章的高亮内容...
> [[书名#^para-xxx|原文位置↗]]

---
```

### 测试覆盖

- 总测试数: 15
- 新增测试: 7 (`TestNewFormat` 类)
- 全部通过: ✅

### 已知限制

1. **别名搜索为占位符** - `search_book_alias_online()` 返回空字符串，需要集成 WebSearch 工具实现实际搜索
2. **`total_highlights` 计数** - 统计所有高亮条目，包含未匹配的
3. **`aliasest` 字段** - 如用户模板所示，字段名保持为 `aliasest`（非 Obsidian 标准 `aliases`）

### 使用方式

```bash
# 基本用法
python3 scripts/main.py \
    --epub "/path/to/book.epub" \
    --asset-id "YOUR_ASSET_ID" \
    --output-dir "/path/to/output"

# 列出 Apple Books 中的书籍
python3 scripts/main.py --list-books
```
