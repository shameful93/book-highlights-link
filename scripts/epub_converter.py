#!/usr/bin/env python3
"""
EPUB to Markdown converter with image extraction.
Adapted from document-to-markdown-skill for use in book-highlights-link.
Outputs Obsidian-compatible Markdown with wikilink image references.
"""

import os
import re
from pathlib import Path
from typing import Optional

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def extract_images(book: epub.EpubBook, images_dir: str) -> dict:
    """
    Extract all images from EPUB and return a mapping.

    Args:
        book: EpubBook object from ebooklib
        images_dir: Directory to save extracted images

    Returns:
        dict: Mapping from original image paths to clean filenames
    """
    os.makedirs(images_dir, exist_ok=True)
    image_map = {}

    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        content = item.get_content()
        original_name = item.get_name()
        clean_name = sanitize_filename(os.path.basename(original_name))

        if not clean_name:
            clean_name = f"image_{len(image_map):03d}.png"

        # Determine extension from content or name
        if '.' not in clean_name:
            if b'\x89PNG' in content[:8]:
                clean_name += '.png'
            elif b'\xff\xd8' in content[:2]:
                clean_name += '.jpg'
            else:
                clean_name += '.bin'

        output_path = os.path.join(images_dir, clean_name)

        # Handle duplicates
        counter = 1
        base, ext = os.path.splitext(clean_name)
        while os.path.exists(output_path):
            clean_name = f"{base}_{counter}{ext}"
            output_path = os.path.join(images_dir, clean_name)
            counter += 1

        with open(output_path, 'wb') as f:
            f.write(content)

        # Map original src to new filename
        image_map[original_name] = clean_name
        image_map[os.path.basename(original_name)] = clean_name

    return image_map


def convert_html_to_markdown(
    html_content: str,
    image_map: dict,
    images_dir_name: str,
    cleanup: bool = True
) -> str:
    """
    Convert HTML content to Markdown with proper image references.

    Args:
        html_content: HTML string
        image_map: Mapping from original paths to clean filenames
        images_dir_name: Name of images directory (relative path)
        cleanup: Whether to remove script/style/empty elements

    Returns:
        str: Markdown content with Obsidian wikilink images
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    if cleanup:
        for element in soup.find_all(['script', 'style']):
            element.decompose()

        for p in soup.find_all('p'):
            if not p.get_text(strip=True) and not p.find('img'):
                p.decompose()

    # Convert image src to Obsidian wikilink format
    for img in soup.find_all('img'):
        src = img.get('src', '')
        clean_name = image_map.get(src, image_map.get(os.path.basename(src), None))

        if clean_name:
            img['src'] = f"{images_dir_name}/{clean_name}"
            img['data-obsidian'] = f"[[{images_dir_name}/{clean_name}]]"

    # Convert to Markdown
    markdown = md(str(soup), heading_style='atx', strip=['script', 'style'])

    # Post-process image links to Obsidian format
    for original_src, clean_name in image_map.items():
        old_format = f"![{clean_name}]({images_dir_name}/{clean_name})"
        new_format = f"![[{images_dir_name}/{clean_name}]]"
        markdown = markdown.replace(old_format, new_format)

        old_format_alt = f"![]({images_dir_name}/{clean_name})"
        markdown = markdown.replace(old_format_alt, new_format)

    return markdown


def convert_epub_to_markdown(
    epub_path: str,
    output_dir: str,
    images_subdir: str = "images",
    cleanup: bool = True,
    title: Optional[str] = None
) -> dict:
    """
    Convert an EPUB file to Markdown with images.

    Args:
        epub_path: Path to EPUB file
        output_dir: Directory for output files
        images_subdir: Subdirectory name for images
        cleanup: Whether to clean up HTML before conversion
        title: Optional title override

    Returns:
        dict: {
            'content': str,           # Markdown content
            'images_dir': str,        # Path to images directory
            'image_count': int,       # Number of images extracted
            'title': str,             # Book title
            'author': str,            # Book author
            'paragraphs': list        # List of paragraph texts
        }
    """
    epub_path = Path(epub_path)
    output_dir = Path(output_dir)

    images_dir = output_dir / images_subdir
    images_dir_name = images_subdir

    # Read EPUB
    book = epub.read_epub(str(epub_path))

    # Extract metadata
    if title is None:
        title_meta = book.get_metadata('DC', 'title')
        title = title_meta[0][0] if title_meta else epub_path.stem

    author_meta = book.get_metadata('DC', 'creator')
    author = author_meta[0][0] if author_meta else 'Unknown'

    # Extract images
    image_map = extract_images(book, str(images_dir))

    # Process documents in spine order
    all_markdown = []
    paragraphs = []

    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                content = item.get_content()
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace')

                markdown = convert_html_to_markdown(
                    content, image_map, images_dir_name, cleanup
                )

                if markdown.strip():
                    all_markdown.append(markdown)

                    # Extract paragraphs for matching
                    for line in markdown.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            paragraphs.append(line)

            except Exception as e:
                print(f"Warning: Failed to process item {item_id}: {e}")

    # Combine all markdown
    full_markdown = '\n\n---\n\n'.join(all_markdown)

    # Add YAML frontmatter
    frontmatter = f"""---
title: "{title}"
author: "{author}"
source: "{epub_path.name}"
---

# {title}

"""

    full_markdown = frontmatter + full_markdown

    return {
        'content': full_markdown,
        'images_dir': str(images_dir),
        'image_count': len(image_map),
        'title': title,
        'author': author,
        'paragraphs': paragraphs
    }


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert EPUB to Markdown')
    parser.add_argument('input', help='Input EPUB file')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--images-dir', default='images', help='Images subdirectory name')
    parser.add_argument('--no-cleanup', action='store_true', help='Disable HTML cleanup')
    parser.add_argument('--title', help='Override document title')

    args = parser.parse_args()

    result = convert_epub_to_markdown(
        args.input,
        args.output_dir,
        args.images_dir,
        cleanup=not args.no_cleanup,
        title=args.title
    )

    # Write output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    book_path = output_dir / f"{result['title']}.md"
    with open(book_path, 'w', encoding='utf-8') as f:
        f.write(result['content'])

    print(f"Converted: {book_path}")
    print(f"Images: {result['image_count']} in {result['images_dir']}")


if __name__ == '__main__':
    main()
