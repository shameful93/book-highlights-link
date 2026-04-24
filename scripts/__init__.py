"""
Book Highlights Link - Scripts Package

One-click workflow to convert EPUB, add block IDs, extract Apple Books highlights, and link them.
"""

from .epub_converter import convert_epub_to_markdown
from .apple_books_extractor import extract_highlights_by_asset_id, list_all_books
from .block_id_adder import add_block_ids_to_content, parse_markdown_paragraphs
from .highlight_linker import link_and_format_highlights
from .text_matcher import TextMatcher, generate_block_id, normalize_text
