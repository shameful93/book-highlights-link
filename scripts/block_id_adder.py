#!/usr/bin/env python3
"""
Add Obsidian block IDs to paragraphs in a markdown file.
Block IDs are based on text fingerprints for stability.
Supports both file-based and in-memory processing.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from text_matcher import generate_block_id


def parse_markdown_paragraphs(content: str) -> list:
    """
    Parse markdown content into paragraphs.

    Args:
        content: Markdown content string

    Returns:
        list: [{text, start_line, end_line, chapter, block_id}]
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
                    block_id = generate_block_id(para_text)
                    paragraphs.append({
                        'text': para_text,
                        'start_line': para_start,
                        'end_line': i - 1,
                        'chapter': current_chapter,
                        'block_id': block_id
                    })
                current_para = []
            para_start = i + 1
            continue

        # Empty line marks paragraph boundary
        if not line.strip():
            if current_para:
                para_text = '\n'.join(current_para).strip()
                if para_text and not para_text.startswith('^'):
                    block_id = generate_block_id(para_text)
                    paragraphs.append({
                        'text': para_text,
                        'start_line': para_start,
                        'end_line': i - 1,
                        'chapter': current_chapter,
                        'block_id': block_id
                    })
                current_para = []
            para_start = i + 1
            continue

        current_para.append(line)

    # Handle last paragraph
    if current_para:
        para_text = '\n'.join(current_para).strip()
        if para_text and not para_text.startswith('^'):
            block_id = generate_block_id(para_text)
            paragraphs.append({
                'text': para_text,
                'start_line': para_start,
                'end_line': len(lines) - 1,
                'chapter': current_chapter,
                'block_id': block_id
            })

    return paragraphs


def add_block_ids_to_content(content: str) -> tuple:
    """
    Add block IDs to paragraphs in markdown content (in-memory).

    Args:
        content: Markdown content string

    Returns:
        tuple: (modified_content, paragraphs_list)
            modified_content: Content with block IDs added
            paragraphs_list: [{text, block_id, chapter, start_line, end_line}]
    """
    paragraphs = parse_markdown_paragraphs(content)
    lines = content.split('\n')

    # Track modifications with offset
    modifications = []  # (line_index, block_id)

    for para in paragraphs:
        last_line_idx = para['end_line']
        last_line = lines[last_line_idx]

        # Check if already has block ID
        if re.search(r'\s+\^[a-zA-Z0-9-]+$', last_line.rstrip()):
            continue

        modifications.append((last_line_idx, para['block_id']))

    # Apply modifications (reverse order to maintain indices)
    for line_idx, block_id in reversed(modifications):
        lines[line_idx] = lines[line_idx].rstrip() + f" {block_id}"

    return '\n'.join(lines), paragraphs


def add_block_ids_to_file(input_path: str, output_path: Optional[str] = None) -> tuple:
    """
    Add block IDs to paragraphs in a markdown file.

    Args:
        input_path: Path to input markdown file
        output_path: Path to output file (default: overwrite input)

    Returns:
        tuple: (output_path, paragraphs_list)
    """
    input_path = Path(input_path)
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = input_path

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    modified_content, paragraphs = add_block_ids_to_content(content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    return str(output_path), paragraphs


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
            print(f"  {i+1}. {p['text'][:50]}... → {p['block_id']}")
        return

    output, paragraphs = add_block_ids_to_file(args.input, args.output)
    print(f"Added {len(paragraphs)} block IDs to: {output}")


if __name__ == '__main__':
    main()
