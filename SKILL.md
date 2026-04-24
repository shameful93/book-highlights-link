---
name: book-highlights-link
description: One-click workflow to convert EPUB, extract Apple Books highlights, and create Obsidian wikilinks. Use when you want to link your Apple Books reading notes to converted book markdown files.
---

# Book Highlights Linker

One-click workflow: Convert EPUB to Markdown with images, extract Apple Books highlights, and create Obsidian wikilinks for precise paragraph-level navigation.

## When to Use This Skill

Use when you want to:
- Convert EPUB to Markdown with images extracted
- Link Apple Books highlights to the converted book
- Create stable paragraph-level links (not line numbers)
- Build an integrated reading notes system in Obsidian

## Quick Start

### One-Click Workflow

```bash
python scripts/main.py \
    --epub "/path/to/book.epub" \
    --asset-id "YOUR_ASSET_ID" \
    --output-dir "/path/to/output"
```

This single command will:
1. Convert EPUB to Markdown, extracting images
2. Add stable block IDs to all paragraphs
3. Extract highlights from Apple Books by asset ID
4. Link highlights to paragraphs with Obsidian wikilinks

### Find Your Asset ID

List all books in your Apple Books library:

```bash
python scripts/main.py --list-books
```

Output:
```
  1. 书名                                       | 作者                   |  32 条
      Asset ID: YOUR_ASSET_ID
```

### Preview Mode

Preview without writing files:

```bash
python scripts/main.py --epub "book.epub" --asset-id "XXX" --dry-run
```

## Output Files

The workflow produces exactly **2 files**:

### 1. Book Markdown (`书名.md`)

Contains:
- YAML frontmatter with title, author, source
- Full book content with images as Obsidian wikilinks: `![[images/xxx.png]]`
- Stable block IDs on every paragraph: `^para-xxxxxx`

```markdown
---
title: "书名"
author: "作者"
source: "book.epub"
---

# 书名

## 第1章

这是第一段内容。 ![[images/ch1_001.png]] ^para-a1b2c3

这是第二段内容。 ^para-d4e5f6
```

### 2. Highlights Markdown (`书名_highlights.md`)

Organized by chapter, with highlights and notes separated:

```markdown
---
title: "书名 — 高亮笔记"
author: "作者"
source: "Apple Books"
total_highlights: 32
total_notes: 5
---

# 书名 — 高亮笔记

## 第1章

### 高亮

> 高亮文本1

> — 位置: `epubcfi(...)` · [[书名#^para-a1b2c3|↗原文]]

### 批注

> 带批注的高亮文本

> — 位置: `epubcfi(...)` · [[书名#^para-xxx|↗原文]]

**我的笔记**: 用户批注内容
```

## Key Features

### Image Support

Images are automatically extracted from EPUB and converted to Obsidian wikilink format:

```
![[images/chapter1_001.png]]
```

### Stable Block IDs

Block IDs are based on text fingerprints (MD5 hash), ensuring stability:
- IDs survive book edits
- Same paragraph = same ID
- No line number dependencies

### Smart Text Matching

1. **Exact match**: Search for highlight text as substring
2. **Fuzzy match**: Calculate similarity ratio (threshold: 0.75)
3. **Chapter hint**: Use CFI chapter info to narrow search

### Traditional/Simplified Chinese Support

Automatically converts between traditional and simplified Chinese for better matching.

## Prerequisites

### Required Permissions

Apple Books databases require **Full Disk Access**:
- System Settings → Privacy & Security → Full Disk Access
- Add Terminal (or your terminal app)

### Dependencies

```bash
pip install ebooklib beautifulsoup4 markdownify zhconv
```

## CLI Reference

```bash
# One-click workflow
python scripts/main.py --epub "book.epub" --asset-id "XXX" --output-dir "./output"

# List books in Apple Books
python scripts/main.py --list-books

# Dry run (preview)
python scripts/main.py --epub "book.epub" --asset-id "XXX" --dry-run

# Adjust matching threshold
python scripts/main.py --epub "book.epub" --asset-id "XXX" --threshold 0.8

# Verbose output
python scripts/main.py --epub "book.epub" --asset-id "XXX" --verbose
```

## Module Reference

For programmatic use:

```python
from scripts import (
    convert_epub_to_markdown,
    extract_highlights_by_asset_id,
    add_block_ids_to_content,
    link_and_format_highlights
)

# Step 1: Convert EPUB
epub_result = convert_epub_to_markdown(epub_path, output_dir)

# Step 2: Add block IDs
book_content, paragraphs = add_block_ids_to_content(epub_result['content'])

# Step 3: Extract highlights
highlights, metadata = extract_highlights_by_asset_id(asset_id)

# Step 4: Link and format
formatted, stats = link_and_format_highlights(
    highlights, paragraphs,
    book_title, book_author, book_filename
)
```

## Troubleshooting

### Low Match Rate

- Check book encoding (should be UTF-8)
- Try lower threshold: `--threshold 0.6`
- Verify highlights file format

### Permission Denied

If you see errors accessing Apple Books databases:
1. Open System Settings
2. Go to Privacy & Security → Full Disk Access
3. Add Terminal (or your terminal app)
4. Restart terminal

### Missing Images

- Check EPUB contains images
- Verify output directory is writable

## Workflow Comparison

| Old Workflow | New Workflow |
|--------------|--------------|
| 4 separate commands | 1 command |
| 4 output files | 2 output files |
| Manual file management | Automatic |
| No image support | Images extracted |
| Mixed highlights/notes | Separated by type |
