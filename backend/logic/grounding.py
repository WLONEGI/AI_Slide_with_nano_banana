
from .vertex_wrapper import get_gemini
import logging
import os
from typing import Optional, List, Dict, Any, Union

try:
    from vertexai.generative_models import Tool
except ImportError:
    try:
        from vertexai.preview.generative_models import Tool
    except Exception:
        Tool = None

GoogleSearchRetrieval = None # Not needed with from_dict strategy

logger = logging.getLogger(__name__)

async def perform_grounding(query: str) -> str:
    """
    Performs a grounded search using Gemini and returns a summary + sources.
    
    Args:
        query (str): The search query.

    Returns:
        str: A summary of grounded information.
    """
    # Note: Vertex AI "Grounding with Google Search" is typically configured 
    # via tools in the generation config or using specific grounding services.
    # For this prototype, we'll simulate it by asking Gemini to "Answer using your knowledge" 
    # or using the actual Tool if available/configured in the wrapper.
    # The detailed Requirement says: "Grounding (Web Search) ... Sources slide".
    
    grounding_mode: str = os.getenv("GROUNDING_MODE", "auto").lower()
    if grounding_mode in {"off", "disabled", "false", "0"}:
        logger.info("Grounding disabled via GROUNDING_MODE=%s. Falling back to internal knowledge.", grounding_mode)
        return ""

    model = get_gemini()

    # Check if we are mocking
    # Checking for specific mock class or attribute to determine if it is a mock model
    if hasattr(model, "generate_content") and "mock" in str(type(model)).lower():
        logger.info("Grounding using mock model. Returning mock grounding info.")
        return "Based on search results, AI Slide Generator is a cutting-edge prototype. Source: internal-mock-db."

    # Real implementation using Grounding Tool
    # Note: Grounding with Google Search requires enterprise_search or similar setup usually.
    # We will use the 'tools' parameter if available in the SDK version.
    
    if not Tool:
        logger.warning("Grounding tool is unavailable in this environment. Falling back to internal knowledge.")
        return ""

    # Use Google Search Grounding via dictionary configuration
    # This avoids import issues with GoogleSearchRetrieval vs GoogleSearch
    tools: List[Tool] = [
        Tool.from_dict({"google_search": {}})
    ]
    
    prompt: str = (
        f"Research the following topic: {query}\n\n"
        "Provide a professional, concise summary of key facts and trends. "
        "Focus on structured insights that would be useful for a presentation slide. "
        "Keep the combined summary under 2 paragraphs."
    )
    
    try:
        response = model.generate_content(
            prompt,
            tools=tools
        )
        logger.info("Grounding succeeded. Using grounded response.")
        return response.text
    except Exception as e:
        logger.error(f"Grounding error: {e}")
        logger.warning("Grounding failed. Falling back to internal knowledge.")
        return ""
