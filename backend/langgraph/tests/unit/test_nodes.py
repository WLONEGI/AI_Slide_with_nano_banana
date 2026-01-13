import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from src.graph.nodes import (
    process_single_slide, 
    visualizer_node, 
    reviewer_node, 
    supervisor_node,
    _update_artifact
)
from src.schemas import ImagePrompt, ReviewOutput, VisualizerOutput
from langchain_core.messages import HumanMessage
from src.config.constants import MAX_RETRIES, MAX_REPLANNING

# === Fixtures ===

@pytest.fixture
def mock_storage():
    with patch("src.graph.nodes.upload_to_gcs") as mock_upload, \
         patch("src.graph.nodes.download_blob_as_bytes") as mock_download:
        yield mock_upload, mock_download

@pytest.fixture
def mock_gen_image():
    with patch("src.graph.nodes.generate_image") as mock:
        yield mock

# === Tests for process_single_slide ===

@pytest.mark.asyncio
async def test_process_single_slide_basic(mock_storage, mock_gen_image):
    mock_upload, mock_download = mock_storage
    
    # Setup mocks
    mock_gen_image.return_value = b"image_data"
    mock_upload.return_value = "http://gcs/image.png"

    item = ImagePrompt(slide_number=1, image_generation_prompt="A cat", rationale="reason")
    
    result = await process_single_slide(item)
    
    assert result.generated_image_url == "http://gcs/image.png"
    assert result.thought_signature.seed is not None
    assert result.thought_signature.base_prompt == "A cat"
    
    mock_gen_image.assert_called_once()
    mock_upload.assert_called_once()

@pytest.mark.asyncio
async def test_process_single_slide_deep_edit_match(mock_storage, mock_gen_image):
    mock_upload, mock_download = mock_storage
    mock_gen_image.return_value = b"new_image"
    mock_upload.return_value = "http://gcs/new.png"
    mock_download.return_value = b"ref_image"

    previous_generations = [{
        "slide_number": 2,
        "thought_signature": {"seed": 999},
        "generated_image_url": "http://old/ref.png"
    }]
    
    item = ImagePrompt(slide_number=2, image_generation_prompt="A dog", rationale="reason")
    
    result = await process_single_slide(item, previous_generations=previous_generations)
    
    assert result.thought_signature.seed == 999
    mock_download.assert_called_with("http://old/ref.png")
    mock_gen_image.assert_called_with("A dog", seed=999, reference_image=b"ref_image")

@pytest.mark.asyncio
async def test_process_single_slide_override_anchor(mock_storage, mock_gen_image):
    mock_upload, _ = mock_storage
    mock_gen_image.return_value = b"new_image"
    mock_upload.return_value = "http://gcs/new.png"
    
    anchor_bytes = b"anchor_bytes"
    item = ImagePrompt(slide_number=1, image_generation_prompt="Prompt", rationale="Reason")
    
    await process_single_slide(item, override_reference_bytes=anchor_bytes)
    
    mock_gen_image.assert_called_with("Prompt", seed=ANY, reference_image=anchor_bytes)


# === Tests for visualizer_node ===

@pytest.fixture
def mock_llm():
    with patch("src.graph.nodes.get_llm_by_type") as mock:
        yield mock

@pytest.fixture
def mock_apply_template():
    with patch("src.graph.nodes.apply_prompt_template") as mock:
        mock.return_value = [HumanMessage(content="template")]
        yield mock

@pytest.mark.asyncio
async def test_visualizer_node_strategy_a(mock_llm, mock_apply_template, mock_storage):
    mock_upload, mock_download = mock_storage
    
    state = {
        "plan": [{"id": 1, "instruction": "Make slides", "role": "visualizer"}],
        "current_step_index": 0,
        "artifacts": {}
    }
    
    mock_structured_llm = MagicMock()
    mock_llm.return_value.with_structured_output.return_value = mock_structured_llm
    
    result_output = VisualizerOutput(
        prompts=[ImagePrompt(slide_number=1, image_generation_prompt="Slide 1", rationale="r")],
        anchor_image_prompt="Style Anchor"
    )
    mock_structured_llm.invoke.return_value = result_output
    
    # We patch process_single_slide where it is defined, which is correct for internal calls
    with patch("src.graph.nodes.process_single_slide", new_callable=AsyncMock) as mock_process:
        # Mock returns
        anchor_ret = ImagePrompt(slide_number=0, image_generation_prompt="Style Anchor", rationale="r")
        anchor_ret.generated_image_url = "http://anchor"
        
        slide_ret = ImagePrompt(slide_number=1, image_generation_prompt="Slide 1", rationale="r")
        slide_ret.generated_image_url = "http://slide1"
        
        # side_effect using async function to return correct objects
        async def side_effect_func(*args, **kwargs):
            item = args[0]
            if item.slide_number == 0:
                return anchor_ret
            return slide_ret
            
        mock_process.side_effect = side_effect_func
        
        mock_download.return_value = b"anchor_bytes"
        
        cmd = await visualizer_node(state)
        
        assert cmd.goto == "reviewer"
        assert "visualizer" in cmd.update["messages"][0].content
        
        # Verify calls
        assert mock_process.call_count == 2
        # Check Strategy A implementation details
        # 1. Anchor generation
        args1, _ = mock_process.call_args_list[0]
        assert args1[0].slide_number == 0
        
        # 2. Target generation
        args2, kwargs2 = mock_process.call_args_list[1]
        assert args2[0].slide_number == 1
        assert kwargs2.get("override_reference_bytes") == b"anchor_bytes"


# === Tests for reviewer_node ===

def test_reviewer_node_approval(mock_llm):
    state = {
        "plan": [{"id": 1, "instruction": "Do X", "role": "storywriter"}],
        "current_step_index": 0,
        "artifacts": {"step_1_story": "{}"},
        "retry_count": 0
    }
    
    mock_structured = MagicMock()
    mock_llm.return_value.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = ReviewOutput(approved=True, score=0.9, feedback="Good")
    
    cmd = reviewer_node(state)
    
    assert cmd.goto == "supervisor"
    assert cmd.update["current_quality_score"] == 0.9

def test_reviewer_node_rejection_retry(mock_llm):
    state = {
        "plan": [{"id": 1, "instruction": "Do X", "role": "storywriter"}],
        "current_step_index": 0,
        "artifacts": {"step_1_story": "{}"},
        "retry_count": 0
    }
    
    mock_structured = MagicMock()
    mock_llm.return_value.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = ReviewOutput(approved=False, score=0.3, feedback="Bad")
    
    cmd = reviewer_node(state)
    
    assert cmd.goto == "storywriter"
    assert cmd.update["retry_count"] == 1

def test_reviewer_node_max_retries(mock_llm):
    state = {
        "plan": [{"id": 1, "instruction": "Do X", "role": "storywriter"}],
        "current_step_index": 0,
        "artifacts": {"step_1_story": "{}"},
        "retry_count": MAX_RETRIES
    }
    
    mock_structured = MagicMock()
    mock_llm.return_value.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = ReviewOutput(approved=False, score=0.3, feedback="Bad")
    
    cmd = reviewer_node(state)
    
    assert cmd.goto == "supervisor"
    assert "error_context" in cmd.update


# === Tests for supervisor_node ===

def test_supervisor_replanning():
    state = {
        "current_step_index": 0,
        "plan": [{"id": 1, "role": "storywriter"}],
        "error_context": "Something went wrong",
        "replanning_count": 0
    }
    
    cmd = supervisor_node(state)
    
    assert cmd.goto == "planner"
    assert cmd.update["replanning_count"] == 1

def test_supervisor_max_replanning():
    state = {
        "current_step_index": 0,
        "plan": [{"id": 1, "role": "storywriter"}],
        "error_context": "Something went wrong",
        "replanning_count": MAX_REPLANNING
    }
    
    cmd = supervisor_node(state)
    
    assert cmd.goto == "__end__"
