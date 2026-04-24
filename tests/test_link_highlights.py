# tests/test_link_highlights.py
import pytest
import tempfile
from pathlib import Path
from highlight_linker import (
    parse_book_paragraphs,
    link_highlights_to_paragraphs,
    organize_highlights_by_chapter,
    format_highlights_document,
    link_and_format_highlights
)


class TestParseBookParagraphs:
    """测试书籍段落解析"""

    def test_parse_basic(self):
        """基本解析测试"""
        content = """# 测试书

## 第 1 章

这是第一段内容。 ^para-abc123

这是第二段内容。 ^para-def456
"""
        paragraphs = parse_book_paragraphs(content)
        assert len(paragraphs) == 2
        assert paragraphs[0]['block_id'] == '^para-abc123'
        assert paragraphs[0]['chapter'] == '第 1 章'

    def test_parse_with_chapter(self):
        """测试章节识别"""
        content = """## 第 1 章

内容一。 ^para-001

## 第 2 章

内容二。 ^para-002
"""
        paragraphs = parse_book_paragraphs(content)
        assert len(paragraphs) == 2
        assert paragraphs[0]['chapter'] == '第 1 章'
        assert paragraphs[1]['chapter'] == '第 2 章'


class TestLinkHighlights:
    """测试链接生成"""

    def test_link_highlights_to_paragraphs(self):
        """测试高亮匹配"""
        paragraphs = [
            {'text': '这是第一段内容。', 'block_id': '^para-abc123', 'chapter': '第 1 章'},
            {'text': '这是第二段内容。', 'block_id': '^para-def456', 'chapter': '第 1 章'}
        ]
        # Use full text for better matching
        highlights = [
            {'text': '这是第一段内容。', 'chapter': '第 1 章', 'location': 'test'},
            {'text': '这是第二段内容。', 'chapter': '第 1 章', 'location': 'test2'}
        ]

        linked, stats = link_highlights_to_paragraphs(highlights, paragraphs)

        assert stats['matched'] == 2
        assert linked[0]['block_id'] == '^para-abc123'
        assert linked[1]['block_id'] == '^para-def456'

    def test_link_highlights_partial_match(self):
        """测试部分匹配"""
        paragraphs = [
            {'text': '这是第一段内容。', 'block_id': '^para-abc123', 'chapter': '第 1 章'}
        ]
        # Partial text should still match (it's a substring)
        highlights = [
            {'text': '第一段内容', 'chapter': '第 1 章', 'location': 'test'}
        ]

        linked, stats = link_highlights_to_paragraphs(highlights, paragraphs)

        assert stats['matched'] == 1
        assert linked[0]['block_id'] == '^para-abc123'

    def test_organize_by_chapter(self):
        """测试按章节组织"""
        linked = [
            {'text': '高亮1', 'chapter': '第 1 章', 'block_id': '^para-001', 'position': (1, 0, 0)},
            {'text': '高亮2', 'chapter': '第 1 章', 'block_id': '^para-002', 'note': '笔记', 'position': (1, 1, 0)},
            {'text': '高亮3', 'chapter': '第 2 章', 'block_id': '^para-003', 'position': (2, 0, 0)}
        ]

        chapters = organize_highlights_by_chapter(linked)

        assert '第 1 章' in chapters
        assert '第 2 章' in chapters
        assert len(chapters['第 1 章']['highlights']) == 1
        assert len(chapters['第 1 章']['notes']) == 1

    def test_format_highlights_document(self):
        """测试格式化输出"""
        linked = [
            {'text': '高亮文本内容。', 'chapter': '第 1 章', 'block_id': '^para-abc123', 'location': 'test', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        assert 'aliasest:' in formatted
        assert 'author: 作者' in formatted
        assert '# 第 1 章' in formatted
        assert '[[测试书#^para-abc123|原文位置↗]]' in formatted

    def test_notes_separated(self):
        """测试批注紧跟高亮"""
        linked = [
            {'text': '纯高亮', 'chapter': '第 1 章', 'block_id': '^para-001', 'position': (1, 0, 0)},
            {'text': '带批注的高亮', 'chapter': '第 1 章', 'block_id': '^para-002', 'note': '我的笔记', 'position': (1, 1, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        # Should have both highlights and note inline
        assert '纯高亮' in formatted
        assert '带批注的高亮' in formatted
        assert '我的笔记' in formatted
        assert '**批注：**' in formatted

    def test_full_pipeline(self):
        """测试完整流程"""
        paragraphs = [
            {'text': '这是第一段内容。', 'block_id': '^para-abc123', 'chapter': '第 1 章'}
        ]
        highlights = [
            {'text': '这是第一段内容。', 'chapter': '第 1 章', 'location': 'test', 'position': (1, 0, 0)}
        ]

        formatted, stats = link_and_format_highlights(
            highlights=highlights,
            paragraphs=paragraphs,
            book_title='测试书',
            book_author='作者',
            book_filename='测试书'
        )

        assert stats['matched'] == 1
        assert '[[测试书#^para-abc123|原文位置↗]]' in formatted


class TestNewFormat:
    """测试新格式输出"""

    def test_frontmatter_has_aliasest(self):
        """测试 frontmatter 包含 aliasest 字段"""
        linked = [
            {'text': '高亮内容', 'chapter': '第一章', 'block_id': '^para-001', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书',
            aliasest='Test Book English Title'
        )

        assert 'aliasest: Test Book English Title' in formatted

    def test_chapter_heading_level_one(self):
        """测试章节标题使用一级标题"""
        linked = [
            {'text': '高亮内容', 'chapter': '第一章 引言', 'block_id': '^para-001', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        assert '# 第一章 引言' in formatted
        assert '## 第一章 引言' not in formatted

    def test_link_text_format(self):
        """测试链接文本格式"""
        linked = [
            {'text': '高亮内容', 'chapter': '第一章', 'block_id': '^para-001', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        assert '[[测试书#^para-001|原文位置↗]]' in formatted
        assert '↗原文' not in formatted

    def test_note_follows_highlight(self):
        """测试批注紧跟高亮"""
        linked = [
            {'text': '高亮内容', 'chapter': '第一章', 'block_id': '^para-001', 'note': '我的笔记', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        assert '**批注：**' in formatted
        assert '我的笔记' in formatted
        assert '### 高亮' not in formatted
        assert '### 批注' not in formatted

    def test_chapter_separator(self):
        """测试章节分隔线"""
        linked = [
            {'text': '高亮1', 'chapter': '第一章', 'block_id': '^para-001', 'position': (1, 0, 0)},
            {'text': '高亮2', 'chapter': '第二章', 'block_id': '^para-002', 'position': (2, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        # Should have --- between chapters
        lines = formatted.split('\n')
        # Find chapter headings and check separator before them (except first)
        chapter_indices = [i for i, l in enumerate(lines) if l.startswith('# 第')]
        assert len(chapter_indices) == 2
        # Second chapter should have separator before it
        if chapter_indices[1] > 0:
            # Check there's a --- somewhere before second chapter
            before_second = lines[:chapter_indices[1]]
            assert '---' in before_second

    def test_no_extra_frontmatter_fields(self):
        """测试不包含多余的 frontmatter 字段"""
        linked = [
            {'text': '高亮内容', 'chapter': '第一章', 'block_id': '^para-001', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        # Should not have old fields
        assert 'source:' not in formatted
        assert 'title:' not in formatted.split('---')[1]  # Not in frontmatter

    def test_single_blank_line_without_note(self):
        """测试无批注时只有一个空行"""
        linked = [
            {'text': '高亮内容', 'chapter': '第一章', 'block_id': '^para-001', 'position': (1, 0, 0)}
        ]

        formatted = format_highlights_document(
            book_title='测试书',
            book_author='作者',
            linked_highlights=linked,
            book_filename='测试书'
        )

        lines = formatted.split('\n')
        # Find the line with link
        link_idx = next(i for i, l in enumerate(lines) if '原文位置↗' in l)
        # Next non-empty line should be --- or end
        next_lines = lines[link_idx+1:]
        non_empty = [l for l in next_lines if l.strip()]
        # First non-empty should be --- or end
        assert len(non_empty) == 0 or non_empty[0] == '---'
