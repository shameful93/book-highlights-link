#!/usr/bin/env python3
"""
Extract highlights from Apple Books SQLite database by asset ID.
Adapted from apple-books-sync for use in book-highlights-link.
"""

import glob
import os
import re
import sqlite3
from datetime import datetime
from typing import Optional


# Core Data timestamp offset (seconds from 2001-01-01 to Unix epoch)
CORE_DATA_OFFSET = 978307200

# Annotation type mapping
TYPE_MAP = {
    1: 'bookmark',
    2: 'highlight',
    3: 'note',
}


def find_databases() -> tuple:
    """
    Find Apple Books SQLite databases.

    Returns:
        tuple: (annotation_db_path, library_db_path)

    Raises:
        FileNotFoundError: If databases not found
    """
    home = os.path.expanduser("~")
    container = f"{home}/Library/Containers/com.apple.iBooksX/Data/Documents"

    annotation_pattern = f"{container}/AEAnnotation/AEAnnotation*.sqlite"
    library_pattern = f"{container}/BKLibrary/BKLibrary*.sqlite"

    annotation_dbs = glob.glob(annotation_pattern)
    library_dbs = glob.glob(library_pattern)

    if not annotation_dbs:
        raise FileNotFoundError(f"Annotation database not found at {annotation_pattern}")
    if not library_dbs:
        raise FileNotFoundError(f"Library database not found at {library_pattern}")

    return annotation_dbs[0], library_dbs[0]


def convert_coredata_timestamp(timestamp: Optional[float]) -> Optional[str]:
    """Convert Core Data timestamp to ISO format string."""
    if timestamp is None:
        return None
    unix_ts = timestamp + CORE_DATA_OFFSET
    return datetime.fromtimestamp(unix_ts).isoformat()


def extract_section_from_cfi(cfi: str) -> Optional[str]:
    """
    Extract section identifier from CFI for grouping.

    Args:
        cfi: EPUB CFI string like 'epubcfi(/6/16[ch00]!/4/50,/1:0,/5:2)'

    Returns:
        Section identifier or None
    """
    if not cfi:
        return None

    cfi = str(cfi)
    match = re.search(r'\[([^\]]+)\]', cfi)
    if not match:
        return None

    return match.group(1)


def format_section_name(section_id: str) -> str:
    """
    Convert section identifier to readable chapter name.

    Args:
        section_id: Section identifier from CFI

    Returns:
        Human-readable chapter name
    """
    if not section_id:
        return "未分类"

    name = section_id

    # Check for common section prefixes
    for prefix in ['Section', 'chapter', 'Chapter', 'ch', 'part', 'Part']:
        if name.lower().startswith(prefix.lower()):
            num_match = re.search(r'(\d+)', name[len(prefix):])
            if num_match:
                num = int(num_match.group(1))
                return f"第 {num} 章"
            break

    # If it looks like a filename with extension
    if '.' in name:
        base_name = name.split('.')[0]
        num_match = re.search(r'(\d+)', base_name)
        if num_match:
            num = int(num_match.group(1))
            return f"第 {num} 章"
        return base_name

    # If it's just a number
    if name.isdigit():
        num = int(name)
        return f"第 {num} 章"

    # For id references
    if name.startswith('id'):
        num_match = re.search(r'(\d+)', name)
        if num_match:
            return f"章节 {num_match.group(1)}"

    return name


def extract_cfi_position(cfi: str) -> tuple:
    """
    Extract numeric position from CFI for sorting.

    Args:
        cfi: EPUB CFI string

    Returns:
        tuple: (chapter_num, item_num, offset) for comparison
    """
    if not cfi:
        return (0, 0, 0)

    # Extract chapter number
    ch_match = re.search(r'ch(\d+)', cfi)
    chapter = int(ch_match.group(1)) if ch_match else 0

    # Extract item number (last number before comma or end)
    item_match = re.search(r'/(\d+)(?:,/|$)', cfi)
    item = int(item_match.group(1)) if item_match else 0

    # Extract offset
    offset_match = re.search(r',(\d+):(\d+)', cfi)
    offset = int(offset_match.group(2)) if offset_match else 0

    return (chapter, item, offset)


def get_book_metadata_by_asset_id(asset_id: str) -> dict:
    """
    Get book metadata by asset ID.

    Args:
        asset_id: Apple Books asset ID

    Returns:
        dict: {title, author, path} or None if not found
    """
    annotation_db, library_db = find_databases()

    conn = sqlite3.connect(library_db)
    cursor = conn.execute(
        """
        SELECT ZTITLE, ZAUTHOR, ZPATH
        FROM ZBKLIBRARYASSET
        WHERE ZASSETID = ?
        """,
        (asset_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'title': row[0] or 'Unknown Title',
            'author': row[1] or 'Unknown Author',
            'path': row[2]
        }
    return None


def list_all_books() -> list:
    """
    List all books in Apple Books library.

    Returns:
        list: [{asset_id, title, author, highlight_count}]
    """
    annotation_db, library_db = find_databases()

    conn = sqlite3.connect(annotation_db)
    conn.execute(f"ATTACH DATABASE '{library_db}' AS bklib")

    query = """
    SELECT
        bklib.ZBKLIBRARYASSET.ZASSETID,
        bklib.ZBKLIBRARYASSET.ZTITLE,
        bklib.ZBKLIBRARYASSET.ZAUTHOR,
        COUNT(a.ZANNOTATIONUUID) as highlight_count
    FROM bklib.ZBKLIBRARYASSET
    LEFT JOIN ZAEANNOTATION a
        ON a.ZANNOTATIONASSETID = bklib.ZBKLIBRARYASSET.ZASSETID
        AND a.ZANNOTATIONDELETED = 0
        AND a.ZANNOTATIONTYPE != 1
    GROUP BY bklib.ZBKLIBRARYASSET.ZASSETID
    ORDER BY bklib.ZBKLIBRARYASSET.ZTITLE
    """

    cursor = conn.execute(query)
    books = []

    for row in cursor:
        books.append({
            'asset_id': row[0],
            'title': row[1] or 'Unknown Title',
            'author': row[2] or 'Unknown Author',
            'highlight_count': row[3]
        })

    conn.close()
    return books


def extract_highlights_by_asset_id(asset_id: str) -> tuple:
    """
    Extract all highlights for a specific book by asset ID.

    Args:
        asset_id: Apple Books asset ID

    Returns:
        tuple: (highlights_list, metadata_dict)
            highlights_list: [{text, note, location, chapter, created, modified}]
            metadata_dict: {title, author}
    """
    annotation_db, library_db = find_databases()

    conn = sqlite3.connect(annotation_db)
    conn.execute(f"ATTACH DATABASE '{library_db}' AS bklib")

    query = """
    SELECT
        bklib.ZBKLIBRARYASSET.ZTITLE,
        bklib.ZBKLIBRARYASSET.ZAUTHOR,
        a.ZANNOTATIONSELECTEDTEXT,
        a.ZANNOTATIONNOTE,
        a.ZANNOTATIONTYPE,
        a.ZANNOTATIONLOCATION,
        a.ZANNOTATIONUUID,
        a.ZANNOTATIONCREATIONDATE,
        a.ZANNOTATIONMODIFICATIONDATE
    FROM ZAEANNOTATION a
    LEFT JOIN bklib.ZBKLIBRARYASSET
        ON a.ZANNOTATIONASSETID = bklib.ZBKLIBRARYASSET.ZASSETID
    WHERE a.ZANNOTATIONASSETID = ?
        AND a.ZANNOTATIONDELETED = 0
        AND a.ZANNOTATIONTYPE != 1
    ORDER BY a.ZANNOTATIONCREATIONDATE
    """

    cursor = conn.execute(query, (asset_id,))

    highlights = []
    title = 'Unknown Title'
    author = 'Unknown Author'

    for row in cursor:
        title = row[0] or title
        author = row[1] or author

        selected_text = row[2] or ''
        note = row[3] or ''
        atype = row[4]
        location = row[5]
        uuid = row[6]
        created = convert_coredata_timestamp(row[7])
        modified = convert_coredata_timestamp(row[8])

        # Skip bookmarks (type 1)
        if atype == 1:
            continue

        # Extract chapter from CFI
        section = extract_section_from_cfi(location)
        chapter = format_section_name(section) if section else "未分类"
        position = extract_cfi_position(location)

        highlights.append({
            'text': selected_text,
            'note': note,
            'type': TYPE_MAP.get(atype, 'unknown'),
            'location': location,
            'uuid': uuid,
            'chapter': chapter,
            'position': position,
            'created': created,
            'modified': modified
        })

    conn.close()

    metadata = {
        'title': title,
        'author': author,
        'asset_id': asset_id,
        'highlight_count': len(highlights)
    }

    return highlights, metadata


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract Apple Books highlights')
    parser.add_argument('--asset-id', help='Extract highlights for specific book')
    parser.add_argument('--list-books', action='store_true', help='List all books')

    args = parser.parse_args()

    if args.list_books:
        books = list_all_books()
        print(f"\n找到 {len(books)} 本书:\n")
        for book in books:
            print(f"  {book['asset_id']}: {book['title']} ({book['highlight_count']} 条高亮)")
        return

    if args.asset_id:
        highlights, metadata = extract_highlights_by_asset_id(args.asset_id)
        print(f"\n书名: {metadata['title']}")
        print(f"作者: {metadata['author']}")
        print(f"高亮数: {metadata['highlight_count']}\n")

        for i, h in enumerate(highlights, 1):
            print(f"高亮 {i}:")
            print(f"  章节: {h['chapter']}")
            print(f"  文本: {h['text'][:50]}...")
            if h['note']:
                print(f"  批注: {h['note']}")
            print()


if __name__ == '__main__':
    main()
