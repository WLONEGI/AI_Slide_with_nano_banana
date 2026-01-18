"""
Visualizer Node のテンプレート機能統合テスト

テスト対象:
- process_single_slide の design_context 対応
- visualizer_node の Strategy T 実装
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio


class TestProcessSingleSlideWithDesignContext:
    """process_single_slide のdesign_context対応テスト"""
    
    @pytest.mark.asyncio
    async def test_uses_layout_specific_template(self):
        """レイアウト固有のテンプレート画像を使用することを確認"""
        from src.graph.nodes import process_single_slide
        from src.schemas.outputs import ImagePrompt, ThoughtSignature
        from src.schemas.design import DesignContext, ColorScheme, FontScheme
        
        # モック DesignContext
        template_bytes = b"TEMPLATE_PNG_DATA"
        mock_design_context = Mock(spec=DesignContext)
        mock_design_context.get_template_image_for_layout.return_value = template_bytes
        mock_design_context.layout_image_bytes = {"title_slide": template_bytes}
        
        # テスト用 ImagePrompt（layout_type あり）
        prompt_item = ImagePrompt(
            slide_number=1,
            image_generation_prompt="Test prompt for title slide",
            rationale="Test rationale",
            layout_type="title_slide",
        )
        
        # Mock generate_image and upload_to_gcs
        with patch("src.graph.nodes.generate_image") as mock_gen, \
             patch("src.graph.nodes.upload_to_gcs") as mock_upload:
            
            mock_gen.return_value = (b"GENERATED_IMAGE", None)  # (image_bytes, token)
            mock_upload.return_value = "https://storage.example.com/image.png"
            
            result = await process_single_slide(
                prompt_item,
                previous_generations=None,
                override_reference_bytes=None,
                design_context=mock_design_context,
            )
            
            # DesignContext.get_template_image_for_layout が呼ばれたことを確認
            mock_design_context.get_template_image_for_layout.assert_called_once_with("title_slide")
            
            # generate_image が reference_image 付きで呼ばれたことを確認
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            assert call_args.kwargs.get("reference_image") == template_bytes or \
                   (len(call_args.args) >= 3 and call_args.args[2] == template_bytes)
            
            # 結果が正しいことを確認
            assert result.generated_image_url == "https://storage.example.com/image.png"
            assert result.thought_signature is not None
    
    @pytest.mark.asyncio
    async def test_fallback_to_default_layout(self):
        """レイアウト画像がない場合のフォールバックを確認"""
        from src.graph.nodes import process_single_slide
        from src.schemas.outputs import ImagePrompt
        from src.schemas.design import DesignContext
        
        # DesignContext があるがレイアウト画像が見つからない場合
        mock_design_context = Mock(spec=DesignContext)
        mock_design_context.get_template_image_for_layout.return_value = None
        mock_design_context.layout_image_bytes = {}
        
        prompt_item = ImagePrompt(
            slide_number=1,
            image_generation_prompt="Test prompt",
            rationale="Test rationale",
            layout_type="other",  # 存在しないマッピングでフォールバックをテスト
        )
        
        with patch("src.graph.nodes.generate_image") as mock_gen, \
             patch("src.graph.nodes.upload_to_gcs") as mock_upload:
            
            mock_gen.return_value = (b"GENERATED_IMAGE", None)  # (image_bytes, token)
            mock_upload.return_value = "https://storage.example.com/image.png"
            
            result = await process_single_slide(
                prompt_item,
                design_context=mock_design_context,
            )
            
            # generate_image が reference_image=None で呼ばれたことを確認
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            # reference_image が None または渡されていないことを確認
            ref_image = call_args.kwargs.get("reference_image")
            assert ref_image is None
    
    @pytest.mark.asyncio
    async def test_without_design_context_fallback_to_anchor(self):
        """DesignContextなしでは従来のアンカー戦略が動作することを確認"""
        from src.graph.nodes import process_single_slide
        from src.schemas.outputs import ImagePrompt
        
        anchor_bytes = b"ANCHOR_IMAGE_DATA"
        
        prompt_item = ImagePrompt(
            slide_number=2,
            image_generation_prompt="Content slide prompt",
            rationale="Content rationale",
        )
        
        with patch("src.graph.nodes.generate_image") as mock_gen, \
             patch("src.graph.nodes.upload_to_gcs") as mock_upload:
            
            mock_gen.return_value = (b"GENERATED_IMAGE", None)  # (image_bytes, token)
            mock_upload.return_value = "https://storage.example.com/image.png"
            
            result = await process_single_slide(
                prompt_item,
                previous_generations=None,
                override_reference_bytes=anchor_bytes,  # 従来のアンカー
                design_context=None,  # DesignContextなし
            )
            
            # アンカー画像が使われたことを確認
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            assert call_args.kwargs.get("reference_image") == anchor_bytes or \
                   (len(call_args.args) >= 3 and call_args.args[2] == anchor_bytes)


class TestVisualizerNodeStrategyT:
    """visualizer_node の Strategy T テスト"""
    
    @pytest.mark.asyncio
    async def test_strategy_t_when_design_context_available(self):
        """DesignContextがある場合にStrategy Tが選択されることを確認"""
        from src.graph.nodes import visualizer_node
        from src.schemas.design import DesignContext, ColorScheme, FontScheme, SlideLayoutInfo
        from src.schemas.outputs import VisualizerOutput, ImagePrompt, GenerationConfig
        
        # モック State
        mock_state = {
            "plan": [{"id": 1, "instruction": "Generate slides"}],
            "current_step_index": 0,
            "artifacts": {},
            "messages": [],
            "TEAM_MEMBERS": ["visualizer"],
            "design_context": Mock(spec=DesignContext),
        }
        
        # DesignContext のモック設定
        mock_state["design_context"].layout_image_bytes = {"title_slide": b"PNG", "title_and_content": b"PNG"}
        mock_state["design_context"].layouts = [
            Mock(layout_type="title_slide"),
            Mock(layout_type="title_and_content"),
        ]
        mock_state["design_context"].color_scheme = Mock(accent1="#FF0000", accent2="#00FF00", dk1="#000", lt1="#FFF")
        mock_state["design_context"].font_scheme = Mock(major_latin="Arial")
        mock_state["design_context"].get_template_image_for_layout.return_value = b"TEMPLATE_PNG"
        
        # LLM 出力のモック
        mock_visualizer_output = VisualizerOutput(
            prompts=[
                ImagePrompt(
                    slide_number=1,
                    image_generation_prompt="Title slide prompt",
                    rationale="Title",
                    layout_type="title_slide",
                ),
            ],
            generation_config=GenerationConfig(thinking_level="high", media_resolution="high"),
        )
        
        with patch("src.graph.nodes.apply_prompt_template") as mock_template, \
             patch("src.graph.nodes.get_llm_by_type") as mock_llm, \
             patch("src.graph.nodes.process_single_slide") as mock_process:
            
            mock_template.return_value = []
            mock_structured_llm = Mock()
            mock_structured_llm.invoke.return_value = mock_visualizer_output
            mock_llm.return_value.with_structured_output.return_value = mock_structured_llm
            
            mock_process.return_value = ImagePrompt(
                slide_number=1,
                image_generation_prompt="Title slide prompt",
                rationale="Title",
                layout_type="title_slide",
                generated_image_url="https://storage.example.com/image.png",
            )
            
            result = await visualizer_node(mock_state)
            
            # process_single_slide が design_context 付きで呼ばれたことを確認
            mock_process.assert_called()
            call_kwargs = mock_process.call_args.kwargs
            assert "design_context" in call_kwargs
            assert call_kwargs["design_context"] is not None


class TestAnchorStrategyFallback:
    """Strategy T が使えない場合のフォールバックテスト"""
    
    @pytest.mark.asyncio
    async def test_strategy_a_when_no_design_context(self):
        """DesignContextがない場合にStrategy Aが動作することを確認"""
        from src.graph.nodes import visualizer_node
        from src.schemas.outputs import VisualizerOutput, ImagePrompt, GenerationConfig
        
        # DesignContextなしのState
        mock_state = {
            "plan": [{"id": 1, "instruction": "Generate slides"}],
            "current_step_index": 0,
            "artifacts": {},
            "messages": [],
            "TEAM_MEMBERS": ["visualizer"],
            "design_context": None,  # DesignContextなし
        }
        
        # LLM 出力（anchor_image_prompt あり = Strategy A）
        mock_visualizer_output = VisualizerOutput(
            anchor_image_prompt="Style anchor: abstract blue background",
            prompts=[
                ImagePrompt(
                    slide_number=1,
                    image_generation_prompt="Content slide prompt",
                    rationale="Content",
                ),
            ],
            generation_config=GenerationConfig(thinking_level="high", media_resolution="high"),
        )
        
        with patch("src.graph.nodes.apply_prompt_template") as mock_template, \
             patch("src.graph.nodes.get_llm_by_type") as mock_llm, \
             patch("src.graph.nodes.process_single_slide") as mock_process, \
             patch("src.graph.nodes.download_blob_as_bytes") as mock_download:
            
            mock_template.return_value = []
            mock_structured_llm = Mock()
            mock_structured_llm.invoke.return_value = mock_visualizer_output
            mock_llm.return_value.with_structured_output.return_value = mock_structured_llm
            
            # アンカー生成
            anchor_result = ImagePrompt(
                slide_number=0,
                image_generation_prompt="Style anchor",
                rationale="Anchor",
                generated_image_url="https://storage.example.com/anchor.png",
            )
            
            content_result = ImagePrompt(
                slide_number=1,
                image_generation_prompt="Content slide prompt",
                rationale="Content",
                generated_image_url="https://storage.example.com/slide1.png",
            )
            
            mock_process.side_effect = [anchor_result, content_result]
            mock_download.return_value = b"ANCHOR_BYTES"
            
            result = await visualizer_node(mock_state)
            
            # process_single_slide がアンカー生成用に呼ばれたことを確認
            assert mock_process.call_count >= 1
