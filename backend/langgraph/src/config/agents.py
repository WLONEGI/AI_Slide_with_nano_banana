from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "high_reasoning"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic",  # basic llm
    "planner": "high_reasoning",  # Dedicated model
    "supervisor": "basic",  # basic llm
    "storywriter": "high_reasoning",  # Content creation needs strong reasoning
    "visualizer": "reasoning",   # Prompt creation using Reasoning Model
    "data_analyst": "reasoning", # Structure data for visualization
    "researcher": "basic",       # Search tasks
}
