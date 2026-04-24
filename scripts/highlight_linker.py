#!/usr/bin/env python3
"""
Link Apple Books highlights to book paragraphs using Obsidian block IDs.
Supports chapter-based organization with separated highlights and notes.
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from text_matcher import TextMatcher, normalize_text


def parse_book_paragraphs(content: str) -> list:
    """
    Parse book markdown and extract paragraphs with block IDs.

    Args:
        content: Book markdown content

    Returns:
        list: [{text, block_id, chapter, line_num}]
    """
    paragraphs = []
    lines = content.split('\n')
    current_chapter = None

    for i, line in enumerate(lines):
        # Detect chapter (## 第X章 or ## Chapter X)
        ch_match = re.match(r'^##\s+第\s*(\d+)\s*章', line)
        if ch_match:
            current_chapter = f"第 {ch_match.group(1)} 章"
            continue

        ch_match_en = re.match(r'^##\s+Chapter\s+(\d+)', line)
        if ch_match_en:
            current_chapter = f"Chapter {ch_match_en.group(1)}"
            continue

        # Find paragraphs with block IDs
        block_match = re.search(r'(\^[a-zA-Z0-9-]+)$', line.rstrip())
        if block_match:
            block_id = block_match.group(1)
            text = line[:block_match.start()].strip()

            if text and not text.startswith('#'):
                paragraphs.append({
                    'text': text,
                    'block_id': block_id,
                    'chapter': current_chapter or '未分类',
                    'line_num': i + 1
                })

    return paragraphs


def link_highlights_to_paragraphs(
    highlights: list,
    paragraphs: list,
    threshold: float = 0.75
) -> tuple:
    """
    Match highlights to paragraphs and generate links.

    Args:
        highlights: List of highlight dicts from apple_books_extractor
        paragraphs: List of paragraph dicts from block_id_adder
        threshold: Similarity threshold for fuzzy matching

    Returns:
        tuple: (linked_highlights, match_stats)
    """
    # Build matcher
    matcher = TextMatcher(threshold=threshold)
    for para in paragraphs:
        matcher.add_paragraph(para['text'], para['block_id'], para.get('chapter'))

    linked = []
    stats = {'total': len(highlights), 'matched': 0, 'unmatched': 0}

    for hl in highlights:
        if not hl.get('text') or len(hl['text']) < 5:
            stats['unmatched'] += 1
            continue

        # Find match
        result = matcher.find_match(hl['text'], hl.get('chapter'))

        if result:
            stats['matched'] += 1
            hl['block_id'] = result['block_id']
            hl['match_type'] = result['match_type']
            hl['similarity'] = result.get('similarity', 1.0)
        else:
            stats['unmatched'] += 1
            hl['block_id'] = None
            hl['match_type'] = 'none'

        linked.append(hl)

    stats['match_rate'] = stats['matched'] / stats['total'] if stats['total'] > 0 else 0

    return linked, stats


def organize_highlights_by_chapter(linked_highlights: list) -> dict:
    """
    Organize highlights by chapter, sorted by position, with notes separated.

    Args:
        linked_highlights: List of highlights with block_id

    Returns:
        dict: {chapter: {'highlights': [...], 'notes': [...]}}
    """
    # Group by chapter
    chapters = defaultdict(lambda: {'highlights': [], 'notes': []})

    for hl in linked_highlights:
        chapter = hl.get('chapter', '未分类')

        # Sort by position within chapter
        position = hl.get('position', (0, 0, 0))

        if hl.get('note'):
            chapters[chapter]['notes'].append(hl)
        else:
            chapters[chapter]['highlights'].append(hl)

    # Sort each chapter's highlights and notes by position
    for chapter in chapters:
        chapters[chapter]['highlights'].sort(key=lambda h: h.get('position', (0, 0, 0)))
        chapters[chapter]['notes'].sort(key=lambda h: h.get('position', (0, 0, 0)))

    return dict(chapters)


def sort_chapters_by_position(chapters: dict) -> list:
    """
    Sort chapters by their first highlight's position.

    Args:
        chapters: Dict of chapter data

    Returns:
        list: Sorted chapter names
    """
    def get_first_position(chapter_name):
        data = chapters.get(chapter_name, {})
        all_items = data.get('highlights', []) + data.get('notes', [])
        if all_items:
            return all_items[0].get('position', (999, 0, 0))
        return (999, 0, 0)

    return sorted(chapters.keys(), key=get_first_position)


def format_highlights_document(
    book_title: str,
    book_author: str,
    linked_highlights: list,
    book_filename: str,
    aliasest: str = ""
) -> str:
    """
    Format highlights as a Markdown document organized by chapter.

    Args:
        book_title: Book title
        book_author: Book author
        linked_highlights: List of linked highlights
        book_filename: Filename of the book (for wikilinks)
        aliasest: Other language title/alias (optional)

    Returns:
        str: Formatted Markdown content
    """
    # Organize by chapter (combine highlights and notes)
    chapters = defaultdict(list)

    for hl in linked_highlights:
        chapter = hl.get('chapter', '未分类')
        chapters[chapter].append(hl)

    # Sort each chapter's highlights by position
    for chapter in chapters:
        chapters[chapter].sort(key=lambda h: h.get('position', (0, 0, 0)))

    # Sort chapters by position
    def get_first_position(chapter_name):
        items = chapters.get(chapter_name, [])
        if items:
            return items[0].get('position', (999, 0, 0))
        return (999, 0, 0)

    sorted_chapter_names = sorted(chapters.keys(), key=get_first_position)

    # Count
    total_highlights = len(linked_highlights)
    total_notes = len([h for h in linked_highlights if h.get('note')])

    # Build frontmatter
    lines = [
        '---',
        f'aliasest: {aliasest}' if aliasest else 'aliasest:',
        f'author: {book_author}',
        f'created: {datetime.now().isoformat()}',
        f'total_highlights: {total_highlights}',
        f'total_notes: {total_notes}',
        '---',
        ''
    ]

    # Build content
    for chapter_idx, chapter_name in enumerate(sorted_chapter_names):
        chapter_items = chapters[chapter_name]

        if not chapter_items:
            continue

        # Chapter heading (level 1, preserve original title)
        lines.append(f'# {chapter_name}')
        lines.append('')

        for hl in chapter_items:
            text = hl['text'].strip()

            # Highlight text as blockquote
            lines.append(f'> {text}')

            # Link on same blockquote
            if hl.get('block_id'):
                link = f"[[{book_filename}#{hl['block_id']}|原文位置↗]]"
                lines.append(f'> {link}')
            else:
                location = hl.get('location', '未知位置')
                lines.append(f'> 位置: `{location}` (未匹配)')

            # Note if present
            if hl.get('note'):
                lines.append('')
                lines.append('**批注：**')
                lines.append(hl['note'].strip())

            lines.append('')

        # Add chapter separator between chapters (not after the last one)
        if chapter_idx < len(sorted_chapter_names) - 1:
            lines.append('---')
            lines.append('')

    return '\n'.join(lines)


def link_and_format_highlights(
    highlights: list,
    paragraphs: list,
    book_title: str,
    book_author: str,
    book_filename: str,
    threshold: float = 0.75,
    aliasest: str = ""
) -> tuple:
    """
    Full pipeline: link highlights to paragraphs and format output.

    Args:
        highlights: List of highlights from apple_books_extractor
        paragraphs: List of paragraphs from block_id_adder
        book_title: Book title
        book_author: Book author
        book_filename: Filename for wikilinks
        threshold: Matching threshold
        aliasest: Other language title/alias (optional)

    Returns:
        tuple: (formatted_markdown, match_stats)
    """
    # Link
    linked, stats = link_highlights_to_paragraphs(highlights, paragraphs, threshold)

    # Format
    formatted = format_highlights_document(
        book_title, book_author, linked, book_filename, aliasest
    )

    return formatted, stats


# Legacy function for backward compatibility
def link_highlights_to_book(
    highlights_path: str,
    book_path: str,
    output_path: Optional[str] = None
) -> str:
    """
    Legacy: Link highlights file to book file (file-based).

    Args:
        highlights_path: Path to highlights markdown file
        book_path: Path to book markdown file (with block IDs)
        output_path: Path to output file (default: overwrite highlights)

    Returns:
        Path to output file
    """
    highlights_path = Path(highlights_path)
    book_path = Path(book_path)
    output_path = Path(output_path) if output_path else highlights_path

    # Read files
    with open(highlights_path, 'r', encoding='utf-8') as f:
        hl_content = f.read()

    with open(book_path, 'r', encoding='utf-8') as f:
        book_content = f.read()

    # Parse
    paragraphs = parse_book_paragraphs(book_content)

    # Parse highlights (legacy format)
    highlights = []
    pattern = r'### 高亮 \d+\s*\n\n> ([^\n]+(?:\n>[^\n]+)*)'
    for match in re.finditer(pattern, hl_content):
        text = match.group(1).strip()
        text = re.sub(r'^> ?', '', text, flags=re.MULTILINE).strip()

        loc_match = re.search(r'位置: `([^`]+)`', hl_content[match.end():match.end()+200])
        location = loc_match.group(1) if loc_match else ""

        note_match = re.search(r'\*\*我的笔记\*\*:\s*([^\n]+)', hl_content[match.end():match.end()+300])
        note = note_match.group(1).strip() if note_match else None

        # Extract chapter from CFI
        chapter = None
        if location:
            ch_match = re.search(r'\[ch(\d+)\]', location)
            if ch_match:
                chapter = f"第 {ch_match.group(1)} 章"

        highlights.append({
            'text': text,
            'location': location,
            'chapter': chapter,
            'note': note,
            'position': (0, 0, 0)
        })

    # Link and format
    book_name = book_path.stem
    formatted, stats = link_and_format_highlights(
        highlights, paragraphs,
        book_name, 'Unknown Author',
        book_name
    )

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatted)

    print(f"Matched {stats['matched']}/{stats['total']} highlights")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description='Link Apple Books highlights to book using block IDs'
    )
    parser.add_argument('highlights', help='Highlights markdown file')
    parser.add_argument('book', help='Book markdown file with block IDs')
    parser.add_argument('--output', '-o', help='Output file (default: overwrite)')
    parser.add_argument('--dry-run', action='store_true', help='Preview matches')

    args = parser.parse_args()

    if args.dry_run:
        with open(args.highlights, 'r', encoding='utf-8') as f:
            hl_content = f.read()
        with open(args.book, 'r', encoding='utf-8') as f:
            book_content = f.read()

        paragraphs = parse_book_paragraphs(book_content)

        # Parse highlights (simplified for dry run)
        highlights = []
        pattern = r'### 高亮 \d+\s*\n\n> ([^\n]+(?:\n>[^\n]+)*)'
        for match in re.finditer(pattern, hl_content):
            text = match.group(1).strip()
            text = re.sub(r'^> ?', '', text, flags=re.MULTILINE).strip()
            highlights.append({'text': text})

        matcher = TextMatcher(threshold=0.75)
        for para in paragraphs:
            matcher.add_paragraph(para['text'], para['block_id'], para.get('chapter'))

        print(f"Found {len(highlights)} highlights, {len(paragraphs)} paragraphs")
        for i, hl in enumerate(highlights[:10]):
            result = matcher.find_match(hl['text'])
            if result:
                print(f"  ✓ {hl['text'][:30]}... → {result['block_id']}")
            else:
                print(f"  ✗ {hl['text'][:30]}... → no match")
        return

    output = link_highlights_to_book(args.highlights, args.book, args.output)
    print(f"Updated: {output}")


if __name__ == '__main__':
    main()
