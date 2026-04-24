#!/usr/bin/env python3
"""
Add Obsidian block IDs to paragraphs in a markdown file.
Block IDs are based on text fingerprints for stability.
"""

import argparse
import re
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from text_matcher import generate_block_id


def parse_markdown_paragraphs(content: str) -> list:
    """
    Parse markdown content into paragraphs.
    Returns list of dicts with text, start_pos, end_pos, and metadata.
    """
    lines = content.split('\n')
    paragraphs = []

    current_para = []
    para_start = 0
    current_chapter = None
    in_code_block = False

    for i, line in enumerate(lines):
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Detect chapter headings (## 第X章 or ## Chapter X)
        chapter_match = re.match(r'^##\s+(第\s*\d+\s*章|Chapter\s+\d+)', line)
        if chapter_match:
            current_chapter = chapter_match.group(1)

        # Detect headings (skip these)
        if re.match(r'^#{1,6}\s+', line):
            if current_para:
                # Save current paragraph
                para_text = '\n'.join(current_para).strip()
                if para_text and not para_text.startswith('^'):
                    paragraphs.append({
                        'text': para_text,
                        'start_line': para_start,
                        'end_line': i - 1,
                        'chapter': current_chapter
                    })
                current_para = []
            para_start = i + 1
            continue

        # Empty line marks paragraph boundary
        if not line.strip():
            if current_para:
                para_text = '\n'.join(current_para).strip()
                if para_text and not para_text.startswith('^'):
                    paragraphs.append({
                        'text': para_text,
                        'start_line': para_start,
                        'end_line': i - 1,
                        'chapter': current_chapter
                    })
                current_para = []
            para_start = i + 1
            continue

        current_para.append(line)

    # Handle last paragraph
    if current_para:
        para_text = '\n'.join(current_para).strip()
        if para_text and not para_text.startswith('^'):
            paragraphs.append({
                'text': para_text,
                'start_line': para_start,
                'end_line': len(lines) - 1,
                'chapter': current_chapter
            })

    return paragraphs


def add_block_ids_to_file(input_path: str, output_path: str = None) -> str:
    """
    Add block IDs to paragraphs in a markdown file.

    Args:
        input_path: Path to input markdown file
        output_path: Path to output file (default: create new file with _with_ids suffix)

    Returns:
        Path to output file
    """
    input_path = Path(input_path)
    if output_path:
        output_path = Path(output_path)
    else:
        # Create new file with _with_ids suffix
        output_path = input_path.with_stem(input_path.stem + '_with_ids')

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    paragraphs = parse_markdown_paragraphs(content)
    lines = content.split('\n')

    modified_lines = lines.copy()
    offset = 0

    for para in paragraphs:
        # Check if already has block ID
        last_line = modified_lines[para['end_line'] + offset]
        if re.search(r'\s+\^[a-zA-Z0-9-]+$', last_line.rstrip()):
            continue

        # Generate and add block ID (Obsidian requires space before ^)
        block_id = generate_block_id(para['text'])
        modified_lines[para['end_line'] + offset] = last_line.rstrip() + f" {block_id}\n"

    result = '\n'.join(modified_lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description='Add Obsidian block IDs to markdown paragraphs'
    )
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('--output', '-o', help='Output file (default: overwrite)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')

    args = parser.parse_args()

    if args.dry_run:
        with open(args.input, 'r', encoding='utf-8') as f:
            content = f.read()
        paragraphs = parse_markdown_paragraphs(content)
        print(f"Found {len(paragraphs)} paragraphs")
        for i, p in enumerate(paragraphs[:5]):
            print(f"  {i+1}. {p['text'][:50]}... → {generate_block_id(p['text'])}")
        return

    output = add_block_ids_to_file(args.input, args.output)
    print(f"Added block IDs to: {output}")


if __name__ == '__main__':
    main()
