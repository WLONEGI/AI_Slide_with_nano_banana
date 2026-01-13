from langgraph.prebuilt import create_react_agent

from src.prompts import apply_prompt_template
from src.tools import (
    crawl_tool,
    google_search_tool,
)

from .llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP

# Create agents using configured LLM types
research_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["researcher"]),
    tools=[google_search_tool, crawl_tool],
    prompt=lambda state: apply_prompt_template("researcher", state),
)

storywriter_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["storywriter"]),
    tools=[],  # Pure text generation
    prompt=lambda state: apply_prompt_template("storywriter", state),
)

visualizer_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["visualizer"]),
    tools=[],  # Will define image gen tool logic in node
    prompt=lambda state: apply_prompt_template("visualizer", state),
)
