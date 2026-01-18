"""
PPTXテンプレート機能のユニットテスト

テスト対象:
- DesignContext スキーマ
- pptx_extractor ユーティリティ
- template_analyzer 統合モジュール
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import io

# テスト対象モジュール
from src.schemas.design import (
    DesignContext,
    ColorScheme,
    FontScheme,
    SlideLayoutInfo,
    BackgroundInfo,
    LayoutType,
)


def create_test_design_context(**kwargs):
    """テスト用のDesignContextを作成するヘルパー関数"""
    defaults = {
        "color_scheme": ColorScheme(
            dk1="#000000", lt1="#FFFFFF", dk2="#1F1F1F", lt2="#F0F0F0",
            accent1="#FF0000", accent2="#00FF00", accent3="#0000FF",
            accent4="#FFFF00", accent5="#FF00FF", accent6="#00FFFF",
            hlink="#0000FF", folHlink="#800080"
        ),
        "font_scheme": FontScheme(major_latin="Arial", minor_latin="Calibri"),
        "layouts": [],
        "background": BackgroundInfo(fill_type="solid", solid_color="#FFFFFF"),
        "source_filename": "test_template.pptx",
        "slide_master_count": 1,
        "layout_count": 5,
    }
    defaults.update(kwargs)
    return DesignContext(**defaults)


class TestDesignContextSchema:
    """DesignContextスキーマのテスト"""
    
    def test_create_minimal_design_context(self):
        """最小構成のDesignContextを作成できることを確認"""
        design_context = create_test_design_context()
        
        assert design_context.color_scheme.accent1 == "#FF0000"
        assert design_context.font_scheme.major_latin == "Arial"
        assert len(design_context.layouts) == 0
    
    def test_design_context_with_layouts(self):
        """レイアウト情報を含むDesignContextを作成できることを確認"""
        layouts = [
            SlideLayoutInfo(
                name="Title Slide",
                layout_type="title_slide",
                placeholders=[],
            ),
            SlideLayoutInfo(
                name="Title and Content",
                layout_type="title_and_content",
                placeholders=[],
            ),
        ]
        
        design_context = create_test_design_context(layouts=layouts, layout_count=2)
        
        assert len(design_context.layouts) == 2
        assert design_context.layouts[0].layout_type == "title_slide"
        assert design_context.layouts[1].layout_type == "title_and_content"
    
    def test_get_template_image_for_layout_direct_match(self):
        """直接マッチするレイアウト画像を取得できることを確認"""
        # テスト用画像バイト
        title_image = b"PNG_TITLE_SLIDE"
        content_image = b"PNG_CONTENT_SLIDE"
        
        design_context = create_test_design_context(
            layout_image_bytes={
                "title_slide": title_image,
                "title_and_content": content_image,
            }
        )
        
        result = design_context.get_template_image_for_layout("title_slide")
        assert result == title_image
        
        result = design_context.get_template_image_for_layout("title_and_content")
        assert result == content_image
    
    def test_get_template_image_for_layout_fallback(self):
        """フォールバックロジックが機能することを確認"""
        title_image = b"PNG_TITLE_SLIDE"
        
        design_context = create_test_design_context(
            layout_image_bytes={
                "title_slide": title_image,
            }
        )
        
        # section_header は title_slide にフォールバック
        result = design_context.get_template_image_for_layout("section_header")
        assert result == title_image
    
    def test_get_template_image_for_layout_default_fallback(self):
        """デフォルト画像へのフォールバックが機能することを確認"""
        default_image = b"PNG_DEFAULT"
        
        design_context = create_test_design_context(
            layout_image_bytes={},
            default_template_image_bytes=default_image,
        )
        
        # 存在しないレイアウトはデフォルトにフォールバック
        result = design_context.get_template_image_for_layout("unknown_layout")
        assert result == default_image
    
    def test_get_template_image_for_layout_none_when_empty(self):
        """画像がない場合にNoneを返すことを確認"""
        design_context = create_test_design_context(
            layout_image_bytes={},
        )
        
        result = design_context.get_template_image_for_layout("title_slide")
        assert result is None
    
    def test_design_context_serialization(self):
        """DesignContextがJSON化可能であることを確認（bytesフィールドは除外）"""
        design_context = create_test_design_context(
            layout_image_bytes={"title_slide": b"PNG_DATA"},
            default_template_image_bytes=b"DEFAULT_PNG",
        )
        
        # JSON化
        json_data = design_context.model_dump(mode="json")
        
        # bytesフィールドは除外されている
        assert "layout_image_bytes" not in json_data or json_data.get("layout_image_bytes") == {}
        
        # 基本フィールドは存在
        assert "color_scheme" in json_data
        assert "font_scheme" in json_data
        assert "source_filename" in json_data


class TestLayoutTypeLiteral:
    """LayoutType Literalのテスト"""
    
    def test_valid_layout_types(self):
        """有効なレイアウトタイプが定義されていることを確認"""
        valid_types = [
            "title_slide",
            "section_header",
            "two_content",
            "comparison",
            "blank",
            "content_with_caption",
            "picture_with_caption",
            "title_and_content",
            "other",
        ]
        
        # SlideLayoutInfo で有効なタイプが使えることを確認
        for layout_type in valid_types:
            info = SlideLayoutInfo(
                name=f"Test {layout_type}",
                layout_type=layout_type,  # type: ignore
                placeholders=[],
            )
            assert info.layout_type == layout_type
