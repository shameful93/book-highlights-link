# tests/test_text_matcher.py
import pytest
from text_matcher import generate_block_id, TextMatcher


class TestGenerateBlockId:
    """测试 block ID 生成"""

    def test_generates_consistent_id(self):
        """相同文本应生成相同 ID"""
        text = "这是第一段内容，用于测试 block ID 生成。"
        id1 = generate_block_id(text)
        id2 = generate_block_id(text)
        assert id1 == id2

    def test_different_text_different_id(self):
        """不同文本应生成不同 ID"""
        text1 = "这是第一段内容。"
        text2 = "这是第二段内容。"
        id1 = generate_block_id(text1)
        id2 = generate_block_id(text2)
        assert id1 != id2

    def test_id_format(self):
        """ID 格式应为 ^para-xxxxxx（6位hex）"""
        text = "测试文本"
        block_id = generate_block_id(text)
        assert block_id.startswith("^para-")
        assert len(block_id) == 12  # ^para- + 6 hex chars

    def test_uses_first_50_chars(self):
        """使用前 50 字符生成 ID"""
        long_text = "A" * 100
        short_text = "A" * 50
        id1 = generate_block_id(long_text)
        id2 = generate_block_id(short_text)
        assert id1 == id2


class TestTextMatcher:
    """测试文本匹配器"""

    def setup_method(self):
        self.matcher = TextMatcher(threshold=0.8)
        self.matcher.add_paragraph("这是第一段内容，用于测试。", "^para-abc123", "ch01")
        self.matcher.add_paragraph("这是第二段内容，完全不同。", "^para-def456", "ch01")
        self.matcher.add_paragraph("这是第三段内容，在第二章。", "^para-ghi789", "ch02")

    def test_exact_match(self):
        """精确匹配测试"""
        result = self.matcher.find_match("这是第一段内容，用于测试。")
        assert result is not None
        assert result['block_id'] == "^para-abc123"
        assert result['match_type'] == 'exact'

    def test_partial_match(self):
        """部分匹配测试（高亮文本是段落的一部分）"""
        result = self.matcher.find_match("第一段内容")
        assert result is not None
        assert result['block_id'] == "^para-abc123"

    def test_no_match(self):
        """无匹配测试"""
        result = self.matcher.find_match("完全不存在的内容xyz123")
        assert result is None

    def test_chapter_hint(self):
        """章节提示测试"""
        result = self.matcher.find_match("第三段内容", chapter_hint="ch02")
        assert result is not None
        assert result['chapter'] == "ch02"

    def test_fuzzy_match(self):
        """模糊匹配测试"""
        # 稍有不同的文本应该仍能匹配
        result = self.matcher.find_match("这是第一段内容，用于测试！")
        assert result is not None
