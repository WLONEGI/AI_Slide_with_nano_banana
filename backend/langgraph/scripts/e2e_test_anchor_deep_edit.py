
import asyncio
import logging
import json
import sys
import os
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Ensure src module is visible
sys.path.append(os.getcwd())

from src.graph.builder import build_graph
from src.config import TEAM_MEMBERS

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Helper to find the latest visual artifact
def search_anchor_url(state):
    anchor_url = None
    if "artifacts" in state:
        for key, value in state["artifacts"].items():
            if key.endswith("_visual"): # e.g. step_2_visual
                try:
                    data = json.loads(value)
                    if data.get("anchor_image_url"):
                        anchor_url = data["anchor_image_url"]
                        logger.info(f"Found visual artifact '{key}' with anchor URL: {anchor_url}")
                except Exception as e:
                    logger.error(f"Error parsing artifact {key}: {e}")
    return anchor_url

async def main():
    logger.info("Starting E2E Test: Anchor Image & Deep Edit")
    
    # -------------------------------------------------------------------------
    # AUTH SETUP: Use credentials.json and verify Vertex AI mode
    # -------------------------------------------------------------------------
    creds_path = os.path.abspath("credentials.json")
    if not os.path.exists(creds_path):
        logger.error(f"Credentials file not found at: {creds_path}")
        sys.exit(1)
        
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    
    # Extract Project ID from credentials
    with open(creds_path, "r") as f:
        creds_data = json.load(f)
        project_id = creds_data.get("project_id")
        
    if not project_id:
        logger.error("Could not find 'project_id' in credentials.json")
        sys.exit(1)
        
    logger.info(f"Using Credentials: {creds_path}")
    logger.info(f"Target Project ID: {project_id}")

    # Ensure VERTEX_PROJECT_ID is set in env so llm.py picks it up
    os.environ["VERTEX_PROJECT_ID"] = project_id
    
    # Reload config to ensure it picks up the project ID if it wasn't there
    import src.config.env
    src.config.env.VERTEX_PROJECT_ID = project_id
    
    # Clear cache to ensure LLMs are recreated with Vertex config
    import src.agents.llm
    src.agents.llm.VERTEX_PROJECT_ID = project_id
    src.agents.llm.get_llm_by_type.cache_clear()
    
    logger.info("Auth configured. Using models from .env with Vertex AI.")
    # -------------------------------------------------------------------------

    # 1. Setup Graph with Memory Checkpointer
    memory = MemorySaver()
    graph = build_graph(checkpointer=memory)
    
    thread_id = "test_thread_e2e_anchor"
    config = {"configurable": {"thread_id": thread_id}}

    # =========================================================================
    # ROUND 1: Initial Generation
    # =========================================================================
    input_text_1 = "日本の経済成長について"
    logger.info(f"\n[Run 1] Sending User Input: {input_text_1}")

    # We use invoke/stream. Using invoke for simplicity, but for memory we need to correctly manage state inputs.
    # When using checkpointer, we typically pass the input dict.
    
    initial_inputs = {
        "TEAM_MEMBERS": TEAM_MEMBERS,
        "messages": [HumanMessage(content=input_text_1)],
        "deep_thinking_mode": True,
        "search_before_planning": True,
    }

    # Running the graph
    # Note: 'graph.invoke' with checkpointer will save state to 'thread_id'
    final_state_1 = await graph.ainvoke(initial_inputs, config=config)
    
    logger.info("[Run 1] Completed.")
    
    # Verify Anchor URL
    anchor_url_1 = search_anchor_url(final_state_1)
    if not anchor_url_1:
        logger.error("FAILED: No anchor_image_url found in Run 1 artifacts!")
        sys.exit(1)
    
    logger.info(f"SUCCESS (Run 1): Generated Anchor URL: {anchor_url_1}")

    # =========================================================================
    # ROUND 2: Deep Edit (Refinement)
    # =========================================================================
    input_text_2 = "アメリカの経済についても追加して"
    logger.info(f"\n[Run 2] Sending User Input: {input_text_2} (Deep Edit Mode)")

    # For subsequent runs in same thread, we just provide the new messages
    # The 'plan' and other state keys should be preserved/updated by the graph logic.
    second_inputs = {
        "messages": [HumanMessage(content=input_text_2)],
        # We might need to re-supply constants or let them persist? 
        # StateGraph schema usually merges keys. TEAM_MEMBERS is likely static.
        # But 'deep_thinking_mode' etc might need to be re-passed if they are not reduced/preserved or if we want to change them.
        # Assuming they persist or defaulted.
    }

    final_state_2 = await graph.ainvoke(second_inputs, config=config)

    logger.info("[Run 2] Completed.")

    # Verify Anchor URL Persistence
    anchor_url_2 = search_anchor_url(final_state_2)
    
    if not anchor_url_2:
        logger.error("FAILED: No anchor_image_url found in Run 2 artifacts!")
        sys.exit(1)

    if anchor_url_1 == anchor_url_2:
        logger.info(f"SUCCESS (Run 2): Reused Anchor URL: {anchor_url_2}")
    else:
        logger.warning(f"WARNING: Anchor URL changed! \nRun 1: {anchor_url_1}\nRun 2: {anchor_url_2}")
        # This might be valid if the LLM decided to regenerate everything? But our Deep Edit goal is consistency.
        # If it changed, we should check logs (which we can't easily here without streaming)
        sys.exit(1)

    logger.info("\n=== E2E Test Passed Successfully ===")

if __name__ == "__main__":
    asyncio.run(main())
