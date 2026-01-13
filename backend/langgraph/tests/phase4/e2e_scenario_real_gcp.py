
import asyncio
import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.graph import build_graph
from src.config import TEAM_MEMBERS

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("E2E_Test")

async def run_e2e():
    logger.info("Building graph...")
    graph = build_graph()

    print("\n" + "="*50)
    print("STEP 1: Initial Generation ('日本の経済成長について')")
    print("="*50 + "\n")

    initial_query = "日本の経済成長について"
    
    # State for Step 1
    input_state_1 = {
        "TEAM_MEMBERS": TEAM_MEMBERS,
        "messages": [{"role": "user", "content": initial_query}],
        "deep_thinking_mode": True,
        "search_before_planning": True,
    }

    config = {"recursion_limit": 50}

    logger.info("Invoking graph for Step 1...")
    result_1 = await graph.ainvoke(input_state_1, config)
    
    logger.info("Step 1 Complete.")
    
    # Verification of Step 1
    artifacts_1 = result_1.get("artifacts", {})
    # Assuming the final output is in artifacts or we can parse the last message
    # In this project structure, look for 'plan' or 'visualizer' outputs in artifacts
    
    print("\n--- Step 1 Results ---")
    if "visualizer" in result_1.get("plan", [{}])[-1].get("role", ""):
         print("Visualizer completed successfully (in plan).")
    
    # Simple check: print keys in artifacts to see what we got
    print("Artifacts keys:", list(artifacts_1.keys()))
    
    # Try to print slide titles if available in artifacts (e.g. from a visualizer step)
    # This depends on specific artifact key naming conventions, e.g., 'step_N_visual'
    for key, value in artifacts_1.items():
        if "visual" in key:
            try:
                data = json.loads(value)
                print(f"Artifact {key} prompts count:", len(data.get("prompts", [])))
                for p in data.get("prompts", []):
                    print(f" - Slide {p.get('slide_number')}: {p.get('image_generation_prompt')[:50]}...")
            except:
                print(f"Artifact {key} Content (raw): {value[:100]}...")

    print("\n" + "="*50)
    print("STEP 2: Refinement ('アメリカの経済についても追加して')")
    print("="*50 + "\n")

    refinement_query = "アメリカの経済についても追加して"
    
    # Prepare state for Step 2
    # We pass the full history of messages
    history = result_1["messages"]
    new_messages = history + [{"role": "user", "content": refinement_query}]
    
    # We also keep existing artifacts and plan context if needed, 
    # but strictly speaking 'messages' might be enough if the graph reconstructs state,
    # OR we should pass the entire 'result_1' state updated with new messages.
    # Let's pass the updated state from result_1.
    
    input_state_2 = result_1.copy()
    input_state_2["messages"] = new_messages
    
    logger.info("Invoking graph for Step 2...")
    result_2 = await graph.ainvoke(input_state_2, config)

    logger.info("Step 2 Complete.")

    # Verification of Step 2
    artifacts_2 = result_2.get("artifacts", {})
    print("\n--- Step 2 Results ---")
    print("Artifacts keys:", list(artifacts_2.keys()))

    found_america = False
    for key, value in artifacts_2.items():
        # Check if new artifacts were generated or existing ones updated
        if "visual" in key:
            try:
                data = json.loads(value)
                for p in data.get("prompts", []):
                    prompt_text = p.get('image_generation_prompt', '')
                    print(f" - Slide {p.get('slide_number')}: {prompt_text[:50]}...")
                    if "America" in prompt_text or "USA" in prompt_text or "米国" in prompt_text or "アメリカ" in prompt_text:
                        found_america = True
            except:
                pass
    
    if found_america:
        print("\n[SUCCESS] Found mention of 'America/USA' in generated slides.")
    else:
        print("\n[WARNING] Did not strictly find 'America' in slide prompts. Check manual output.")

if __name__ == "__main__":
    asyncio.run(run_e2e())
