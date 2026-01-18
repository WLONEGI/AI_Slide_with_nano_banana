"""
構造化プロンプト v2 (Markdown Slide Format) のテスト

テスト対象:
- compile_structured_prompt() の新しいMarkdown形式出力
- StructuredImagePrompt の新スキーマ
"""

import pytest
from src.schemas import StructuredImagePrompt
from src.graph.nodes import compile_structured_prompt


class TestCompileStructuredPromptV2:
    """compile_structured_prompt() v2 のテスト"""
    
    def test_basic_title_slide(self):
        """タイトルスライドの基本的な変換テスト"""
        structured = StructuredImagePrompt(
            slide_type="Title Slide",
            main_title="The Evolution of Japan's Economy",
            sub_title="From Post-War Recovery to Future Innovation",
            visual_style="Minimalist and professional design with navy blue and red accents."
        )
        
        result = compile_structured_prompt(structured, slide_number=1)
        
        # Slide Header
        assert "# Slide1: Title Slide" in result
        
        # Main Title
        assert "## The Evolution of Japan's Economy" in result
        
        # Sub Title
        assert "### From Post-War Recovery to Future Innovation" in result
        
        # Visual Style
        assert "Visual style: Minimalist and professional design" in result
    
    def test_content_slide_with_contents(self):
        """本文コンテンツ付きスライドのテスト"""
        structured = StructuredImagePrompt(
            slide_type="Content",
            main_title="The Economic Miracle",
            sub_title="Rapid Industrialization (1960s-1980s)",
            contents="Japan's rapid economic growth established it as the world's second-largest economy.",
            visual_style="Clean layout with flat-design icons."
        )
        
        result = compile_structured_prompt(structured, slide_number=2)
        
        # Slide Header with correct number
        assert "# Slide2: Content" in result
        
        # Contents should be included
        assert "Japan's rapid economic growth" in result
        
        # Visual style at the end
        assert result.strip().endswith("Visual style: Clean layout with flat-design icons.")
    
    def test_slide_without_subtitle(self):
        """サブタイトルなしのスライドテスト"""
        structured = StructuredImagePrompt(
            slide_type="Data Visualization",
            main_title="経済成長の推移",
            visual_style="Data-focused design with bar charts."
        )
        
        result = compile_structured_prompt(structured, slide_number=3)
        
        # Main title should be present
        assert "## 経済成長の推移" in result
        
        # No ### should appear (no subtitle)
        assert "### " not in result
    
    def test_slide_with_japanese_content(self):
        """日本語コンテンツのテスト"""
        structured = StructuredImagePrompt(
            slide_type="Content",
            main_title="日本経済の発展",
            sub_title="戦後復興から現代へ",
            contents="高度経済成長期を経て、日本は世界第2位の経済大国となった。",
            visual_style="Professional Japanese business style with blue gradient."
        )
        
        result = compile_structured_prompt(structured, slide_number=1)
        
        # Japanese content should be preserved
        assert "日本経済の発展" in result
        assert "戦後復興から現代へ" in result
        assert "高度経済成長期" in result
    
    def test_slide_with_markdown_table(self):
        """Markdownテーブル付きコンテンツのテスト"""
        table_content = """| 年代 | GDP成長率 |
|------|-----------|
| 1960年代 | 10-13% |
| 1980年代 | 4-6% |"""
        
        structured = StructuredImagePrompt(
            slide_type="Data Visualization",
            main_title="Growth Data",
            contents=table_content,
            visual_style="Clean data visualization."
        )
        
        result = compile_structured_prompt(structured, slide_number=4)
        
        # Table should be preserved
        assert "| 年代 | GDP成長率 |" in result
        assert "| 1960年代 | 10-13% |" in result
    
    def test_output_format_structure(self):
        """出力形式の構造テスト"""
        structured = StructuredImagePrompt(
            slide_type="Title Slide",
            main_title="Test Title",
            sub_title="Test Subtitle",
            contents="Test contents.",
            visual_style="Test visual style."
        )
        
        result = compile_structured_prompt(structured, slide_number=1)
        
        lines = result.split("\n")
        
        # First line should be # Slide...
        assert lines[0].startswith("# Slide")
        
        # Second line should be ## Title
        assert lines[1].startswith("## ")
        
        # Third line should be ### Subtitle
        assert lines[2].startswith("### ")
        
        # Last line should be Visual style
        assert lines[-1].startswith("Visual style:")


class TestStructuredImagePromptSchemaV2:
    """StructuredImagePrompt v2 スキーマのテスト"""
    
    def test_minimal_valid_prompt(self):
        """最小限の有効なプロンプトをテスト"""
        prompt = StructuredImagePrompt(
            main_title="Test Title",
            visual_style="Test style."
        )
        
        assert prompt.slide_type == "Content"  # デフォルト値
        assert prompt.sub_title is None
        assert prompt.contents is None
    
    def test_full_prompt(self):
        """全フィールドを含むプロンプトをテスト"""
        prompt = StructuredImagePrompt(
            slide_type="Title Slide",
            main_title="Full Test",
            sub_title="All Fields",
            contents="This is the content.",
            visual_style="Complete visual style description."
        )
        
        assert prompt.slide_type == "Title Slide"
        assert prompt.main_title == "Full Test"
        assert prompt.sub_title == "All Fields"
        assert prompt.contents == "This is the content."
        assert "Complete visual style" in prompt.visual_style
