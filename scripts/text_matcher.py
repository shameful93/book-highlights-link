"""
Text matching utilities for book highlights linking.
Provides block ID generation and text matching algorithms.
"""

import hashlib
import re

try:
    from zhconv import convert
    HAS_ZHCONV = True
except ImportError:
    HAS_ZHCONV = False


def to_simplified(text: str) -> str:
    """Convert traditional Chinese to simplified Chinese."""
    if HAS_ZHCONV:
        return convert(text, 'zh-cn')
    return text


def generate_block_id(text: str) -> str:
    """
    Generate a stable Obsidian block ID from text.
    Uses MD5 hash of first 50 characters.

    Args:
        text: The paragraph text

    Returns:
        Block ID in format ^para-xxxxxx (6 hex chars)
    """
    # Take first 50 characters for stability
    sample = text[:50]

    # Generate MD5 hash and take first 6 hex chars
    hash_obj = hashlib.md5(sample.encode('utf-8'))
    hex_digest = hash_obj.hexdigest()[:6]

    return f"^para-{hex_digest}"


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    Removes whitespace, normalizes punctuation, and converts to simplified Chinese.
    """
    # Convert traditional Chinese to simplified
    text = to_simplified(text)

    text = re.sub(r'\s+', '', text)
    # Normalize Chinese punctuation
    replacements = {
        '，': ',', '。': '.', '、': ',',
        '：': ':', '；': ';', '！': '!',
        '？': '?', '"': '"', '"': '"',
        ''': "'", ''': "'", '（': '(',
        '）': ')', '【': '[', '】': ']',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity ratio between two texts.
    Uses sequence matcher for fuzzy matching.

    Returns:
        Float between 0.0 and 1.0
    """
    from difflib import SequenceMatcher

    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    return SequenceMatcher(None, norm1, norm2).ratio()


class TextMatcher:
    """
    Matches highlight text to book paragraphs.
    Supports exact and fuzzy matching.
    """

    def __init__(self, threshold: float = 0.8):
        """
        Args:
            threshold: Minimum similarity for fuzzy match (0.0-1.0)
        """
        self.threshold = threshold
        self.paragraphs = []  # List of (text, block_id, chapter)

    def add_paragraph(self, text: str, block_id: str, chapter: str = None):
        """Add a paragraph to the matcher index."""
        self.paragraphs.append({
            'text': text,
            'normalized': normalize_text(text),
            'block_id': block_id,
            'chapter': chapter
        })

    def find_match(self, highlight_text: str, chapter_hint: str = None) -> dict:
        """
        Find matching paragraph for a highlight.

        Args:
            highlight_text: The highlighted text
            chapter_hint: Optional chapter to search within

        Returns:
            dict with 'block_id', 'similarity', 'chapter' or None if no match
        """
        hl_norm = normalize_text(highlight_text)
        search_text = hl_norm[:60]  # Use first 60 chars for matching

        best_match = None
        best_score = 0.0

        # Filter by chapter if hint provided
        candidates = self.paragraphs
        if chapter_hint:
            candidates = [p for p in self.paragraphs
                         if p['chapter'] == chapter_hint] or self.paragraphs

        for para in candidates:
            # Exact substring match
            if search_text in para['normalized']:
                return {
                    'block_id': para['block_id'],
                    'similarity': 1.0,
                    'chapter': para['chapter'],
                    'match_type': 'exact'
                }

            # Fuzzy match
            similarity = calculate_similarity(search_text, para['normalized'][:80])
            if similarity > best_score:
                best_score = similarity
                best_match = para

        # Return fuzzy match if above threshold
        if best_score >= self.threshold:
            return {
                'block_id': best_match['block_id'],
                'similarity': best_score,
                'chapter': best_match['chapter'],
                'match_type': 'fuzzy'
            }

        return None
