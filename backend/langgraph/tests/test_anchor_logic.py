import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
from src.graph.nodes import visualizer_node, State
from src.schemas import VisualizerOutput, ImagePrompt, GenerationConfig

@pytest.mark.asyncio
async def test_visualizer_node_anchor_logic():
    # 1. Setup Mock State
    state = {
        "plan": [{"id": 1, "role": "visualizer", "instruction": "Make slides"}],
        "current_step_index": 0,
        "artifacts": {},
        "messages": []
    }

    # 2. Mock LLM Output (Style Anchor + 3 prompts)
    mock_prompts = [
        ImagePrompt(slide_number=1, image_generation_prompt="Prompt 1", rationale="R1"),
        ImagePrompt(slide_number=2, image_generation_prompt="Prompt 2", rationale="R2"),
        ImagePrompt(slide_number=3, image_generation_prompt="Prompt 3", rationale="R3"),
    ]
    # New: Include anchor_image_prompt
    mock_llm_output = VisualizerOutput(
        anchor_image_prompt="Style Anchor Prompt",
        prompts=mock_prompts,
        generation_config=GenerationConfig()
    )

    # 3. Patch dependencies
    with patch("src.graph.nodes.get_llm_by_type") as mock_get_llm, \
         patch("src.graph.nodes.generate_image") as mock_gen_image, \
         patch("src.graph.nodes.upload_to_gcs") as mock_upload, \
         patch("src.graph.nodes.download_blob_as_bytes") as mock_download:

        # Mock LLM behavior
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_llm_output
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm

        # Mock Utils behavior
        # Return bytes related to the prompt so we can check if anchor bytes were passed
        mock_gen_image.side_effect = lambda prompt, seed=None, reference_image=None, thought_signature=None: (f"IMAGE_BYTES_FOR_{prompt}".encode(), None)
        
        mock_upload.side_effect = lambda data, content_type: f"http://gcs/{hash(data)}.png"
        
        # When downloading, return anchor bytes
        mock_download.return_value = b"DOWNLOADED_ANCHOR_BYTES"

        # 4. Run the node
        result = await visualizer_node(state)

        # DEBUG: Check result content
        # result is a Command object
        print(f"DEBUG: Result Update: {result.update}")
        
        # Check if error occurred
        for key, value in result.update["artifacts"].items():
            if "visual" in key:
                data = json.loads(value)
                if "error" in data:
                    pytest.fail(f"Visualizer Node Error: {data['error']}")

        # 5. Verify Logic
        
        # Check generate_image calls: 1 (Style Anchor) + 3 (Slides) = 4 total
        assert mock_gen_image.call_count == 4
        
        call_args_list = mock_gen_image.call_args_list
        
        # 1. Verify Style Anchor Call (Should be first or logically handled)
        # Check call with "Style Anchor Prompt"
        anchor_call = next(c for c in call_args_list if "Style Anchor Prompt" in c[0][0])
        _, kwargs_anchor = anchor_call
        assert kwargs_anchor.get("reference_image") is None, "Style Anchor should NOT have a reference image"

        # 2. Verify Slides use the Anchor Bytes
        # Check Slide 1 (Prompt 1) - Should now use reference!
        call_1 = next(c for c in call_args_list if "Prompt 1" in c[0][0])
        _, kwargs_1 = call_1
        assert kwargs_1.get("reference_image") == b"DOWNLOADED_ANCHOR_BYTES", "Slide 1 MUST use the Style Anchor bytes"

        # Check Slide 2
        call_2 = next(c for c in call_args_list if "Prompt 2" in c[0][0])
        _, kwargs_2 = call_2
        assert kwargs_2.get("reference_image") == b"DOWNLOADED_ANCHOR_BYTES", "Slide 2 MUST use the Style Anchor bytes"
        
        # Check Slide 3
        call_3 = next(c for c in call_args_list if "Prompt 3" in c[0][0])
        _, kwargs_3 = call_3
        assert kwargs_3.get("reference_image") == b"DOWNLOADED_ANCHOR_BYTES", "Slide 3 MUST use the Style Anchor bytes"

        print("Test Passed: Separate Style Anchor logic verified.")
