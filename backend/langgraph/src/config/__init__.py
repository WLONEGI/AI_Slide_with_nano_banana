from .env import (
    # Reasoning LLM
    REASONING_MODEL,
    REASONING_BASE_URL,
    REASONING_API_KEY,
    # Basic LLM
    BASIC_MODEL,
    BASIC_BASE_URL,
    BASIC_API_KEY,
    # Vision-language LLM
    VL_MODEL,
    VL_BASE_URL,
    VL_API_KEY,
    # Other configurations
    CHROME_INSTANCE_PATH,
    # Vertex AI
    VERTEX_PROJECT_ID,
    VERTEX_LOCATION,
)
from .tools import GOOGLE_SEARCH_MAX_RESULTS

# Team configuration
TEAM_MEMBERS = ["storywriter", "researcher", "visualizer", "data_analyst"]

__all__ = [
    # Reasoning LLM
    "REASONING_MODEL",
    "REASONING_BASE_URL",
    "REASONING_API_KEY",
    # Basic LLM
    "BASIC_MODEL",
    "BASIC_BASE_URL",
    "BASIC_API_KEY",
    # Vision-language LLM
    "VL_MODEL",
    "VL_BASE_URL",
    "VL_API_KEY",
    # Other configurations
    "TEAM_MEMBERS",
    "GOOGLE_SEARCH_MAX_RESULTS",
    "CHROME_INSTANCE_PATH",
    # Vertex AI
    "VERTEX_PROJECT_ID",
    "VERTEX_LOCATION",
]
