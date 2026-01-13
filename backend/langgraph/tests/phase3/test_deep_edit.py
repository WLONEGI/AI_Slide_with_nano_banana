
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from src.schemas import VisualizerOutput, ImagePrompt, ThoughtSignature
from src.graph.nodes import visualizer_node
from src.graph.graph_types import State

@pytest.fixture
def mock_dependencies():
    with patch("src.utils.image_generation.generate_image") as mock_gen, \
         patch("src.utils.storage.upload_to_gcs") as mock_upload, \
         patch("src.utils.storage.download_blob_as_bytes") as mock_download, \
         patch("src.graph.nodes.apply_prompt_template") as mock_tmpl, \
         patch("src.graph.nodes.get_llm_by_type") as mock_get_llm:
         
        # Setup common mocks
        mock_upload.return_value = "https://gcs/uploaded.png"
        mock_download.return_value = b"reference_bytes"
        mock_gen.return_value = b"new_image_bytes"
        
        yield mock_gen, mock_upload, mock_download, mock_tmpl, mock_get_llm

@pytest.mark.asyncio
async def test_it05_deep_edit_flow(mock_dependencies):
    """IT-05: Verify Deep Edit Flow (Seed Reuse & Reference Anchor)."""
    mock_gen, mock_upload, mock_download, mock_tmpl, mock_get_llm = mock_dependencies

    # --- Step 1: Initial Generation ---
    # Mock LLM to return a new prompt
    initial_prompt = ImagePrompt(
        slide_number=1, 
        image_generation_prompt="A majestic mountain", 
        rationale="Nature"
    )
    mock_llm_obj = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = VisualizerOutput(prompts=[initial_prompt])
    mock_llm_obj.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm_obj

    # Setup State
    state_1 = {
        "plan": [{"id": 1, "role": "visualizer", "instruction": "Create slide"}],
        "current_step_index": 0,
        "artifacts": {},
        "messages": []
    }

    # Execute Visualizer
    result_1 = visualizer_node(state_1)
    
    # Verify Initial Generation
    assert mock_gen.call_count == 1
    call_args_1 = mock_gen.call_args
    # call_args[1] is kwargs. Check seed is random (int) and Ref is None
    invoked_seed = call_args_1.kwargs.get("seed")
    assert isinstance(invoked_seed, int)
    assert call_args_1.kwargs.get("reference_image") is None
    
    # Extract artifact content
    import json
    artifact_json_1 = result_1.update["artifacts"]["step_1_visual"]
    artifact_data_1 = json.loads(artifact_json_1)
    
    # Check ThoughtSignature created
    generated_prompt_1 = artifact_data_1["prompts"][0]
    assert "thought_signature" in generated_prompt_1
    sig_1 = generated_prompt_1["thought_signature"]
    assert sig_1["seed"] == invoked_seed
    assert sig_1["reference_image_url"] is None
    
    reference_url_1 = generated_prompt_1["generated_image_url"]
    assert reference_url_1 == "https://gcs/uploaded.png"

    # --- Step 2: Refinement (Deep Edit) ---
    # Update state with previous artifact
    state_2 = {
        "plan": [{"id": 2, "role": "visualizer", "instruction": "Make it blue"}],
        "current_step_index": 0,
        "artifacts": {"step_1_visual": artifact_json_1}, # Previous output available
        "messages": []
    }
    
    # Mock LLM to return REFINED prompt for SAME slide number
    refined_prompt = ImagePrompt(
        slide_number=1, # Matching slide number
        image_generation_prompt="A majestic mountain, blue style", 
        rationale="User request"
    )
    mock_structured.invoke.return_value = VisualizerOutput(prompts=[refined_prompt])
    
    # Execute Visualizer again
    result_2 = visualizer_node(state_2)
    
    # Verify Refinement Generation
    assert mock_gen.call_count == 2
    call_args_2 = mock_gen.call_args
    
    # Check Seed Reuse
    assert call_args_2.kwargs.get("seed") == invoked_seed # MUST MATCH Step 1
    
    # Check Reference Anchor
    # Should have downloaded image from reference_url_1
    mock_download.assert_called_with(reference_url_1)
    assert call_args_2.kwargs.get("reference_image") == b"reference_bytes"
    
    # Check New ThoughtSignature
    artifact_json_2 = result_2.update["artifacts"]["step_2_visual"]
    artifact_data_2 = json.loads(artifact_json_2)
    sig_2 = artifact_data_2["prompts"][0]["thought_signature"]
    
    assert sig_2["seed"] == invoked_seed
    assert sig_2["reference_image_url"] == reference_url_1
    assert sig_2["base_prompt"] == "A majestic mountain, blue style"
