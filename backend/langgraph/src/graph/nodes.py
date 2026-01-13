import asyncio
import logging
import json
import random
from copy import deepcopy
from typing import Literal, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from src.agents import research_agent, storywriter_agent, visualizer_agent
from src.agents.llm import get_llm_by_type
from src.config import TEAM_MEMBERS
from src.config.agents import AGENT_LLM_MAP
from src.config.settings import settings

from src.prompts.template import apply_prompt_template
from src.tools.search import google_search_tool
from src.schemas import (
    PlannerOutput,
    StorywriterOutput,
    VisualizerOutput,
    DataAnalystOutput,
    ReviewOutput,
    ThoughtSignature,
    ImagePrompt,
)
from src.utils.image_generation import generate_image
from src.utils.storage import upload_to_gcs, download_blob_as_bytes

from .graph_types import State, TaskStep

logger = logging.getLogger(__name__)


def _update_artifact(state: State, key: str, value: Any) -> dict[str, Any]:
    """Helper to update artifacts dictionary."""
    artifacts = state.get("artifacts", {})
    artifacts[key] = value
    return artifacts


def research_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the researcher agent (ReAct agent with google_search_tool)."""
    logger.info("Research agent starting task")
    # Inject specific instruction from plan if available
    current_step = state["plan"][state["current_step_index"]]
    instruction_msg = HumanMessage(content=f"Requirement: {current_step['instruction']}", name="supervisor")
    
    # Temporarily append instruction to messages for this invoke
    invoke_state = deepcopy(state)
    invoke_state["messages"].append(instruction_msg)
    
    result = research_agent.invoke(invoke_state, {"recursion_limit": settings.RECURSION_LIMIT_RESEARCHER})  # max tool calls
    content = result["messages"][-1].content
    
    return Command(
        update={
            "messages": [
                HumanMessage(content=settings.RESPONSE_FORMAT.format(role="researcher", content=content), name="researcher")
            ],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_research", content)
        },
        goto="reviewer",
    )




def storywriter_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for storywriter agent - uses structured output."""
    logger.info("Storywriter starting task")
    current_step = state["plan"][state["current_step_index"]]
    
    # Provide context including artifacts
    context = f"Instruction: {current_step['instruction']}\n\nAvailable Artifacts: {json.dumps(state.get('artifacts', {}), default=str)}"
    
    # Build messages with prompt template
    messages = apply_prompt_template("storywriter", state)
    messages.append(HumanMessage(content=context, name="supervisor"))
    
    # Use structured output with Pydantic schema
    llm = get_llm_by_type(AGENT_LLM_MAP["storywriter"])
    structured_llm = llm.with_structured_output(StorywriterOutput)
    
    try:
        result: StorywriterOutput = structured_llm.invoke(messages)
        content_json = result.model_dump_json(ensure_ascii=False, indent=2)
        logger.info(f"Storywriter generated {len(result.slides)} slides")
    except Exception as e:
        logger.error(f"Storywriter structured output failed: {e}")
        content_json = json.dumps({"error": str(e)}, ensure_ascii=False)

    return Command(
        update={
            "messages": [HumanMessage(content=settings.RESPONSE_FORMAT.format(role="storywriter", content=content_json), name="storywriter")],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_story", content_json)
        },
        goto="reviewer",
    )

# Helper for single slide processing
async def process_single_slide(
    prompt_item: ImagePrompt, 
    previous_generations: list[dict] | None = None, 
    override_reference_bytes: bytes | None = None
) -> ImagePrompt:
    """
    Helper function to process a single slide: generation or edit.

    Handles the core image generation logic, including:
    1. Seed management for determinism (reusing seed from ThoughtSignature).
    2. Reference image handling for Deep Edit / Visual Consistency.
    3. Image generation via Vertex AI.
    4. Uploading to GCS.

    Args:
        prompt_item (ImagePrompt): The prompt object containing the image generation instruction.
        previous_generations (list[dict] | None): List of previous generation data for "Deep Edit" logic.
        override_reference_bytes (bytes | None): Optional image bytes to force as a reference (e.g., Anchor Image).
                                                 If provided, this takes precedence over previous generations.

    Returns:
        ImagePrompt: Updated prompt item with `generated_image_url` and `thought_signature` populated.

    Raises:
        Exception: Captures and logs generation failures, returning the item with None URL to allow partial batch success.
    """


    try:
        logger.info(f"Processing image generation for slide {prompt_item.slide_number}...")
        
        # === Deep Edit Logic ===
        seed = None
        reference_image_bytes = None
        reference_url = None
        
        # 1. Use Override (Anchor Image) if provided
        if override_reference_bytes:
            logger.info(f"Using Anchor Image as reference for slide {prompt_item.slide_number}")
            reference_image_bytes = override_reference_bytes
            # Note: We don't necessarily set reference_url here as it's an in-memory byte buffer from the anchor.
        
        # 2. Check for matching previous generation to anchor consistency (Deep Edit)
        # Only check if we don't already have an override (or maybe override takes precedence? Yes, Anchor Strategy forces consistency)
        # However, if we are doing a specific re-generation of a slide in a deck that already has an anchor... 
        # For now, let's assume if override is passed, it wins.
        # 2. Check for matching previous generation to anchor consistency (Deep Edit)
        elif previous_generations:
            # Match by slide_number logic (assuming slide numbers are stable)
            for prev in previous_generations:
                if prev.get("slide_number") != prompt_item.slide_number:
                    continue
                
                # 1. Reuse Seed (Thought Signature)
                prev_sig = prev.get("thought_signature")
                if prev_sig and "seed" in prev_sig:
                    seed = prev_sig["seed"]
                    logger.info(f"Reusing seed {seed} from ThoughtSignature")
                
                # 2. Reference Anchor (Visual Consistency)
                if prev.get("generated_image_url"):
                    reference_url = prev["generated_image_url"]
                    logger.info(f"Downloading reference anchor from {reference_url}...")
                    try:
                        reference_image_bytes = await asyncio.to_thread(download_blob_as_bytes, reference_url)
                    except Exception as e:
                        logger.warning(f"Failed to download previous reference image: {e}")
                
                break
        
        # Generate new seed if none found
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        logger.info(f"Generating image {prompt_item.slide_number}/{'batch'} with Seed: {seed}, Ref: {bool(reference_image_bytes)}...")
        
        # 1. Generate Image (Blocking -> Thread)
        image_bytes = await asyncio.to_thread(
            generate_image,
            prompt_item.image_generation_prompt, 
            seed=seed,
            reference_image=reference_image_bytes
        )
        
        # 2. Upload to GCS (Blocking -> Thread)
        logger.info(f"Uploading image {prompt_item.slide_number} to GCS...")
        public_url = await asyncio.to_thread(upload_to_gcs, image_bytes, content_type="image/png")
        
        # 3. Update Result & Signature
        prompt_item.generated_image_url = public_url
        
        # Create ThoughtSignature
        prompt_item.thought_signature = ThoughtSignature(
            seed=seed,
            base_prompt=prompt_item.image_generation_prompt,
            refined_prompt=None, # This IS the prompt used.
            model_version=AGENT_LLM_MAP["visualizer"],
            reference_image_url=reference_url or (prompt_item.thought_signature.reference_image_url if prompt_item.thought_signature else None)
        )
        
        logger.info(f"Image generated and stored at: {public_url}")
        return prompt_item

    except Exception as img_err:
        logger.error(f"Failed to generate/upload image for prompt {prompt_item.slide_number}: {img_err}")
        # Return item as-is (with None URL) to avoid crashing the whole batch
        return prompt_item


async def visualizer_node(state: State) -> Command[Literal["supervisor"]]:
    """
    Node for the Visualizer agent. Responsible for generating slide images.

    This node executes the following complex logic:
    1. **Context Preparation**: Gathers instructions and previous artifacts.
    2. **Edit Mode Detection**: Identifies if this is a modification of existing slides.
    3. **Prompt Generation**: Uses the LLM to generate image prompts (ImagePrompt schema).
    4. **Anchor Strategy (Visual Consistency)**:
        - **Strategy A (Preferred)**: Generates a dedicated 'Style Anchor' image first, then uses it as a reference for all slides.
        - **Strategy B (Reuse)**: Reuses an existing anchor from a previous run (Deep Edit).
        - **Strategy C (Fallback)**: Uses the first slide as the anchor if no dedicated style is defined.
    5. **Parallel Execution**: Generates images concurrently using `asyncio.gather` with a semaphore.

    Args:
        state (State): Current graph state.

    Returns:
        Command[Literal["supervisor"]]: Route to supervisor (via reviewer) with generated artifacts.
    """
    logger.info("Visualizer starting task")
    current_step = state["plan"][state["current_step_index"]]
    
    context = f"Instruction: {current_step['instruction']}\n\nAvailable Artifacts: {json.dumps(state.get('artifacts', {}), default=str)}"

    # === Phase 3: Deep Edit Workflow (Thought Signature) ===
    # Check for previous visualizer outputs to enable "Edit Mode"
    previous_generations = []
    for key, json_str in state.get("artifacts", {}).items():
        if key.endswith("_visual"):
            try:
                data = json.loads(json_str)
                if "prompts" in data:
                    previous_generations.extend(data["prompts"])
            except:
                pass
    
    # Check for previous Anchor URL
    previous_anchor_url = None
    for key, json_str in state.get("artifacts", {}).items():
        if key.endswith("_visual"):
            try:
                data = json.loads(json_str)
                if "anchor_image_url" in data and data["anchor_image_url"]:
                    previous_anchor_url = data["anchor_image_url"]
                    logger.info(f"Found existing Anchor URL in artifacts: {previous_anchor_url}")
                    break # Use the first found anchor
            except:
                pass
    
    if previous_generations:
        context += f"\n\n# PREVIOUS GENERATIONS (EDIT MODE)\nUser wants to modify these. Maintain consistency with seed/style if specified:\n{json.dumps(previous_generations, ensure_ascii=False, indent=2)}"
    
    # Build messages with prompt template
    messages = apply_prompt_template("visualizer", state)
    messages.append(HumanMessage(content=context, name="supervisor"))
    
    # Use structured output with Pydantic schema
    llm = get_llm_by_type(AGENT_LLM_MAP["visualizer"])
    structured_llm = llm.with_structured_output(VisualizerOutput)
    
    try:
        result: VisualizerOutput = structured_llm.invoke(messages)
        
        # [NEW Phase 4 + Anchor Logic] Parallel Execution with Anchor
        
        prompts = result.prompts
        updated_prompts = []
        anchor_bytes = None
        
        # === Strategy Determination ===
        anchor_prompt_text = result.anchor_image_prompt
        if anchor_prompt_text:
            # === STRATEGY A: Separate Style Anchor (Preferred) ===
            logger.info("Found 'anchor_image_prompt'. Generating dedicated Style Anchor Image...")
            
            anchor_item = ImagePrompt(
                slide_number=0, # 0 for Anchor
                image_generation_prompt=anchor_prompt_text,
                rationale="Style Anchor for consistency"
            )
            
            # Process Anchor
            # Note: Anchor itself has NO reference image, so previous_generations can be ignored or passed safely.
            # Passing 'override_reference_bytes=None' explicitly.
            processed_anchor = await process_single_slide(anchor_item, previous_generations, override_reference_bytes=None)
            
            if processed_anchor.generated_image_url:
                try:
                    anchor_bytes = await asyncio.to_thread(download_blob_as_bytes, processed_anchor.generated_image_url)
                    logger.info(f"Style Anchor Image downloaded ({len(anchor_bytes)} bytes).")
                    result.anchor_image_url = processed_anchor.generated_image_url
                except Exception as e:
                    logger.error(f"Failed to download Style Anchor Image: {e}. Proceeding without anchor.")
            
            target_prompts = prompts

        elif previous_anchor_url:
            # === STRATEGY B: Reuse Existing Style Anchor (Deep Edit) ===
            logger.info(f"Reusing existing Anchor URL: {previous_anchor_url}")
            try:
                anchor_bytes = await asyncio.to_thread(download_blob_as_bytes, previous_anchor_url)
                logger.info(f"Existing Style Anchor downloaded ({len(anchor_bytes)} bytes).")
                result.anchor_image_url = previous_anchor_url
            except Exception as e:
                logger.error(f"Failed to download existing Style Anchor: {e}. Falling back to Slide 1 strategy.")
                anchor_bytes = None
                
            target_prompts = prompts

        elif prompts:
             # === STRATEGY C: First Slide as Anchor (Fallback) ===
            logger.info("No 'anchor_image_prompt' found. Using Slide 1 as Anchor (Fallback Strategy)...")
            
            anchor_prompt = prompts[0]
            # Process Anchor (Slide 1) - No override
            processed_anchor = await process_single_slide(anchor_prompt, previous_generations, override_reference_bytes=None)
            updated_prompts.append(processed_anchor)
            
            if processed_anchor.generated_image_url:
                try:
                    anchor_bytes = await asyncio.to_thread(download_blob_as_bytes, processed_anchor.generated_image_url)
                    logger.info(f"Anchor Image (Slide 1) downloaded.")
                except Exception as e:
                    logger.error(f"Failed to download Anchor Image: {e}.")
            
            target_prompts = prompts[1:]
        else:
            logger.warning("No prompts generated by Visualizer.")
            target_prompts = []

        # 2. Parallel Processing for Target Prompts
        if target_prompts:
            # Limit concurrency
            semaphore = asyncio.Semaphore(settings.VISUALIZER_CONCURRENCY)
            
            async def constrained_task(prompt_item, idx):
                async with semaphore:
                    # Pass anchor_bytes as override
                    return await process_single_slide(prompt_item, previous_generations, override_reference_bytes=anchor_bytes)

            # Note on indices: enumerate starts at 0. 
            # If Strategy A, we are strictly processing prompts in order.
            # If Strategy B, we appended Slide 1 already, so we continue.
            
            # Fix index offset
            start_offset = 1 if not updated_prompts else 2 # If empty updated_prompts, start at 1 (Slide 1). If we rely on prompts[1:], it was slide 2.
            # Actually, using prompt_item.slide_number is better for logging inside process_single_slide. 'idx' is just for loop counting.
            
            tasks = [constrained_task(item, i) for i, item in enumerate(target_prompts)]
            
            if tasks:
                logger.info(f"Starting parallel generation for {len(tasks)} slides using Anchor...")
                processed_targets = await asyncio.gather(*tasks)
                updated_prompts.extend(processed_targets)
        
        # Update results
        # Sort by slide number just in case
        updated_prompts.sort(key=lambda x: x.slide_number)
        result.prompts = updated_prompts
        
        # content_json = result.model_dump_json(ensure_ascii=False, indent=2) # Pydantic V2 dump_json doesn't support ensure_ascii
        content_json = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
        logger.info(f"Visualizer generated {len(result.prompts)} image prompts with artifacts")
    except Exception as e:
        logger.error(f"Visualizer structured output failed: {e}")
        content_json = json.dumps({"error": str(e)}, ensure_ascii=False)
    
    return Command(
        update={
            "messages": [HumanMessage(content=settings.RESPONSE_FORMAT.format(role="visualizer", content=content_json), name="visualizer")],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_visual", content_json)
        },
        goto="reviewer",
    )

def data_analyst_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for data analyst agent - uses structured output."""
    logger.info("Data Analyst starting task")
    current_step = state["plan"][state["current_step_index"]]

    context = f"Instruction: {current_step['instruction']}\n\nAvailable Artifacts: {json.dumps(state.get('artifacts', {}), default=str)}"

    # Build messages with prompt template
    messages = apply_prompt_template("data_analyst", state)
    messages.append(HumanMessage(content=context, name="supervisor"))

    # Use structured output with Pydantic schema
    llm = get_llm_by_type(AGENT_LLM_MAP["data_analyst"])
    structured_llm = llm.with_structured_output(DataAnalystOutput)

    try:
        result: DataAnalystOutput = structured_llm.invoke(messages)
        content_json = result.model_dump_json(ensure_ascii=False, indent=2)
        logger.info(f"Data Analyst generated {len(result.blueprints)} blueprints")
    except Exception as e:
        logger.error(f"Data Analyst structured output failed: {e}")
        content_json = json.dumps({"error": str(e)}, ensure_ascii=False)

    return Command(
        update={
            "messages": [HumanMessage(content=settings.RESPONSE_FORMAT.format(role="data_analyst", content=content_json), name="data_analyst")],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_data", content_json)
        },
        goto="reviewer",
    )

def reviewer_node(state: State) -> Command[Literal["supervisor", "storywriter", "visualizer", "researcher", "data_analyst"]]:
    """
    Generic Reviewer (Critic) Node.
    
    Evaluates the quality of the output produced by the previous agent against the requirements.
    Implements a **Reflexion** loop:
    - **Approved**: Passes control back to Supervisor to proceed to the next step.
    - **Rejected**: Returns control to the Worker (Writer/Visualizer/etc.) for retry, up to MAX_RETRIES.
    - **Failed**: Escalates to Supervisor if max retries are exceeded.

    Args:
        state (State): Current graph state.

    Returns:
        Command: Routing command to either Supervisor (next step/fail) or Worker (retry).
    """
    logger.info("Reviewer evaluating output...")
    
    current_step = state["plan"][state["current_step_index"]]
    current_role = current_step["role"]
    
    # Identify the target artifact
    role_suffix_map = {
        "storywriter": "story",
        "visualizer": "visual",
        "coder": "code",
        "researcher": "research",
        "data_analyst": "data"
    }
    suffix = role_suffix_map.get(current_role, "unknown")
    artifact_key = f"step_{current_step['id']}_{suffix}"
    latest_artifact = state["artifacts"].get(artifact_key)
    
    if not latest_artifact:
        logger.error(f"No artifact found for review at {artifact_key}")
        # Skip review if artifact is missing (fail safe)
        return Command(goto="supervisor", update={"error_context": f"Missing artifact for {current_role}"})

    # LLM Evaluation (Using Reasoning Model)
    messages = [
        SystemMessage(content="You are a strict QA Lead. Grade the work based on instructions. Output must be in JSON."),
        HumanMessage(content=f"Instruction: {current_step['instruction']}\nOutput: {latest_artifact}")
    ]
    
    # Use structured output
    llm = get_llm_by_type("reasoning") # Use reasoning model for critique
    structured_llm = llm.with_structured_output(ReviewOutput)
    
    try:
        review: ReviewOutput = structured_llm.invoke(messages)
    except Exception as e:
        logger.error(f"Review structured output failed: {e}")
        # If critique fails, default to approved to avoid blocking workflow
        review = ReviewOutput(approved=True, score=0.5, feedback=f"Auto-approved due to critic error: {e}")

    # --- Routing Logic (Reflexion) ---
    current_retries = state.get("retry_count", 0)
    feedback_history = state.get("feedback_history", {})
    step_id_str = str(current_step['id'])
    
    if step_id_str not in feedback_history:
        feedback_history[step_id_str] = []

    # Case 1: Approved
    if review.approved:
        logger.info(f"Work approved (Score: {review.score})")
        feedback_history[step_id_str].append(f"APPROVED: {review.feedback}")
        return Command(
            goto="supervisor",
            update={
                "current_quality_score": review.score,
                "feedback_history": feedback_history
            }
        )

    # Case 2: Rejected (Retry available)
    if current_retries < settings.MAX_RETRIES:
        logger.info(f"Rejecting work (Score: {review.score}). Retry {current_retries + 1}/{settings.MAX_RETRIES}")
        feedback_history[step_id_str].append(f"REJECTED: {review.feedback}")
        return Command(
            goto=current_role, # Route back to Worker
            update={
                "retry_count": current_retries + 1,
                "messages": [HumanMessage(content=f"Review Feedback (QC Failed, Score={review.score}): {review.feedback}. Please fix and regenerate.", name="reviewer")],
                "feedback_history": feedback_history
            }
        )
    
    # Case 3: Rejected (Max retries exceeded)
    logger.warning("Max retries reached. Escalating to Supervisor.")
    feedback_history[step_id_str].append(f"FAILED (Max Retries): {review.feedback}")
    return Command(
        goto="supervisor",
        update={
            "error_context": f"Failed criteria after {settings.MAX_RETRIES} retries. Last feedback: {review.feedback}",
            "feedback_history": feedback_history
        }
    )

def supervisor_node(state: State) -> Command[Literal[*TEAM_MEMBERS, "planner", "__end__", "reviewer"]]:
    """
    Supervisor Node (Orchestrator).

    Manages the execution flow of the graph.
    - **Task Assignment**: Routes to the appropriate worker based on the current plan step.
    - **Progress Tracking**: Moves to the next step upon successful completion (signaled by Reviewer).
    - **Dynamic Replanning**: triggers the Planner if the workflow stalls or encounters unrecoverable errors (Error Context).
    - **Completion**: Routes to END when all steps are finished.

    Args:
        state (State): Current graph state.

    Returns:
        Command: Routing command to Worker, Planner, or END.
    """
    logger.info("Supervisor evaluating state")
    
    idx = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    error_context = state.get("error_context")

    # --- 1. Dynamic Replanning Trigger ---
    # --- 1. Dynamic Replanning Trigger ---
    if error_context:
        current_replans = state.get("replanning_count", 0)
        max_replans = settings.MAX_REPLANNING
        
        if current_replans >= max_replans:
            logger.critical(f"Max replanning limit ({max_replans}) reached. Force stopping to prevent infinite loop.")
            return Command(
                goto="__end__",
                update={
                    "messages": [HumanMessage(content=f"System Stopped: Unable to complete task after {max_replans} replanning attempts. Last error: {error_context}", name="supervisor")]
                }
            )

        logger.error(f"Critical Failure/Stall detected: {error_context}. Requesting Re-planning ({current_replans + 1}/{max_replans}).")
        return Command(
            goto="planner",
            update={
                "messages": [HumanMessage(content=f"Replanning Request: Current plan stalled at step {idx+1}. Reason: {error_context}", name="supervisor")],
                "retry_count": 0,
                "replanning_count": current_replans + 1,
                "error_context": None 
            }
        )

    # --- 2. Normal Plan Progression ---
    if idx >= len(plan):
        logger.info("All steps completed. Converting artifacts to final response.")
        return Command(goto="__end__", update={"current_step_index": idx})

    next_step = plan[idx]
    current_role = next_step["role"]
    
    # Check if we are coming from a successful Review
    # Logic: If the last message is from 'reviewer' AND we are in this node (supervisor),
    # it implies the Reviewer sent us here via "goto='supervisor'".
    # In our Reviewer logic, "goto='supervisor'" happens ONLY on Approval (or Max Retry error_context, handled above).
    # So if we are here and last msg is Reviewer, it's a success.
    
    messages = state.get("messages", [])
    if messages and messages[-1].name == "reviewer":
         # Moved to next step
         new_idx = idx + 1
         logger.info(f"Step {idx} approved. Moving to Step {new_idx}")
         
         if new_idx >= len(plan):
             return Command(goto="__end__", update={"current_step_index": new_idx})
             
         next_step = plan[new_idx] # Update to new next step
         return Command(
            goto=next_step["role"],
            update={
                "current_step_index": new_idx,
                "retry_count": 0,
                # "feedback_history": {} # Keep history for audit trail
            }
        )

    # Initial Assignment (or standard progression)
    logger.info(f"Assigning task to {next_step['role']}")
    return Command(
        goto=next_step["role"],
        update={"retry_count": 0}
    )

def planner_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Planner node - uses structured output for reliable JSON execution plan."""
    logger.info("Planner creating execution plan")
    messages = apply_prompt_template("planner", state)
    
    # Add search results if needed (keep existing logic)
    if state.get("search_before_planning"):
        searched_content = google_search_tool.invoke(state["messages"][-1].content)
        messages = deepcopy(messages)
        messages[-1].content += f"\n\n# Relative Search Results\n\n{searched_content}"

    # Use structured output with Pydantic schema
    llm = get_llm_by_type("reasoning")
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    try:
        result: PlannerOutput = structured_llm.invoke(messages)
        plan_data = [step.model_dump() for step in result.steps]
        
        logger.info(f"Plan generated with {len(plan_data)} steps (structured output).")
        return Command(
            update={
                "messages": [HumanMessage(content=f"Plan Generated: {len(plan_data)} steps defined.", name="planner")],
                "plan": plan_data,
                "current_step_index": 0,
                "artifacts": {}
            },
            goto="supervisor",
        )
    except Exception as e:
        logger.error(f"Planner structured output failed: {e}")
        return Command(
            update={"messages": [HumanMessage(content=f"Failed to generate a valid plan: {e}", name="planner")]},
            goto="__end__"
        )

def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator: Gatekeeper."""
    logger.info("Coordinator processing request")
    messages = apply_prompt_template("coordinator", state)
    response = get_llm_by_type(AGENT_LLM_MAP["coordinator"]).invoke(messages)
    content = response.content
    
    logger.debug(f"Coordinator response: {content}")
    logger.debug(f"Coordinator Raw Content: '{content}'")
    logger.debug(f"Tool Calls: {response.tool_calls}")
    logger.debug(f"Additional Kwargs: {response.additional_kwargs}")

    if "handoff_to_planner" in content:
        logger.info("Handing off to planner detected.")
        return Command(goto="planner")
    
    # Simple chat response
    return Command(
        update={"messages": [HumanMessage(content=content, name="coordinator")]},
        goto="__end__"
    )
