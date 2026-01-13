
import pytest
from unittest.mock import MagicMock, patch
from src.graph.nodes import visualizer_node
from langchain_core.messages import HumanMessage
from src.graph.graph_types import State
from src.schemas.outputs import VisualizerOutput, ImagePrompt, GenerationConfig

@pytest.mark.asyncio
async def test_ut05_visualizer_prompt_generation():
    """UT-05: Visualizerが適切なプロンプトを出力し、画像生成フローを実行するか検証 (Mock)"""
    
    # Planのある状態
    state: State = {
        "messages": [],
        "plan": [
            {"id": 2, "role": "visualizer", "instruction": "スライド1の画像生成", "description": "ビジュアル化"}
        ],
        "artifacts": {},
        "current_step_index": 0
    }
    
    # Mock LLM Output
    mock_output = VisualizerOutput(
        prompts=[
            ImagePrompt(
                slide_number=1,
                image_generation_prompt="[Role] Designer [Context] Title Slide [Logic] Abstract [Style] Minimal [Constraints] No Text",
                rationale="Title needs to be clean."
            )
        ],
        generation_config=GenerationConfig()
    )
    
    mock_llm = MagicMock()
    structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = structured_llm
    structured_llm.invoke.return_value = mock_output
    
    # Patch targets
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm), \
         patch("src.utils.image_generation.generate_image", return_value=b"fake_image_bytes") as mock_gen, \
         patch("src.utils.storage.upload_to_gcs", return_value="https://gcs-bucket/fake.png") as mock_upload:
        
        # ノード実行
        result = visualizer_node(state)
        
        # 検証
        assert result.goto == "reviewer"
        
        # 画像生成関数が呼ばれたか
        mock_gen.assert_called_once()
        args, _ = mock_gen.call_args
        assert "[Role] Designer" in args[0]
        
        # アップロードが呼ばれたか
        mock_upload.assert_called_once_with(b"fake_image_bytes", content_type="image/png")
        
        # ArtifactにURLが含まれているか確認 (VisualizerOutputがJSON化されているはず)
        import json
        saved_json = result.update["artifacts"]["step_2_visual"]
        saved_data = json.loads(saved_json)
        
        assert saved_data["prompts"][0]["generated_image_url"] == "https://gcs-bucket/fake.png"
