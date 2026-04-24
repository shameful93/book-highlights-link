# book-highlights-link

中文 | [English](#english)

将 EPUB 电子书转换为 Obsidian 友好的 Markdown，并把 Apple Books 高亮自动链接到段落级 Block ID。

## 中文

### 功能概览

- 一键流程：EPUB 转换 + 段落 Block ID + 高亮提取 + 自动链接
- 支持提取 EPUB 图片并转为 Obsidian 图片 wikilink
- 高亮链接优先精确匹配，失败后使用模糊匹配
- 兼容中文文本规范化（繁简转换）

### 环境要求

- Python 3.9+
- macOS（读取 Apple Books 数据库）
- Apple Books 中已有对应书籍与高亮

#### macOS 权限

读取 Apple Books 数据库需要给终端授予「完全磁盘访问」：

`系统设置 -> 隐私与安全性 -> 完全磁盘访问 -> 添加 Terminal/iTerm`

### 安装

```bash
pip install -r requirements.txt
```

### 快速开始

#### 1) 列出 Apple Books 书籍并获取 Asset ID

```bash
python scripts/main.py --list-books
```

#### 2) 一键处理

```bash
python scripts/main.py \
  --epub "/path/to/book.epub" \
  --asset-id "YOUR_ASSET_ID" \
  --output-dir "./output"
```

#### 3) 预览模式（不写文件）

```bash
python scripts/main.py \
  --epub "/path/to/book.epub" \
  --asset-id "YOUR_ASSET_ID" \
  --dry-run
```

### 主要参数

- `--epub` / `-e`: EPUB 文件路径
- `--asset-id` / `-a`: Apple Books 书籍 Asset ID
- `--output-dir` / `-o`: 输出目录（默认 `./output`）
- `--threshold` / `-t`: 匹配阈值（默认 `0.75`）
- `--dry-run` / `-n`: 预览模式
- `--list-books` / `-l`: 列出 Apple Books 书籍

### 输出说明

默认输出 2 个 Markdown 文件和 1 个图片目录：

- `书名.md`：完整书籍内容（包含段落 Block ID）
- `书名_highlights.md`：高亮与批注（带回链）
- `images/`：EPUB 提取的图片资源

### 测试

```bash
pytest
```

### 已知限制

- 目前 Apple Books 提取逻辑基于 macOS 本地数据库路径。
- 书名别名在线搜索仍为占位逻辑（不影响主流程）。

### 许可证

本项目使用 MIT 许可证，详见 `LICENSE`。

---

## English

Convert EPUB books into Obsidian-friendly Markdown, then automatically link Apple Books highlights to paragraph-level Block IDs.

### Features

- One-command pipeline: EPUB conversion + paragraph Block IDs + highlight extraction + auto linking
- Extract EPUB images and convert them to Obsidian image wikilinks
- Prefer exact text matching, then fallback to fuzzy matching
- Chinese text normalization support (Traditional/Simplified conversion)

### Requirements

- Python 3.9+
- macOS (required for Apple Books local database access)
- Matching book and highlights in Apple Books

#### macOS permission

Grant your terminal app Full Disk Access:

`System Settings -> Privacy & Security -> Full Disk Access -> Add Terminal/iTerm`

### Installation

```bash
pip install -r requirements.txt
```

### Quick Start

#### 1) List Apple Books titles and get Asset ID

```bash
python scripts/main.py --list-books
```

#### 2) Run all steps in one command

```bash
python scripts/main.py \
  --epub "/path/to/book.epub" \
  --asset-id "YOUR_ASSET_ID" \
  --output-dir "./output"
```

#### 3) Dry run (no files written)

```bash
python scripts/main.py \
  --epub "/path/to/book.epub" \
  --asset-id "YOUR_ASSET_ID" \
  --dry-run
```

### Main Arguments

- `--epub` / `-e`: EPUB file path
- `--asset-id` / `-a`: Apple Books asset ID
- `--output-dir` / `-o`: output directory (default: `./output`)
- `--threshold` / `-t`: match threshold (default: `0.75`)
- `--dry-run` / `-n`: preview mode
- `--list-books` / `-l`: list books in Apple Books

### Output

By default, the tool produces two Markdown files and one image directory:

- `BookTitle.md`: full book content (with paragraph Block IDs)
- `BookTitle_highlights.md`: highlights and notes (with backlinks)
- `images/`: extracted EPUB images

### Test

```bash
pytest
```

### Known Limitations

- Apple Books extraction currently depends on macOS local database paths.
- Online title alias search is still placeholder logic (does not affect main workflow).

### License

This project is licensed under MIT. See `LICENSE`.
