#!/usr/bin/env python3
"""
PDF to Markdown converter with image extraction.
Uses pymupdf4llm for fast, high-quality conversion (no GPU needed).
Outputs Obsidian-compatible Markdown with wikilink image references.
"""

import os
import re
from pathlib import Path
from typing import Optional


def convert_pdf_to_markdown(
    pdf_path: str,
    output_dir: str,
    images_subdir: str = "images",
    skip_pages: int = 0,
    title: Optional[str] = None,
) -> dict:
    """
    Convert a PDF to Markdown with embedded images.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory for output files and images
        images_subdir: Subdirectory name for images
        skip_pages: Number of pages to skip from the start
        title: Optional title override (default: PDF metadata or filename)

    Returns:
        dict: {
            'content': str,           # Markdown content with YAML frontmatter
            'images_dir': str,        # Path to images directory
            'image_count': int,       # Number of images extracted
            'title': str,             # Document title
            'author': str,            # Document author (empty string if unknown)
            'paragraphs': list        # List of paragraph texts for matching
        }
    """
    import pymupdf4llm

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    images_dir = output_dir / images_subdir
    images_dir.mkdir(parents=True, exist_ok=True)

    # Extract PDF metadata
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    meta = doc.metadata
    total_pages = doc.page_count

    if title is None:
        title = meta.get("title", "") or pdf_path.stem

    author = meta.get("author", "") or ""
    doc.close()

    # Determine pages to process
    pages_to_process = None
    if 0 < skip_pages < total_pages:
        pages_to_process = list(range(skip_pages, total_pages))
    elif skip_pages >= total_pages:
        pages_to_process = []

    # Run pymupdf4llm conversion
    md_text = pymupdf4llm.to_markdown(
        str(pdf_path),
        pages=pages_to_process,
        write_images=True,
        image_path=str(images_dir),
        show_progress=False,
    )

    # Count extracted images
    image_files = [f for f in images_dir.iterdir() if f.is_file()]
    image_count = len(image_files)

    # Convert standard markdown images to Obsidian wikilinks
    md_text = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        lambda m: f"![[{images_subdir}/{os.path.basename(m.group(2))}]]",
        md_text,
    )

    # Extract paragraphs (same logic as epub_converter.py)
    paragraphs = []
    for line in md_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            paragraphs.append(line)

    # Build YAML frontmatter
    frontmatter = f"""---
title: "{title}"
author: "{author}"
source: "{pdf_path.name}"
---

# {title}

"""
    full_markdown = frontmatter + md_text

    return {
        "content": full_markdown,
        "images_dir": str(images_dir),
        "image_count": image_count,
        "title": title,
        "author": author,
        "paragraphs": paragraphs,
    }


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDF to Markdown")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--images-dir", default="images", help="Images subdirectory name")
    parser.add_argument("--skip-pages", type=int, default=0, help="Skip first N pages")
    parser.add_argument("--title", help="Override document title")

    args = parser.parse_args()

    result = convert_pdf_to_markdown(
        args.input,
        args.output_dir,
        args.images_dir,
        skip_pages=args.skip_pages,
        title=args.title,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    book_path = output_dir / f"{result['title']}.md"
    with open(book_path, "w", encoding="utf-8") as f:
        f.write(result["content"])

    print(f"Converted: {book_path}")
    print(f"Images: {result['image_count']} in {result['images_dir']}")


if __name__ == "__main__":
    main()
