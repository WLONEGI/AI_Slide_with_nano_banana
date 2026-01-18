"""
PPTX Extractor のユニットテスト

テスト対象:
- extract_color_scheme
- extract_font_scheme
- extract_layout_info
- _infer_layout_type
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import io


class TestInferLayoutType:
    """レイアウトタイプ推論のテスト"""
    
    def test_infer_title_slide(self):
        """タイトルスライドを推論できることを確認"""
        from src.utils.pptx_extractor import _infer_layout_type
        
        # 英語パターン
        assert _infer_layout_type("Title Slide") == "title_slide"
        # 日本語パターン
        assert _infer_layout_type("タイトル スライド") == "title_slide"
    
    def test_infer_section_header(self):
        """セクションヘッダーを推論できることを確認"""
        from src.utils.pptx_extractor import _infer_layout_type
        
        assert _infer_layout_type("Section Header") == "section_header"
        assert _infer_layout_type("セクション見出し") == "section_header"
    
    def test_infer_comparison(self):
        """比較レイアウトを推論できることを確認"""
        from src.utils.pptx_extractor import _infer_layout_type
        
        assert _infer_layout_type("Comparison") == "comparison"
        assert _infer_layout_type("比較") == "comparison"
    
    def test_infer_title_and_content(self):
        """タイトル＆コンテンツを推論できることを確認"""
        from src.utils.pptx_extractor import _infer_layout_type
        
        assert _infer_layout_type("Title and Content") == "title_and_content"
        assert _infer_layout_type("タイトルとコンテンツ") == "title_and_content"
    
    def test_infer_blank(self):
        """空白レイアウトを推論できることを確認"""
        from src.utils.pptx_extractor import _infer_layout_type
        
        assert _infer_layout_type("Blank") == "blank"
        assert _infer_layout_type("白紙") == "blank"
    
    def test_infer_unknown_defaults_to_other(self):
        """不明なレイアウトはotherになることを確認"""
        from src.utils.pptx_extractor import _infer_layout_type
        
        assert _infer_layout_type("Custom Layout XYZ") == "other"


class TestExtractColorScheme:
    """カラースキーム抽出のテスト"""
    
    def test_extract_color_scheme_from_xml(self):
        """XMLからカラースキームを抽出できることを確認"""
        from src.utils.pptx_extractor import extract_color_scheme
        
        theme_xml = b'''<?xml version="1.0"?>
        <a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <a:themeElements>
                <a:clrScheme name="Test Colors">
                    <a:dk1><a:srgbClr val="000000"/></a:dk1>
                    <a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
                    <a:dk2><a:srgbClr val="1F1F1F"/></a:dk2>
                    <a:lt2><a:srgbClr val="F0F0F0"/></a:lt2>
                    <a:accent1><a:srgbClr val="FF5733"/></a:accent1>
                    <a:accent2><a:srgbClr val="33FF57"/></a:accent2>
                    <a:accent3><a:srgbClr val="3357FF"/></a:accent3>
                    <a:accent4><a:srgbClr val="FFFF33"/></a:accent4>
                    <a:accent5><a:srgbClr val="FF33FF"/></a:accent5>
                    <a:accent6><a:srgbClr val="33FFFF"/></a:accent6>
                    <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
                    <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
                </a:clrScheme>
            </a:themeElements>
        </a:theme>'''
        
        color_scheme = extract_color_scheme(theme_xml)
        
        assert color_scheme.dk1 == "#000000"
        assert color_scheme.lt1 == "#FFFFFF"
        assert color_scheme.accent1 == "#FF5733"
        assert color_scheme.accent2 == "#33FF57"


class TestExtractFontScheme:
    """フォントスキーム抽出のテスト"""
    
    def test_extract_font_scheme_from_xml(self):
        """XMLからフォントスキームを抽出できることを確認"""
        from src.utils.pptx_extractor import extract_font_scheme
        
        theme_xml = b'''<?xml version="1.0"?>
        <a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <a:themeElements>
                <a:fontScheme name="Test Fonts">
                    <a:majorFont>
                        <a:latin typeface="Meiryo"/>
                    </a:majorFont>
                    <a:minorFont>
                        <a:latin typeface="Yu Gothic"/>
                    </a:minorFont>
                </a:fontScheme>
            </a:themeElements>
        </a:theme>'''
        
        font_scheme = extract_font_scheme(theme_xml)
        
        assert font_scheme.major_latin == "Meiryo"
        assert font_scheme.minor_latin == "Yu Gothic"


class TestExtractLayoutInfo:
    """レイアウト情報抽出のテスト"""
    
    def test_extract_layout_info_basic(self):
        """基本的なレイアウト情報抽出をテスト"""
        from src.utils.pptx_extractor import extract_layout_info
        
        # モックレイアウト
        mock_layout = Mock()
        mock_layout.name = "Title and Content"
        mock_layout.placeholders = []
        
        # スライドサイズ (9144000 x 6858000 EMU = 10x7.5 inches)
        slide_width = 9144000
        slide_height = 6858000
        
        result = extract_layout_info(mock_layout, slide_width, slide_height)
        
        assert result.name == "Title and Content"
        assert result.layout_type == "title_and_content"
        assert len(result.placeholders) == 0
    
    def test_extract_layout_info_with_placeholders(self):
        """プレースホルダー付きレイアウト情報抽出をテスト"""
        from src.utils.pptx_extractor import extract_layout_info
        
        # モックプレースホルダー
        mock_ph = Mock()
        mock_ph.left = 914400  # 1 inch
        mock_ph.top = 914400
        mock_ph.width = 7315200  # 8 inches
        mock_ph.height = 914400
        mock_ph.placeholder_format = Mock()
        mock_ph.placeholder_format.type = 1  # Title
        
        mock_layout = Mock()
        mock_layout.name = "Title Slide"
        mock_layout.placeholders = [mock_ph]
        
        slide_width = 9144000
        slide_height = 6858000
        
        result = extract_layout_info(mock_layout, slide_width, slide_height)
        
        assert result.name == "Title Slide"
        assert result.layout_type == "title_slide"
        assert len(result.placeholders) == 1
        assert result.placeholders[0].type == "title"
