#!/usr/bin/env python3
"""
Search for book aliases (other language titles) using web search.
"""

import re
from typing import Optional


def extract_english_title_from_results(search_results: str) -> Optional[str]:
    """
    Extract English title from search results.

    Args:
        search_results: Raw search results text

    Returns:
        English title if found, None otherwise
    """
    # Common patterns for English book titles
    patterns = [
        r'["\']([A-Z][A-Za-z\s:\-,\']+?)["\']',  # Quoted title
        r'^([A-Z][A-Za-z\s:\-,\']+?)\s+by\s+',  # Title by Author
        r'title[:\s]+([A-Z][A-Za-z\s:\-,\']+)',  # Title: XXX
    ]

    for pattern in patterns:
        match = re.search(pattern, search_results, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Filter out common false positives
            if len(title) > 3 and title not in ['The', 'A', 'An', 'Book', 'Read', 'Click', 'More', 'Home', 'About', 'Page', 'Chapter']:
                return title

    return None


def search_book_alias(book_title: str, author: str = "") -> Optional[str]:
    """
    Search for book's other language title (usually English original).

    Args:
        book_title: Chinese or translated book title
        author: Author name (optional)

    Returns:
        English/original title if found, None otherwise

    Note:
        This function is designed to be called from main.py with WebSearch tool.
        The actual web search is done by the caller, this function processes results.
    """
    # Placeholder - actual search done by caller using WebSearch tool
    return None


def build_search_query(book_title: str, author: str = "") -> str:
    """
    Build a search query for finding the original book title.

    Args:
        book_title: Book title
        author: Author name

    Returns:
        Search query string
    """
    # Clean title
    clean_title = re.sub(r'\s+', ' ', book_title).strip()

    if author:
        # Remove Chinese author prefix if present
        clean_author = re.sub(r'^(作者：|著者：|by\s*)', '', author).strip()
        return f'"{clean_title}" {clean_author} original english title'
    else:
        return f'"{clean_title}" book original english title'
