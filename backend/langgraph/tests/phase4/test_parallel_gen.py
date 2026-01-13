
import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
from src.schemas import VisualizerOutput, ImagePrompt
from src.graph.nodes import visualizer_node
from src.graph.graph_types import State

@pytest.fixture
def mock_dependencies():
    with patch("src.utils.image_generation.generate_image") as mock_gen, \
         patch("src.utils.storage.upload_to_gcs") as mock_upload, \
         patch("src.utils.storage.download_blob_as_bytes") as mock_download, \
         patch("src.graph.nodes.apply_prompt_template") as mock_tmpl, \
         patch("src.graph.nodes.get_llm_by_type") as mock_get_llm:
         
        # Simulate latency in generate_image (0.1s per image)
        def delayed_gen(*args, **kwargs):
            time.sleep(0.1) # Simulate blocking IO (wrapped in to_thread)
            return b"image_bytes"
            
        mock_gen.side_effect = delayed_gen
        mock_upload.return_value = "https://gcs/uploaded.png"
        mock_download.return_value = b"reference_bytes"
        
        yield mock_gen, mock_upload, mock_download, mock_tmpl, mock_get_llm

@pytest.mark.asyncio
async def test_it06_parallel_generation_speed(mock_dependencies):
    """IT-06: Verify Visualizer generates images in parallel."""
    mock_gen, mock_upload, _, mock_tmpl, mock_get_llm = mock_dependencies

    # Setup State
    state = {
        "plan": [{"id": 1, "role": "visualizer", "instruction": "Generate 3 slides"}],
        "current_step_index": 0,
        "artifacts": {},
        "messages": []
    }

    # Mock LLM to return 3 prompts
    prompts = [
        ImagePrompt(slide_number=1, image_generation_prompt="Slide 1", rationale="R1"),
        ImagePrompt(slide_number=2, image_generation_prompt="Slide 2", rationale="R2"),
        ImagePrompt(slide_number=3, image_generation_prompt="Slide 3", rationale="R3"),
    ]
    
    mock_llm_obj = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = VisualizerOutput(prompts=prompts)
    mock_llm_obj.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm_obj

    # Measure execution time
    start_time = time.perf_counter()
    
    # Execute Async Node
    result = await visualizer_node(state)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # Assertions
    # 1. Check generated count
    assert mock_gen.call_count == 3
    
    # 2. Check Speed
    # 3 calls * 0.1s = 0.3s if sequential.
    # Parallel should be close to 0.1s + overhead.
    # We assert it's strictly less than sequential sum (0.3s) with some margin.
    print(f"Execution took {duration:.4f}s (Expected < 0.25s for 3 parallel tasks)")
    
    # Allow some buffer for thread overhead, but definitely should be faster than sequential
    assert duration < 0.28, f"Parallel execution too slow: {duration}s"
    
    # 3. Check Data Integrity
    import json
    artifact_json = result.update["artifacts"]["step_1_visual"]
    data = json.loads(artifact_json)
    assert len(data["prompts"]) == 3
    assert data["prompts"][0]["generated_image_url"] == "https://gcs/uploaded.png"
    assert "thought_signature" in data["prompts"][0]

@pytest.mark.asyncio
async def test_it06_parallel_error_handling(mock_dependencies):
    """IT-06: Verify one failure does not crash the batch."""
    mock_gen, _, _, _, mock_get_llm = mock_dependencies

    # Setup State
    state = {
        "plan": [{"id": 1, "role": "visualizer", "instruction": "Generate slides"}],
        "current_step_index": 0,
        "artifacts": {},
        "messages": []
    }

    prompts = [
        ImagePrompt(slide_number=1, image_generation_prompt="Good Slide", rationale="R1"),
        ImagePrompt(slide_number=2, image_generation_prompt="Bad Slide", rationale="R2"), 
    ]
    
    mock_llm_obj = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = VisualizerOutput(prompts=prompts)
    mock_llm_obj.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm_obj

    # Make the second generation fail
    def side_effect(prompt, **kwargs):
        if "Bad" in prompt:
            raise ValueError("Simulated Generation Error")
        return b"image_bytes"
    
    mock_gen.side_effect = side_effect

    # Execute
    result = await visualizer_node(state)
    
    # Assertions
    import json
    artifact_json = result.update["artifacts"]["step_1_visual"]
    data = json.loads(artifact_json)
    
    # Slide 1 should execute fine
    assert data["prompts"][0]["generated_image_url"] is not None
    
    # Slide 2 should have None URL (or handle error gracefully as per logic)
    # The current logic catches exception and returns prompt_item as is (url=None)
    assert data["prompts"][1]["generated_image_url"] is None 
