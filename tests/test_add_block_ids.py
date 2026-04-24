# tests/test_add_block_ids.py
import pytest
import tempfile
import os
from pathlib import Path
from block_id_adder import (
    add_block_ids_to_file,
    add_block_ids_to_content,
    parse_markdown_paragraphs
)


class TestAddBlockIds:
    """测试 block ID 添加"""

    def test_parse_paragraphs(self):
        """测试段落解析"""
        content = """# 第一章

这是第一段。

这是第二段。

## 第一节

这是第三段。
"""
        paragraphs = parse_markdown_paragraphs(content)
        assert len(paragraphs) == 3
        assert "第一段" in paragraphs[0]['text']
        assert "第二段" in paragraphs[1]['text']
        # Each paragraph should have a block_id
        assert paragraphs[0]['block_id'].startswith('^para-')

    def test_add_block_ids_to_content(self):
        """测试内存处理"""
        content = "# 测试\n\n这是第一段。\n\n这是第二段。\n"

        modified, paragraphs = add_block_ids_to_content(content)

        assert "^para-" in modified
        assert len(paragraphs) == 2
        assert paragraphs[0]['block_id'].startswith('^para-')

    def test_add_block_ids_simple(self):
        """测试简单文件添加 block ID"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# 测试\n\n这是第一段。\n\n这是第二段。\n")
            temp_path = f.name

        result, paragraphs = add_block_ids_to_file(temp_path)

        with open(result, 'r') as out:
            content = out.read()

        assert "^para-" in content
        assert content.count("^para-") >= 2
        assert len(paragraphs) >= 2

        # Cleanup
        os.unlink(temp_path)

    def test_preserves_headings(self):
        """标题不应添加 block ID"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# 标题一\n\n## 标题二\n\n内容段落。\n")
            temp_path = f.name

        result, _ = add_block_ids_to_file(temp_path)

        with open(result, 'r') as out:
            content = out.read()

        # 标题行不应有 block ID
        assert "\n# 标题一\n" in content or "# 标题一\n" in content
        # 内容段落应有 block ID (Obsidian requires space before ^)
        assert "内容段落。 ^para-" in content

        # Cleanup
        os.unlink(temp_path)

    def test_idempotent(self):
        """重复运行不应添加重复 ID"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("测试段落。\n")
            temp_path = f.name

        result1, _ = add_block_ids_to_file(temp_path)
        result2, _ = add_block_ids_to_file(result1)

        with open(result2, 'r') as out:
            content = out.read()

        assert content.count("^para-") == 1

        # Cleanup
        os.unlink(temp_path)

    def test_paragraph_has_block_id(self):
        """段落数据包含 block_id"""
        content = "测试段落。\n"
        paragraphs = parse_markdown_paragraphs(content)

        assert len(paragraphs) == 1
        assert 'block_id' in paragraphs[0]
        assert paragraphs[0]['block_id'].startswith('^para-')
