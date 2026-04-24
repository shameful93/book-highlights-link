#!/usr/bin/env python3
"""
Link Apple Books highlights to book markdown file using Obsidian block IDs.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from text_matcher import TextMatcher, normalize_text, generate_block_id


def parse_highlights(content: str) -> list:
    """
    Parse highlights from Apple Books sync output.

    Returns list of dicts with text, location, chapter, note.
    """
    highlights = []

    # Match highlight blocks
    # Format: ### 高亮 N\n\n> text\n\n> — 位置: `cfi`
    pattern = r'### 高亮 \d+\s*\n\n> ([^\n]+(?:\n>[^\n]+)*)'

    for match in re.finditer(pattern, content):
        text = match.group(1).strip()
        text = re.sub(r'^> ?', '', text, flags=re.MULTILINE).strip()

        # Extract location
        loc_match = re.search(r'位置: `([^`]+)`', content[match.end():match.end()+200])
        location = loc_match.group(1) if loc_match else ""

        # Extract chapter from CFI
        chapter = None
        if location:
            ch_match = re.search(r'\[ch(\d+)\]', location)
            if ch_match:
                chapter = f"ch{ch_match.group(1).zfill(2)}"

        # Extract note if present
        note_match = re.search(r'\*\*我的笔记\*\*:\s*([^\n]+)', content[match.end():match.end()+300])
        note = note_match.group(1).strip() if note_match else None

        highlights.append({
            'text': text,
            'location': location,
            'chapter': chapter,
            'note': note,
            'full_match': match.group(0)
        })

    return highlights


def parse_book_paragraphs(content: str) -> list:
    """
    Parse book markdown and extract paragraphs with block IDs.
    """
    paragraphs = []
    lines = content.split('\n')
    current_chapter = None

    for i, line in enumerate(lines):
        # Detect chapter
        ch_match = re.match(r'^##\s+第\s*(\d+)\s*章', line)
        if ch_match:
            current_chapter = f"ch{ch_match.group(1).zfill(2)}"
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
                    'chapter': current_chapter,
                    'line_num': i + 1
                })

    return paragraphs


def link_highlights_to_book(highlights_path: str, book_path: str,
                            output_path: str = None) -> str:
    """
    Link highlights to book paragraphs using block IDs.

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
    highlights = parse_highlights(hl_content)
    paragraphs = parse_book_paragraphs(book_content)

    # Build matcher
    matcher = TextMatcher(threshold=0.75)
    for para in paragraphs:
        matcher.add_paragraph(para['text'], para['block_id'], para['chapter'])

    # Link
    book_name = book_path.stem
    matched_count = 0

    for hl in highlights:
        if not hl['text'] or len(hl['text']) < 5:
            continue

        # Find match
        result = matcher.find_match(hl['text'], hl['chapter'])

        if result:
            matched_count += 1
            block_id = result['block_id']
            link = f"[[{book_name}#{block_id}|↗原文]]"

            # Add link after location
            if hl['location']:
                old = f"> — 位置: `{hl['location']}`"
                new = f"> — 位置: `{hl['location']}` · {link}"
                hl_content = hl_content.replace(old, new, 1)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(hl_content)

    print(f"Matched {matched_count}/{len(highlights)} highlights")
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

        highlights = parse_highlights(hl_content)
        paragraphs = parse_book_paragraphs(book_content)

        matcher = TextMatcher(threshold=0.75)
        for para in paragraphs:
            matcher.add_paragraph(para['text'], para['block_id'], para['chapter'])

        print(f"Found {len(highlights)} highlights, {len(paragraphs)} paragraphs")
        for i, hl in enumerate(highlights[:10]):
            result = matcher.find_match(hl['text'], hl['chapter'])
            if result:
                print(f"  ✓ {hl['text'][:30]}... → {result['block_id']}")
            else:
                print(f"  ✗ {hl['text'][:30]}... → no match")
        return

    output = link_highlights_to_book(args.highlights, args.book, args.output)
    print(f"Updated: {output}")


if __name__ == '__main__':
    main()
