#!/usr/bin/env python3
"""
One-click workflow: Convert EPUB, add block IDs, extract highlights, link.

Usage:
    python scripts/main.py \
        --epub "/path/to/book.epub" \
        --asset-id "29440D1AB4B9D31BD8D64C821D65F79E" \
        --output-dir "/path/to/output"

    python scripts/main.py --list-books
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from epub_converter import convert_epub_to_markdown
from apple_books_extractor import (
    extract_highlights_by_asset_id,
    list_all_books,
    find_databases
)
from block_id_adder import add_block_ids_to_content
from highlight_linker import link_and_format_highlights
from alias_searcher import build_search_query, extract_english_title_from_results


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    if not name:
        return "Untitled"
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = re.sub(r'[\x00-\x1f]', '', cleaned)
    cleaned = cleaned.strip()[:200]
    return cleaned if cleaned else "Untitled"


def check_dependencies() -> bool:
    """Check all required packages are installed."""
    missing = []

    try:
        import ebooklib
    except ImportError:
        missing.append('ebooklib')

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append('beautifulsoup4')

    try:
        from markdownify import markdownify
    except ImportError:
        missing.append('markdownify')

    try:
        from zhconv import convert
    except ImportError:
        missing.append('zhconv (optional, for Chinese text normalization)')

    if missing:
        required = [m for m in missing if 'optional' not in m]
        if required:
            print("缺少依赖包，请安装:")
            print(f"  pip install {' '.join(required)}")
            return False
        else:
            print("可选依赖包未安装 (不影响基本功能):")
            print(f"  pip install {' '.join(missing)}")
    return True


def search_book_alias_online(book_title: str, author: str) -> str:
    """
    Search for book's English/original title online.

    Args:
        book_title: Book title
        author: Author name

    Returns:
        English/original title if found, empty string otherwise
    """
    try:
        import subprocess
        import json

        query = build_search_query(book_title, author)

        # Use WebSearch via claude CLI or fallback to empty
        # This is a placeholder - actual implementation needs WebSearch access
        # For now, return empty and let user fill in manually
        return ""

    except Exception:
        return ""


def process_book(
    epub_path: str,
    asset_id: str,
    output_dir: str,
    match_threshold: float = 0.75,
    dry_run: bool = False,
    verbose: bool = False
) -> dict:
    """
    Full pipeline: Convert EPUB, add block IDs, extract highlights, link.

    Args:
        epub_path: Path to EPUB file
        asset_id: Apple Books asset ID
        output_dir: Output directory
        match_threshold: Text matching threshold
        dry_run: Preview without writing
        verbose: Verbose output

    Returns:
        dict: Result with file paths and stats
    """
    output_dir = Path(output_dir)
    result = {
        'success': False,
        'book_path': None,
        'highlights_path': None,
        'images_dir': None,
        'stats': {}
    }

    # Step 1: Convert EPUB to Markdown
    print("\n📖 Step 1: 转换 EPUB...")
    try:
        epub_result = convert_epub_to_markdown(
            epub_path,
            str(output_dir),
            images_subdir="images",
            cleanup=True
        )
        print(f"  ✓ 提取 {epub_result['image_count']} 张图片")
        print(f"  ✓ 书名: {epub_result['title']}")
        print(f"  ✓ 作者: {epub_result['author']}")

        result['images_dir'] = epub_result['images_dir']
        result['stats']['image_count'] = epub_result['image_count']

    except Exception as e:
        print(f"  ✗ EPUB 转换失败: {e}")
        return result

    # Step 2: Add Block IDs
    print("\n🏷️  Step 2: 添加 Block ID...")
    try:
        book_content, paragraphs = add_block_ids_to_content(epub_result['content'])
        print(f"  ✓ 生成 {len(paragraphs)} 个段落 Block ID")

        result['stats']['paragraph_count'] = len(paragraphs)

    except Exception as e:
        print(f"  ✗ 添加 Block ID 失败: {e}")
        return result

    # Step 3: Extract Highlights from Apple Books
    print("\n📚 Step 3: 提取 Apple Books 高亮...")
    try:
        highlights, metadata = extract_highlights_by_asset_id(asset_id)
        print(f"  ✓ 找到 {len(highlights)} 条高亮/批注")
        print(f"  ✓ 书名: {metadata['title']}")

        result['stats']['highlight_count'] = len(highlights)

    except FileNotFoundError as e:
        print(f"  ✗ 无法访问 Apple Books 数据库: {e}")
        print("  提示: 请确保终端有「完全磁盘访问」权限")
        print("  (系统设置 → 隐私与安全性 → 完全磁盘访问)")
        return result
    except Exception as e:
        print(f"  ✗ 提取高亮失败: {e}")
        return result

    # Step 4: Link and Format
    print("\n🔗 Step 4: 链接高亮到书籍...")
    try:
        book_filename = sanitize_filename(epub_result['title'])

        # Search for book alias (non-blocking)
        print("  正在搜索书籍别名...")
        aliasest = search_book_alias_online(epub_result['title'], epub_result['author'])
        if aliasest:
            print(f"  ✓ 找到别名: {aliasest}")
        else:
            print("  未找到别名，字段留空")

        formatted_highlights, match_stats = link_and_format_highlights(
            highlights=highlights,
            paragraphs=paragraphs,
            book_title=epub_result['title'],
            book_author=epub_result['author'],
            book_filename=book_filename,
            threshold=match_threshold,
            aliasest=aliasest
        )

        print(f"  ✓ 匹配 {match_stats['matched']}/{match_stats['total']} 条高亮")
        print(f"  ✓ 匹配率: {match_stats['match_rate']:.1%}")

        result['stats']['match_rate'] = match_stats['match_rate']
        result['stats']['matched'] = match_stats['matched']
        result['stats']['unmatched'] = match_stats['unmatched']

    except Exception as e:
        print(f"  ✗ 链接失败: {e}")
        return result

    # Step 5: Write Output
    if not dry_run:
        print("\n💾 Step 5: 写入文件...")
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Book file
            book_path = output_dir / f"{book_filename}.md"
            with open(book_path, 'w', encoding='utf-8') as f:
                f.write(book_content)
            print(f"  ✓ 书籍: {book_path}")
            result['book_path'] = str(book_path)

            # Highlights file
            highlights_path = output_dir / f"{book_filename}_highlights.md"
            with open(highlights_path, 'w', encoding='utf-8') as f:
                f.write(formatted_highlights)
            print(f"  ✓ 高亮: {highlights_path}")
            result['highlights_path'] = str(highlights_path)

        except Exception as e:
            print(f"  ✗ 写入文件失败: {e}")
            return result
    else:
        print("\n[DRY RUN] 预览完成，未写入文件")

    result['success'] = True
    return result


def main():
    parser = argparse.ArgumentParser(
        description='One-click: Convert EPUB, add block IDs, extract highlights, link',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换书籍并链接高亮
  python scripts/main.py --epub "book.epub" --asset-id "XXX" --output-dir "./output"

  # 列出 Apple Books 中的书籍
  python scripts/main.py --list-books

  # 预览模式
  python scripts/main.py --epub "book.epub" --asset-id "XXX" --dry-run
        """
    )

    parser.add_argument('--epub', '-e', help='EPUB 文件路径')
    parser.add_argument('--asset-id', '-a', help='Apple Books Asset ID')
    parser.add_argument('--output-dir', '-o', default='./output', help='输出目录')
    parser.add_argument('--threshold', '-t', type=float, default=0.75,
                        help='文本匹配阈值 (默认 0.75)')
    parser.add_argument('--dry-run', '-n', action='store_true', help='预览模式')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--list-books', '-l', action='store_true',
                        help='列出 Apple Books 中的书籍')

    args = parser.parse_args()

    # Check dependencies
    if not check_dependencies():
        return 1

    # List books mode
    if args.list_books:
        print("\n📚 Apple Books 书籍列表:\n")
        try:
            books = list_all_books()
            if not books:
                print("  未找到任何书籍")
                return 0

            print("-" * 80)
            for i, book in enumerate(books, 1):
                title = book['title'][:40]
                author = book['author'][:20]
                count = book['highlight_count']
                asset_id = book['asset_id']
                print(f"  {i:2d}. {title:<42} | {author:<22} | {count:3d} 条")
                print(f"      Asset ID: {asset_id}")
            print("-" * 80)
            print(f"\n共 {len(books)} 本书")
            print("\n提示: 使用 --asset-id 参数指定要处理的书籍")
            return 0

        except FileNotFoundError as e:
            print(f"  ✗ {e}")
            print("\n请确保:")
            print("  1. Apple Books 中有高亮笔记")
            print("  2. 已授予终端「完全磁盘访问」权限")
            print("     (系统设置 → 隐私与安全性 → 完全磁盘访问)")
            return 1

    # Process book mode
    if not args.epub or not args.asset_id:
        print("错误: 需要指定 --epub 和 --asset-id")
        print("使用 --list-books 查看可用书籍")
        return 1

    if not os.path.exists(args.epub):
        print(f"错误: EPUB 文件不存在: {args.epub}")
        return 1

    print("=" * 60)
    print("Book Highlights Link - 一键处理")
    print("=" * 60)
    print(f"\nEPUB: {args.epub}")
    print(f"Asset ID: {args.asset_id}")
    print(f"输出目录: {args.output_dir}")

    result = process_book(
        epub_path=args.epub,
        asset_id=args.asset_id,
        output_dir=args.output_dir,
        match_threshold=args.threshold,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    print("\n" + "=" * 60)
    if result['success']:
        if args.dry_run:
            print("预览完成 ✓")
        else:
            print("处理完成 ✓")
            print(f"\n输出文件:")
            print(f"  书籍: {result['book_path']}")
            print(f"  高亮: {result['highlights_path']}")
            if result['images_dir']:
                print(f"  图片: {result['images_dir']}")
            print(f"\n统计:")
            stats = result['stats']
            print(f"  段落数: {stats.get('paragraph_count', 0)}")
            print(f"  图片数: {stats.get('image_count', 0)}")
            print(f"  高亮数: {stats.get('highlight_count', 0)}")
            print(f"  匹配率: {stats.get('match_rate', 0):.1%}")
    else:
        print("处理失败 ✗")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
