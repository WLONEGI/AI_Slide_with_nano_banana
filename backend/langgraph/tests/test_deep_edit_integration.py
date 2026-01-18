
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock missing dependency before importing nodes
sys.modules["langchain_google_community"] = MagicMock()

import pytest
from src.graph.nodes import visualizer_node, visualizer_agent
from src.schemas import ImagePrompt, VisualizerOutput, GenerationConfig
from langchain_core.messages import HumanMessage
import json

@pytest.mark.asyncio
async def test_deep_edit_anchor_reuse():
    # 1. Setup Mock State with Previous Artifacts (Simulating Edit Mode)
    # The previous artifact contains a valid anchor_image_url
    previous_anchor_url = "https://storage.googleapis.com/test-bucket/anchor.png"
    previous_artifact = {
        "prompts": [],
        "anchor_image_url": previous_anchor_url 
    }
    
    state = {
        "plan": [{"id": 1, "role": "visualizer", "instruction": "Update the text on slide 2"}],
        "current_step_index": 0,
        "artifacts": {
            "step_0_visual": json.dumps(previous_artifact)
        },
        "messages": []
    }

    # 2. Mock Dependencies
    with patch("src.graph.nodes.get_llm_by_type") as mock_get_llm, \
         patch("src.graph.nodes.process_single_slide", new_callable=AsyncMock) as mock_process_slide, \
         patch("src.graph.nodes.download_blob_as_bytes", new_callable=MagicMock) as mock_download:
        
        # Mock LLM response (No new anchor prompt -> Reuse Strategy)
        mock_llm_instance = MagicMock()
        mock_structured_llm = MagicMock()
        
        # Visualizer output: 2 slides, NO anchor_image_prompt
        mock_output = VisualizerOutput(
            anchor_image_prompt=None, # Trigger reuse
            prompts=[
                ImagePrompt(slide_number=1, image_generation_prompt="Slide 1", rationale="test"),
                ImagePrompt(slide_number=2, image_generation_prompt="Slide 2", rationale="test")
            ]
        )
        
        mock_structured_llm.invoke.return_value = mock_output
        mock_get_llm.return_value.with_structured_output.return_value = mock_structured_llm

        # Mock Download (simulate downloading the anchor bytes)
        mock_anchor_bytes = b"fake_anchor_bytes"
        mock_download.return_value = mock_anchor_bytes

        # Mock process_single_slide return value
        call_counter = [0]  # Using list for mutable closure
        async def side_effect(prompt_item, previous_generations=None, override_reference_bytes=None, design_context=None):
            call_counter[0] += 1
            prompt_item.generated_image_url = f"https://fake_url/{call_counter[0]}.png"
            return prompt_item
        
        mock_process_slide.side_effect = side_effect

        # 3. Run Node
        result = await visualizer_node(state)

        # DEBUG: Check result content
        print(f"DEBUG: Result Update: {result.update}")
        
        # Check for errors in artifacts
        for key, value in result.update["artifacts"].items():
            if "visual" in key:
                try:
                    data = json.loads(value)
                    if "error" in data:
                        pytest.fail(f"Visualizer Node Error: {data['error']}")
                except:
                    pass

        # 4. Verify Logic

        # A. Verify Anchor Download was called with the PREVIOUS URL
        mock_download.assert_called_once_with(previous_anchor_url)
        
        # B. Verify process_single_slide was called for the 2 slides
        assert mock_process_slide.call_count == 2
        
        # C. Verify override_reference_bytes was passed to process_single_slide
        # Inspect the kwargs of the calls
        call_args_list = mock_process_slide.call_args_list
        for call in call_args_list:
            args, kwargs = call
            assert kwargs.get("override_reference_bytes") == mock_anchor_bytes

        # D. Verify the Result Artifact contains the REUSED anchor_image_url
        update_artifact_json = result.update["artifacts"]["step_1_visual"]
        update_data = json.loads(update_artifact_json)
        assert update_data["anchor_image_url"] == previous_anchor_url
