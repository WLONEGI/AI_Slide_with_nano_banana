
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.graph.nodes import visualizer_node
from src.schemas.outputs import VisualizerOutput, ImagePrompt, GenerationConfig

@pytest.mark.asyncio
async def test_design_direction_injection():
    """Verify that design_direction from Planner is injected into Visualizer context"""
    
    # State with design_direction
    state = {
        "messages": [],
        "plan": [
            {
                "id": 1, 
                "role": "visualizer", 
                "instruction": "Generate slides", 
                "description": "Visualisation",
                "design_direction": "Cyberpunk Neon Tokyo Style"  # KEY INPUT
            }
        ],
        "artifacts": {},
        "current_step_index": 0,
        "design_context": None
    }
    
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    # Empty result to avoid crash
    mock_structured_llm.invoke.return_value = VisualizerOutput(
        prompts=[], 
        generation_config=GenerationConfig()
    )
    
    with patch("src.graph.nodes.get_llm_by_type", return_value=mock_llm), \
         patch("src.graph.nodes.apply_prompt_template") as mock_template:
        
        mock_template.return_value = []
        
        await visualizer_node(state)
        
        # Verify context injection
        # apply_prompt_template is called FIRST to get base messages
        # THEN we append HumanMessage(content=context)
        # So we check `mock_structured_llm.invoke(messages)`
        
        call_args = mock_structured_llm.invoke.call_args
        messages = call_args[0][0]
        
        # The last message should be the context injection
        last_message = messages[-1]
        assert "Cyberpunk Neon Tokyo Style" in last_message.content
        assert "[Design Direction from Planner]" in last_message.content
